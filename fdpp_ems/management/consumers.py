



import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Employee, Attendance
from datetime import datetime
from django.conf import settings

class BiometricConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time biometric device events"""
    
    async def connect(self):
        await self.channel_layer.group_add("biometric_device", self.channel_name)
        await self.accept()
        
        await self.send(json.dumps({
            "type": "connection",
            "message": "Connected to biometric service"
        }))
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("biometric_device", self.channel_name)
    
    async def receive(self, text_data):
        """Handle data sent FROM the biometric script via WebSocket"""
        try:
            data = json.loads(text_data)
            emp_id = data.get('emp_id')
            if emp_id:
                # Process the scan using the synchronized logic
                response = await self.process_biometric_scan(emp_id)
                
                # Broadcast the result to the frontend
                await self.channel_layer.group_send(
                    "biometric_device",
                    {
                        "type": "biometric_event",
                        "data": response # response now contains the full 'attendance_info'
                    }
                )
        except Exception as e:
            await self.send(json.dumps({"type": "error", "error": str(e)}))

    async def biometric_event(self, event):
        """Receives data from group_send and sends to Frontend"""
        # Matches the structure the frontend expects
        await self.send(text_data=json.dumps({
            "type": "biometric_attendance",
            "data": event.get('data'),
            "timestamp": datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        }))

    @database_sync_to_async
    def process_biometric_scan(self, emp_id):
        """Synchronized Logic: Matches auto_attendance view exactly"""
        try:
            employee = Employee.objects.get(emp_id=emp_id)
            # FIXED: Use system clock (Naive) to match settings.USE_TZ = False
            now = datetime.now()
            today = now.date()
            current_time = now.time()
            
            last_attendance = Attendance.objects.filter(
                employee=employee,
                date=today
            ).order_by('-check_in').first()
            
            # Prepare the exact data structure your frontend UI needs
            attendance_info = {
                "emp_id": employee.emp_id,
                "employee_name": employee.name,
                "profile_img": f"http://{settings.SERVER_IP}:{settings.SERVER_PORT}{employee.profile_img.url}" if employee.profile_img else None,
                "shift_type": employee.shift_type,
                "timestamp": now.strftime('%I:%M %p'), 
            }
            
            # Logic: Check-in or Check-out
            if not last_attendance or last_attendance.check_out:
                # ACTION: CHECK-IN
                shift_start = employee.start_time
                is_late = current_time > shift_start
                status_val = 'late' if is_late else 'on_time'
                
                late_msg = "On time"
                if is_late:
                    shift_start_dt = datetime.combine(today, shift_start)
                    diff = int((now - shift_start_dt).total_seconds() / 60)
                    late_msg = f"{diff//60}h {diff%60}m late" if diff >= 60 else f"{diff}m late"
                
                Attendance.objects.create(
                    employee=employee, date=today, check_in=now,
                    status=status_val, message_late=late_msg
                )
                
                attendance_info.update({
                    "action": "check_in",
                    "check_in": now.strftime('%I:%M %p'),
                    "check_out": "--:--",
                    "is_late": is_late,
                    "late_message": late_msg,
                    "total_hours_today": 0
                })
            else:
                # ACTION: CHECK-OUT
                last_attendance.check_out = now
                last_attendance.save()
                
                # Calculate total hours
                first_checkin = Attendance.objects.filter(employee=employee, date=today).order_by('check_in').first()
                total_hours = round(min((now - first_checkin.check_in).total_seconds() / 3600, 14.0), 2)
                
                attendance_info.update({
                    "action": "check_out",
                    "check_in": last_attendance.check_in.strftime('%I:%M %p'),
                    "check_out": now.strftime('%I:%M %p'),
                    "is_late": False,
                    "total_hours_today": total_hours
                })
            
            return attendance_info
        
        except Exception as e:
            return {"type": "error", "error": str(e), "emp_id": emp_id}
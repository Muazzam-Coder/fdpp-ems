import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Employee, Attendance
from datetime import datetime, timedelta
from django.utils import timezone


class AttendanceConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time attendance notifications"""
    
    async def connect(self):
        """Accept WebSocket connection"""
        await self.accept()
        await self.send(json.dumps({
            "type": "connection",
            "message": "Connected to attendance service"
        }))
    
    async def disconnect(self, close_code):
        """Handle disconnect"""
        pass
    
    async def receive(self, text_data):
        """Handle incoming messages"""
        try:
            data = json.loads(text_data)
            emp_id = data.get('emp_id')
            action = data.get('action', 'check_attendance')
            
            if action == 'check_attendance' and emp_id:
                response = await self.check_employee_attendance(emp_id)
                await self.send(json.dumps(response))
            else:
                await self.send(json.dumps({
                    "error": "Invalid request. Provide emp_id and action."
                }))
        except json.JSONDecodeError:
            await self.send(json.dumps({
                "error": "Invalid JSON format"
            }))
    
    @database_sync_to_async
    def check_employee_attendance(self, emp_id):
        """Check employee status and return attendance info"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            employee = Employee.objects.get(emp_id=emp_id)
            logger.info(f"Found employee: {employee.name}")
            
            # Get today's attendance record
            now = timezone.now()
            today = now.date()
            logger.info(f"Querying for today: {today}")
            
            last_attendance = Attendance.objects.filter(
                employee=employee,
                date=today
            ).order_by('-check_in').first()
            
            logger.info(f"Found attendance records: {last_attendance}")
            if last_attendance:
                logger.info(f"  Check-in: {last_attendance.check_in}")
                logger.info(f"  Check-out: {last_attendance.check_out}")
            
            # Current time
            current_time = now.time()
            
            # Get shift start time
            shift_start = employee.start_time
            is_late = current_time > shift_start
            
            # Calculate message
            if is_late:
                # Calculate how many minutes late
                start_datetime = timezone.make_aware(
                    datetime.combine(today, shift_start)
                )
                minutes_late = int((now - start_datetime).total_seconds() / 60)
                message = f"⚠️ You are {minutes_late} minutes late"
            else:
                message = "✅ You are on time"
            
            # Get profile picture URL
            profile_img_url = None
            if employee.profile_img:
                profile_img_url = employee.profile_img.url
            
            # Get first name and last name
            first_name = ""
            last_name = ""
            if employee.user:
                first_name = employee.user.first_name or ""
                last_name = employee.user.last_name or ""
            
            logger.info(f"Employee info: {first_name} {last_name}")
            
            # Calculate check-in and check-out times for today
            check_in = None
            check_out = None
            total_hours = None
            
            if last_attendance:
                check_in = last_attendance.check_in.isoformat() if last_attendance.check_in else None
                check_out = last_attendance.check_out.isoformat() if last_attendance.check_out else None
                logger.info(f"Set check_in: {check_in}")
                logger.info(f"Set check_out: {check_out}")
                
                # Calculate total hours if checked out
                if check_out:
                    first_checkin = Attendance.objects.filter(
                        employee=employee,
                        date=today
                    ).order_by('check_in').first()
                    
                    if first_checkin:
                        total_duration = (last_attendance.check_out - first_checkin.check_in).total_seconds() / 3600
                        total_hours = round(min(total_duration, 14.0), 2)
            
            result = {
                "type": "attendance_info",
                "emp_id": employee.emp_id,
                "name": employee.name,
                "first_name": first_name,
                "last_name": last_name,
                "profile_picture": profile_img_url,
                "shift_type": employee.shift_type,
                "shift_start": str(employee.start_time),
                "shift_end": str(employee.end_time),
                "check_in": check_in,
                "check_out": check_out,
                "total_hours": total_hours,
                "is_late": is_late,
                "message": message,
                "last_status": last_attendance.status if last_attendance else None,
                "timestamp": now.isoformat()
            }
            logger.info(f"Returning: {result}")
            return result
        
        except Employee.DoesNotExist:
            return {
                "type": "error",
                "error": f"Employee with ID {emp_id} not found"
            }
        except Exception as e:
            import traceback
            logger.error(f"Exception in check_employee_attendance: {e}")
            logger.error(traceback.format_exc())
            return {
                "type": "error",
                "error": str(e),
                "traceback": traceback.format_exc()
            }


class BiometricConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time biometric device events"""
    
    async def connect(self):
        """Accept WebSocket connection from biometric device/script"""
        await self.channel_layer.group_add("biometric_device", self.channel_name)
        await self.accept()
        await self.send(json.dumps({
            "type": "connection",
            "message": "Connected to biometric service",
            "timestamp": timezone.now().isoformat()
        }))
    
    async def disconnect(self, close_code):
        """Handle disconnect"""
        await self.channel_layer.group_discard("biometric_device", self.channel_name)
    
    async def receive(self, text_data):
        """Handle incoming biometric scan data"""
        try:
            data = json.loads(text_data)
            emp_id = data.get('emp_id')
            
            if emp_id:
                # Process the attendance and get response
                response = await self.process_biometric_scan(emp_id)
                
                # Send response back to this connection
                await self.send(json.dumps(response))
                
                # Broadcast to all connected biometric listeners
                await self.channel_layer.group_send(
                    "biometric_device",
                    {
                        "type": "biometric_event",
                        "data": response
                    }
                )
            else:
                await self.send(json.dumps({
                    "error": "emp_id is required"
                }))
        except json.JSONDecodeError:
            await self.send(json.dumps({
                "error": "Invalid JSON format"
            }))
    
    async def biometric_event(self, event):
        """Broadcast biometric event to connected clients"""
        data = event.get('data')
        await self.send(json.dumps({
            "type": "biometric_attendance",
            "data": data,
            "timestamp": timezone.now().isoformat()
        }))
    
    @database_sync_to_async
    def process_biometric_scan(self, emp_id):
        """Process biometric scan and return attendance info"""
        try:
            from .views import AttendanceViewSet
            
            employee = Employee.objects.get(emp_id=emp_id)
            today = timezone.now().date()
            now = timezone.now()
            
            # Get today's latest attendance record
            last_attendance = Attendance.objects.filter(
                employee=employee,
                date=today
            ).order_by('-check_in').first()
            
            # Determine action (check-in or check-out)
            if not last_attendance or last_attendance.check_out:
                action = "check_in"
                is_late = now.time() > employee.start_time
                
                if is_late:
                    shift_start_datetime = timezone.make_aware(
                        datetime.combine(today, employee.start_time)
                    )
                    minutes_late = int((now - shift_start_datetime).total_seconds() / 60)
                    message = f"⚠️ {employee.name} is {minutes_late} minutes late"
                else:
                    message = f"✅ {employee.name} checked in on time"
                
                status = 'late' if is_late else 'on_time'
                attendance = Attendance.objects.create(
                    employee=employee,
                    date=today,
                    check_in=now,
                    status=status
                )
            else:
                action = "check_out"
                duration = (now - last_attendance.check_in).total_seconds() / 3600
                
                if duration > 14:
                    return {
                        "type": "error",
                        "error": f"Cannot check out. Duration exceeds 14 hours",
                        "emp_id": emp_id,
                        "employee_name": employee.name
                    }
                
                last_attendance.check_out = now
                last_attendance.save()
                attendance = last_attendance
                
                first_checkin = Attendance.objects.filter(
                    employee=employee,
                    date=today
                ).order_by('check_in').first()
                
                if first_checkin:
                    total_duration = (now - first_checkin.check_in).total_seconds() / 3600
                    total_hours = round(min(total_duration, 14.0), 2)
                else:
                    total_hours = 0
                
                message = f"👋 {employee.name} checked out (Total: {total_hours} hours)"
            
            return {
                "type": "biometric_success",
                "emp_id": emp_id,
                "employee_name": employee.name,
                "action": action,
                "message": message,
                "is_late": is_late if action == "check_in" else None,
                "check_in": str(attendance.check_in) if attendance.check_in else None,
                "check_out": str(attendance.check_out) if attendance.check_out else None,
                "profile_img": employee.profile_img.url if employee.profile_img else None
            }
        
        except Employee.DoesNotExist:
            return {
                "type": "error",
                "error": f"Employee {emp_id} not found",
                "emp_id": emp_id
            }
        except Exception as e:
            return {
                "type": "error",
                "error": str(e),
                "emp_id": emp_id
            }


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
            employee = Employee.objects.get(emp_id=emp_id)
            
            # Get last attendance record
            last_attendance = Attendance.objects.filter(
                employee=employee
            ).order_by('-date', '-check_in').first()
            
            # Current time and date
            now = timezone.now()
            today = now.date()
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
                message = f"You are {minutes_late} minutes late"
            else:
                message = None
            
            # Get profile picture URL
            profile_img_url = None
            if employee.profile_img:
                profile_img_url = employee.profile_img.url
            
            return {
                "type": "attendance_info",
                "emp_id": employee.emp_id,
                "name": employee.name,
                "profile_picture": profile_img_url,
                "shift_type": employee.shift_type,
                "shift_start": str(employee.start_time),
                "shift_end": str(employee.end_time),
                "check_in": None,
                "check_out": None,
                "is_late": is_late,
                "message": message,
                "last_status": last_attendance.status if last_attendance else None,
                "timestamp": now.isoformat()
            }
        
        except Employee.DoesNotExist:
            return {
                "type": "error",
                "error": f"Employee with ID {emp_id} not found"
            }
        except Exception as e:
            return {
                "type": "error",
                "error": str(e)
            }





import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db import close_old_connections
from .models import Employee, Attendance, InactiveAttendanceAttempt
from datetime import datetime, timedelta
from django.utils import timezone
import logging
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
            timestamp = data.get('timestamp')
            if emp_id:
                # Process the scan using the synchronized logic (pass timestamp if provided)
                response = await self.process_biometric_scan(emp_id, timestamp)
                
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
    def process_biometric_scan(self, emp_id, timestamp_in=None):
        """Synchronized Logic: Matches auto_attendance view exactly"""
        try:
            # Ensure any stale DB connections are closed before using ORM
            close_old_connections()
            employee = Employee.objects.get(emp_id=emp_id)
            # FIXED: Use system clock (Naive) to match settings.USE_TZ = False
            # Prefer client-sent timestamp if provided
            now = None
            if timestamp_in:
                try:
                    # try ISO or common format
                    try:
                        now = datetime.fromisoformat(str(timestamp_in))
                    except Exception:
                        now = datetime.strptime(str(timestamp_in), '%Y-%m-%d %H:%M:%S')
                except Exception:
                    now = datetime.now()
            else:
                now = datetime.now()
            logger = logging.getLogger(__name__)
            today = now.date()
            current_time = now.time()
            
            # Use same logic as HTTP auto_attendance: consider latest attendance
            last_attendance = Attendance.objects.filter(employee=employee).order_by('-check_in').first()

            # For total-hours calculation when checking out, capture first open checkin
            first_checkin = None
            if last_attendance and last_attendance.check_out is None:
                first_checkin = last_attendance

            # If employee is inactive, log the attempt and return an error payload
            if getattr(employee, 'status', '') != 'active':
                try:
                    InactiveAttendanceAttempt.objects.create(
                        employee=employee,
                        attempted_by=None,
                        method='websocket',
                        message='Attempted biometric scan while employee inactive',
                        deactivated_by_username=employee.deactivated_by.username if getattr(employee, 'deactivated_by', None) else None,
                        deactivated_at=employee.deactivated_at
                    )
                except Exception:
                    pass
                return {"type": "error", "error": "Employee inactive", "emp_id": emp_id}
            
            did_modify = False
            # Prepare the exact data structure your frontend UI needs
            attendance_info = {
                "emp_id": employee.emp_id,
                "employee_name": employee.name,
                "profile_img": f"http://{settings.SERVER_IP}:{settings.SERVER_PORT}{employee.profile_img.url}" if employee.profile_img else None,
                "shift_type": employee.shift_type,
                "timestamp": now.strftime('%I:%M %p'), 
            }
            
            # Logic: Check-in or Check-out (mirror auto_attendance view)
            if not last_attendance or (last_attendance.check_out is not None):
                # ===== NEW CHECK-IN =====
                shift_start = employee.start_time
                is_late = False
                late_msg = "On time"
                if shift_start:
                    shift_start_dt = datetime.combine(today, shift_start)
                    # Adjust for overnight shifts
                    if getattr(employee, 'end_time', None) and employee.end_time <= shift_start and shift_start_dt > now:
                        shift_start_dt -= timedelta(days=1)

                    is_late = now > shift_start_dt
                    if is_late:
                        total_minutes = int((now - shift_start_dt).total_seconds() / 60)
                        if total_minutes >= 60:
                            hours = total_minutes // 60
                            minutes = total_minutes % 60
                            late_msg = f"{hours}h {minutes}m late" if minutes > 0 else f"{hours}h late"
                        else:
                            late_msg = f"{total_minutes}m late"

                status_val = 'late' if is_late else 'on_time'

                # Deduplicate creation within small time window
                window_start = now - timedelta(seconds=5)
                window_end = now + timedelta(seconds=5)
                existing = Attendance.objects.filter(employee=employee, check_in__range=[window_start, window_end]).first()
                if existing:
                    attendance = existing
                else:
                    attendance = Attendance.objects.create(
                        employee=employee,
                        date=today,
                        check_in=now,
                        message_late=late_msg,
                        status=status_val
                    )
                    did_modify = True

                attendance_info.update({
                    "action": "check_in",
                    "check_in": now.strftime('%I:%M %p'),
                    "check_out": "--:--",
                    "is_late": is_late,
                    "late_message": late_msg,
                    "total_hours_today": "0h 0m",
                    "total_hours_today_value": 0
                })
            elif last_attendance.check_in is not None and last_attendance.check_out is None:
                # ===== CHECK-OUT =====
                try:
                    logger.debug(f"websocket auto: emp_id={emp_id}, received_timestamp={timestamp_in}, now={now}, last_check_in={last_attendance.check_in}")
                except Exception:
                    pass
                duration = (now - last_attendance.check_in).total_seconds() / 3600
                try:
                    logger.debug(f"websocket auto: computed duration_hours={duration}")
                except Exception:
                    pass
                if duration > 14:
                    # Do NOT auto-fill previous record's check_out; leave it open.
                    # Create a new attendance record for the new check-in and return a check-in payload.
                    new_status = 'on_time'
                    new_late_msg = None
                    if employee.start_time:
                        new_shift_start = datetime.combine(now.date(), employee.start_time)
                        if getattr(employee, 'end_time', None) and employee.end_time <= employee.start_time and new_shift_start > now:
                            new_shift_start -= timedelta(days=1)
                        is_late_new = now > new_shift_start
                        new_status = 'late' if is_late_new else 'on_time'
                        if is_late_new:
                            mins = int((now - new_shift_start).total_seconds() / 60)
                            new_late_msg = f"you are late {mins}m"

                    # Deduplicate new check-in creation
                    window_start = now - timedelta(seconds=5)
                    window_end = now + timedelta(seconds=5)
                    existing_new = Attendance.objects.filter(employee=employee, check_in__range=[window_start, window_end]).first()
                    if existing_new:
                        new_att = existing_new
                    else:
                        new_att = Attendance.objects.create(
                            employee=employee,
                            date=timezone.now().date(),
                            check_in=now,
                            status=new_status,
                            message_late=new_late_msg
                        )
                        did_modify = True

                    # Return a standard check-in style response for the new attendance
                    action = "check_in"
                    attendance_info.update({
                        "action": action,
                        "check_in": new_att.check_in.strftime('%I:%M %p'),
                        "check_out": "--:--",
                        "is_late": True if new_status == 'late' else False,
                        "late_message": new_late_msg,
                        "total_hours_today": "0h 0m",
                        "total_hours_today_value": 0
                    })
                else:
                    # Standard check-out path: close the open attendance
                    last_attendance.check_out = now
                    last_attendance.save()
                    did_modify = True

                    total_hours = 0
                    if first_checkin:
                        total_duration = (now - first_checkin.check_in).total_seconds() / 3600
                        total_hours = round(min(total_duration, 14.0), 2)

                    action = "check_out"
                    attendance_info.update({
                        "action": action,
                        "check_in": last_attendance.check_in.strftime('%I:%M %p'),
                        "check_out": now.strftime('%I:%M %p'),
                        "is_late": False,
                        "late_message": None,
                        "total_hours_today": total_hours,
                        "total_hours_today_value": total_hours
                    })

            # Broadcast/update only if we created/updated DB
            if did_modify:
                try:
                    from asgiref.sync import async_to_sync
                    from channels.layers import get_channel_layer
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        "biometric_device",
                        {
                            "type": "biometric_event",
                            "data": attendance_info
                        }
                    )
                except Exception:
                    pass

            return attendance_info
        except Exception as e:
            return {"type": "error", "error": str(e), "emp_id": emp_id}
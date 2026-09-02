



import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db import close_old_connections
from .models import Employee, Attendance, InactiveAttendanceAttempt, get_employee_shift_times, get_overtime_max_allowed
from datetime import datetime, timedelta
from django.utils import timezone
import logging
from django.conf import settings

# Grace period for lateness in minutes (configurable via Django settings)
LATE_GRACE_MINUTES = getattr(settings, 'LATE_GRACE_MINUTES', 10)

class BiometricConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time biometric device events"""
    
    @database_sync_to_async
    def _check_duplicate(self, emp_id, now):
        """Check if this employee has any scan (in or out) within the last 10 seconds."""
        close_old_connections()
        try:
            employee = Employee.objects.get(emp_id=emp_id)
        except Employee.DoesNotExist:
            return False, 0
        last_att = Attendance.objects.filter(employee=employee).order_by('-check_in').first()
        if last_att:
            last_event = last_att.check_out if last_att.check_out else last_att.check_in
            elapsed = int((now - last_event).total_seconds())
            if elapsed < 10:
                return True, 10 - elapsed
        return False, 0
    
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
                # Dedup check in async context BEFORE calling process_biometric_scan
                now = datetime.now()
                is_dup, wait = await self._check_duplicate(emp_id, now)
                if is_dup:
                    await self.channel_layer.group_send(
                        "biometric_device",
                        {
                            "type": "biometric_duplicate",
                            "message": f"You already marked your attendance, Wait for {wait}s to try again"
                        }
                    )
                    return

                response = await self.process_biometric_scan(emp_id, timestamp, now)
                
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

    async def biometric_duplicate(self, event):
        """Sends duplicate warning in the exact format the user requested"""
        await self.send(text_data=json.dumps({
            "type": "biometric_attendance",
            "message": event["message"],
        }))

    async def biometric_event(self, event):
        """Receives data from group_send and sends to Frontend"""
        # Matches the structure the frontend expects
        await self.send(text_data=json.dumps({
            "type": "biometric_attendance",
            "data": event.get('data'),
            "timestamp": datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        }))

    @database_sync_to_async
    def process_biometric_scan(self, emp_id, timestamp_in=None, now=None):
        """Synchronized Logic: Matches auto_attendance view exactly"""
        try:
            # Ensure any stale DB connections are closed before using ORM
            close_old_connections()
            employee = Employee.objects.get(emp_id=emp_id)
            # Use passed-in now (from dedup) or compute from timestamp / system clock
            if now is None:
                if timestamp_in:
                    try:
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
            
            # Prepare the exact data structure your frontend UI needs
            shift_name = employee.current_shift.name if employee.current_shift else "N/A"
            attendance_info = {
                "emp_id": employee.emp_id,
                "employee_name": employee.name,
                "profile_img": f"http://{settings.SERVER_IP}:{settings.SERVER_PORT}{employee.profile_img.url}" if employee.profile_img else None,
                "shift_type": shift_name,
                "timestamp": now.strftime('%I:%M %p'), 
            }
            
            s_start, s_end = get_employee_shift_times(employee, today)

            # Logic: Check-in or Check-out (mirror auto_attendance view)
            if not last_attendance or (last_attendance.check_out is not None):
                # ===== NEW CHECK-IN =====
                is_late = False
                late_msg = "On time"
                if s_start:
                    shift_start_dt = datetime.combine(today, s_start)
                    # Adjust for overnight shifts
                    if s_end and s_end <= s_start and shift_start_dt > now:
                        if now.time() < s_end:
                            shift_start_dt -= timedelta(days=1)

                    is_late = now > shift_start_dt + timedelta(minutes=LATE_GRACE_MINUTES)
                    if is_late:
                        total_minutes = int((now - shift_start_dt).total_seconds() / 60)
                        if total_minutes >= 60:
                            hours = total_minutes // 60
                            minutes = total_minutes % 60
                            late_msg = f"{hours}h {minutes}m late" if minutes > 0 else f"{hours}h late"
                        else:
                            late_msg = f"{total_minutes}m late"

                status_val = 'late' if is_late else 'on_time'

                Attendance.objects.create(
                    employee=employee,
                    date=today,
                    check_in=now,
                    message_late=late_msg,
                    status=status_val
                )

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
                max_allowed = get_overtime_max_allowed(employee, last_attendance.check_in)
                if duration > max_allowed:
                    # Do NOT auto-fill previous record's check_out; leave it open.
                    # Create a new attendance record for the new check-in and return a check-in payload.
                    new_status = 'on_time'
                    new_late_msg = None
                    if s_start:
                        new_shift_start = datetime.combine(now.date(), s_start)
                        if s_end and s_end <= s_start and new_shift_start > now:
                            if now.time() < s_end:
                                new_shift_start -= timedelta(days=1)
                        is_late_new = now > new_shift_start + timedelta(minutes=LATE_GRACE_MINUTES)
                        new_status = 'late' if is_late_new else 'on_time'
                        if is_late_new:
                            mins = int((now - new_shift_start).total_seconds() / 60)
                            new_late_msg = f"you are late {mins}m"

                    new_att = Attendance.objects.create(
                        employee=employee,
                        date=timezone.now().date(),
                        check_in=now,
                        status=new_status,
                        message_late=new_late_msg
                    )

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

                    total_hours = 0
                    regular_hours = 0
                    overtime_hours = 0
                    if first_checkin:
                        total_duration = (now - first_checkin.check_in).total_seconds() / 3600
                        total_hours = round(min(total_duration, max_allowed), 2)
                        # Auto overtime: hours worked after shift end
                        if s_end:
                            shift_end_dt = datetime.combine(today, s_end)
                            if s_end <= s_start:
                                shift_end_dt += timedelta(days=1)
                            if now > shift_end_dt:
                                ot_sec = (now - shift_end_dt).total_seconds()
                                overtime_hours = round(max(0, ot_sec / 3600), 2)
                                reg_sec = (shift_end_dt - first_checkin.check_in).total_seconds()
                                regular_hours = round(max(0, reg_sec / 3600), 2)
                            else:
                                regular_hours = total_hours
                        else:
                            regular_hours = total_hours

                    action = "check_out"
                    attendance_info.update({
                        "action": action,
                        "check_in": last_attendance.check_in.strftime('%I:%M %p'),
                        "check_out": now.strftime('%I:%M %p'),
                        "is_late": False,
                        "late_message": None,
                        "total_hours_today": total_hours,
                        "total_hours_today_value": total_hours,
                        "regular_hours": regular_hours,
                        "overtime_hours": overtime_hours
                    })

            # Note: broadcasting to the channel layer is handled by the async
            # consumer layer (receive/biometric_event). Avoid sending here to
            # prevent duplicate messages to connected clients.

            return attendance_info
        except Exception as e:
            return {"type": "error", "error": str(e), "emp_id": emp_id}
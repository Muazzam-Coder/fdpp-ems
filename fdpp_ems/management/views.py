from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from django_filters import rest_framework as filters
from django.contrib.auth.models import User
from .models import (
    Employee, Attendance, PaidLeave, Shift, UserAccessLevel,
    InactiveAttendanceAttempt, EmployeeShiftHistory, Holiday, Overtime,
    Salary, get_employee_shift_times, get_overtime_max_allowed,
    get_salary_for_date, get_duty_date_for_check_in,
    ActivityLog, log_activity
)
from .serializers import (
    EmployeeSerializer, AttendanceSerializer, PaidLeaveSerializer, 
    ShiftSerializer, UserAccessLevelSerializer,
    CreateAdminManagerSerializer, RegisterSerializer,
    ChangePasswordSerializer, AdminSetPasswordSerializer,
    EmployeeShiftHistorySerializer, HolidaySerializer, OvertimeSerializer,
    SalarySerializer,
    ComprehensiveReportInputSerializer,
    ActivityLogSerializer,
)
from django.db.models import Q
from datetime import datetime, timedelta, date, time
from decimal import Decimal
from django.utils import timezone
from fdpp_ems import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from io import BytesIO
from django.http import HttpResponse
import logging
try:
    import openpyxl
    from openpyxl.utils import get_column_letter
except Exception:
    openpyxl = None
    get_column_letter = None

# Grace period for lateness in minutes (configurable via Django settings)
LATE_GRACE_MINUTES = getattr(settings, 'LATE_GRACE_MINUTES', 10)

# Permission check: Only admins can create admin/manager
def is_admin(user):
    """Check if user has admin role"""
    if getattr(user, 'is_superuser', False):
        return True
    try:
        return user.access_level.role == 'admin'
    except (AttributeError, UserAccessLevel.DoesNotExist):
        return False


WEEKDAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def format_hours_display(hours_value):
    if hours_value is None:
        return '0h 0m'

    total_minutes = max(0, int(round(float(hours_value) * 60)))
    hours, minutes = divmod(total_minutes, 60)
    return f'{hours}h {minutes}m'


def parse_date_range_params(request):
    """Helper to parse date or start_date/end_date (or date_from/date_to) query params.
    Returns (start_date, end_date, error_message).
    """
    date_str = request.query_params.get('date')
    start_str = request.query_params.get('start_date') or request.query_params.get('date_from')
    end_str = request.query_params.get('end_date') or request.query_params.get('date_to')

    if date_str:
        try:
            d = datetime.strptime(date_str, '%Y-%m-%d').date()
            return d, d, None
        except ValueError:
            return None, None, "Invalid date format. Use YYYY-MM-DD"

    if start_str or end_str:
        if not start_str or not end_str:
            return None, None, "Please provide both start_date and end_date (YYYY-MM-DD)"
        try:
            s_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            e_date = datetime.strptime(end_str, '%Y-%m-%d').date()
            if s_date > e_date:
                return None, None, "start_date cannot be after end_date"
            return s_date, e_date, None
        except ValueError:
            return None, None, "Invalid date format. Use YYYY-MM-DD"

    # Default to current month: 1st of current month to today (or end of month)
    today = timezone.now().date()
    s_date = date(today.year, today.month, 1)
    if today.month == 12:
        e_date = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        e_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
    return s_date, e_date, None


def build_employee_detailed_logs(employee, start_date, end_date):
    """Generate detailed breakdown of all punch sessions and daily summaries for an employee."""
    attendances = Attendance.objects.filter(
        employee=employee,
        date__range=[start_date, end_date]
    ).order_by('date', 'check_in')

    att_map = {}
    for att in attendances:
        att_map.setdefault(att.date, []).append(att)

    leaves = PaidLeave.objects.filter(
        employee=employee,
        approved=True,
        start_time__date__lte=end_date,
        end_time__date__gte=start_date
    )
    holidays = {h.date: h for h in Holiday.objects.filter(date__range=[start_date, end_date])}
    overtimes = {o.date: o for o in Overtime.objects.filter(employee=employee, date__range=[start_date, end_date], status='approved')}

    shift_info = None
    if employee.current_shift:
        st = employee.current_shift.start_time
        et = employee.current_shift.end_time
        st_str = st.strftime('%I:%M %p') if st else ''
        et_str = et.strftime('%I:%M %p') if et else ''
        shift_info = {
            "id": employee.current_shift.id,
            "name": employee.current_shift.name,
            "start_time": st_str,
            "end_time": et_str,
            "working_hours": f"{st_str} - {et_str}" if (st_str and et_str) else employee.current_shift.name
        }

    daily_logs = []
    curr = start_date
    total_worked_hours = 0.0
    total_sessions_count = 0
    days_present = 0
    days_absent = 0
    days_leave = 0
    days_off = 0
    days_holiday = 0
    late_arrivals_count = 0
    today = timezone.now().date()
    current_time = datetime.now().time()

    while curr <= end_date:
        weekday_idx = curr.weekday()
        weekday_name = curr.strftime('%A')
        is_off = (employee.weekly_off_day is not None and weekday_idx == employee.weekly_off_day)
        holiday = holidays.get(curr)
        ot_rec = overtimes.get(curr)

        leave_rec = None
        for lv in leaves:
            if lv.start_time.date() <= curr <= lv.end_time.date():
                leave_rec = lv
                break

        day_atts = att_map.get(curr, [])
        sessions_data = []

        if day_atts:
            days_present += 1
            total_sessions_count += len(day_atts)
            first_att = day_atts[0]
            last_att = day_atts[-1]

            first_in = first_att.check_in.strftime('%I:%M:%S %p') if first_att.check_in else None
            last_out = last_att.check_out.strftime('%I:%M:%S %p') if last_att.check_out else None

            day_hours = round(sum(a.total_hours for a in day_atts), 2)
            total_worked_hours += day_hours

            is_late_day = any(a.status == 'late' for a in day_atts)
            if is_late_day:
                late_arrivals_count += 1
            status_val = 'late' if is_late_day else 'on_time'

            for a in day_atts:
                sessions_data.append({
                    "id": a.id,
                    "check_in": a.check_in.isoformat() if a.check_in else None,
                    "check_in_formatted": a.check_in.strftime('%I:%M:%S %p') if a.check_in else None,
                    "check_out": a.check_out.isoformat() if a.check_out else None,
                    "check_out_formatted": a.check_out.strftime('%I:%M:%S %p') if a.check_out else "--:--",
                    "total_hours": format_hours_display(a.total_hours),
                    "total_hours_value": float(a.total_hours),
                    "status": a.status,
                    "message_late": a.message_late,
                    "is_late": a.is_late,
                })

            daily_logs.append({
                "date": curr.isoformat(),
                "day_of_week": weekday_name,
                "status": status_val,
                "first_check_in": first_in,
                "last_check_out": last_out if last_out else "--:--",
                "total_hours": format_hours_display(day_hours),
                "total_hours_value": day_hours,
                "total_sessions": len(day_atts),
                "is_late": is_late_day,
                "late_message": first_att.message_late or ("Late arrival" if is_late_day else "On time"),
                "overtime_hours": float(ot_rec.total_hours) if ot_rec else 0.0,
                "sessions": sessions_data
            })
        elif leave_rec:
            days_leave += 1
            daily_logs.append({
                "date": curr.isoformat(),
                "day_of_week": weekday_name,
                "status": "on_leave",
                "first_check_in": None,
                "last_check_out": None,
                "total_hours": "0h 0m",
                "total_hours_value": 0.0,
                "total_sessions": 0,
                "is_late": False,
                "late_message": f"Leave ({leave_rec.get_leave_type_display()})",
                "overtime_hours": 0.0,
                "sessions": []
            })
        elif holiday:
            days_holiday += 1
            daily_logs.append({
                "date": curr.isoformat(),
                "day_of_week": weekday_name,
                "status": "holiday",
                "first_check_in": None,
                "last_check_out": None,
                "total_hours": "0h 0m",
                "total_hours_value": 0.0,
                "total_sessions": 0,
                "is_late": False,
                "late_message": f"Holiday ({holiday.name})",
                "overtime_hours": 0.0,
                "sessions": []
            })
        elif is_off:
            days_off += 1
            daily_logs.append({
                "date": curr.isoformat(),
                "day_of_week": weekday_name,
                "status": "off_day",
                "first_check_in": None,
                "last_check_out": None,
                "total_hours": "0h 0m",
                "total_hours_value": 0.0,
                "total_sessions": 0,
                "is_late": False,
                "late_message": "Weekly Off Day",
                "overtime_hours": 0.0,
                "sessions": []
            })
        else:
            s_start, s_end = get_employee_shift_times(employee, curr)
            is_past = (curr < today) or (curr == today and s_end and current_time >= s_end)
            if is_past:
                days_absent += 1
                status_str = "absent"
                msg = "Absent"
            else:
                status_str = "pending"
                msg = "Shift not started yet" if (curr == today) else "Upcoming"

            daily_logs.append({
                "date": curr.isoformat(),
                "day_of_week": weekday_name,
                "status": status_str,
                "first_check_in": None,
                "last_check_out": None,
                "total_hours": "0h 0m",
                "total_hours_value": 0.0,
                "total_sessions": 0,
                "is_late": False,
                "late_message": msg,
                "overtime_hours": 0.0,
                "sessions": []
            })

        curr += timedelta(days=1)

    total_worked_hours = round(total_worked_hours, 2)
    hourly_rate = float(employee.hourly_rate or 0)
    estimated_pay = round(total_worked_hours * hourly_rate, 2)

    return {
        "employee": {
            "id": employee.id,
            "emp_id": employee.emp_id,
            "name": employee.name,
            "designation": employee.designation,
            "status": employee.status,
            "current_shift": shift_info,
            "weekly_off_day": employee.weekly_off_day,
            "weekly_off_day_name": employee.get_weekly_off_day_display() if employee.weekly_off_day is not None else "None",
            "salary": float(employee.salary or 0),
            "hourly_rate": hourly_rate,
        },
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_calendar_days": (end_date - start_date).days + 1
        },
        "summary": {
            "present_days": days_present,
            "absent_days": days_absent,
            "leave_days": days_leave,
            "off_days": days_off,
            "holiday_days": days_holiday,
            "total_sessions": total_sessions_count,
            "total_hours": format_hours_display(total_worked_hours),
            "total_hours_value": total_worked_hours,
            "late_arrivals": late_arrivals_count,
            "hourly_rate": hourly_rate,
            "estimated_pay": estimated_pay
        },
        "daily_logs": daily_logs
    }




def build_absent_entries(report_date, request=None):
    """Build synthetic absent rows for active employees who missed the shift."""
    current_time = datetime.now().time()
    today = timezone.now().date()

    active_employees = Employee.objects.filter(status='active')
    attendances = Attendance.objects.filter(date=report_date)
    present_employee_ids = set(attendances.values_list('employee', flat=True).distinct())

    absent_entries = []
    pending_count = 0

    for employee in active_employees:
        if employee.emp_id in present_employee_ids:
            continue

        shift_entry = employee.get_shift_for_date(report_date)
        if not shift_entry or not shift_entry.shift_start_time or not shift_entry.shift_end_time:
            if report_date < today:
                on_leave = PaidLeave.objects.filter(
                    employee=employee,
                    approved=True,
                    start_time__date__lte=report_date,
                    end_time__date__gte=report_date,
                ).exists()
                status_val = "on_leave" if on_leave else "absent"
                absent_entries.append({
                    "id": None,
                    "employee": employee.emp_id,
                    "employee_name": employee.name,
                    "date": report_date,
                    "check_in": None,
                    "check_out": None,
                    "message_late": None,
                    "status": status_val,
                    "total_hours": "0h 0m",
                    "is_late": False,
                    "created_at": None,
                    "updated_at": None,
                })
            else:
                pending_count += 1
            continue

        if report_date < today or (report_date == today and current_time >= shift_entry.shift_end_time):
            on_leave = PaidLeave.objects.filter(
                employee=employee,
                approved=True,
                start_time__date__lte=report_date,
                end_time__date__gte=report_date,
            ).exists()

            status_val = "on_leave" if on_leave else "absent"
            absent_entries.append({
                "id": None,
                "employee": employee.emp_id,
                "employee_name": employee.name,
                "date": report_date,
                "check_in": None,
                "check_out": None,
                "message_late": None,
                "status": status_val,
                "total_hours": "0h 0m",
                "is_late": False,
                "created_at": None,
                "updated_at": None,
            })
        else:
            pending_count += 1

    return absent_entries, pending_count

class IsAdmin(IsAuthenticated):
    """Permission class for admin access"""
    def has_permission(self, request, view):
        return super().has_permission(request, view) and is_admin(request.user)

# Authentication ViewSet
class AuthViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        """Register a new user and create employee profile with image upload"""
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()
            user = result['user']
            employee = result['employee']
            
            log_activity(
                request=request,
                actor=user,
                action_type='register_user',
                category='auth',
                description=f"User registered: '{user.username}' (Employee ID: {employee.emp_id}, Name: {employee.name})",
                target_model='Employee',
                target_id=employee.emp_id,
                target_name=employee.name,
                details={'username': user.username, 'email': user.email, 'emp_id': employee.emp_id}
            )

            return Response({
                "message": "User registered successfully",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name
                },
                "employee": {
                    "emp_id": employee.emp_id,
                    "name": employee.name,
                    "designation": employee.designation,
                    "phone": employee.phone,
                    "CNIC": employee.CNIC,
                    "shift_type": employee.current_shift.name if employee.current_shift else None,
                    "current_shift": employee.current_shift.id if employee.current_shift else None,
                    "current_shift_name": employee.current_shift.name if employee.current_shift else None,
                    "profile_img": f"http://{settings.SERVER_IP}:{settings.SERVER_PORT}{employee.profile_img.url}" if employee.profile_img else None
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    def create_admin_manager(self, request):
        """Create a new admin or manager user with optional profile image (admin only)"""
        serializer = CreateAdminManagerSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            role_val = serializer.validated_data['role']

            log_activity(
                request=request,
                actor=request.user,
                action_type='create_admin_manager',
                category='auth',
                description=f"Admin/Manager '{user.username}' created with role '{role_val}' by '{request.user.username}'",
                target_model='User',
                target_id=user.id,
                target_name=user.username,
                details={'role': role_val, 'username': user.username, 'email': user.email}
            )

            response_data = {
                "message": f"User created successfully as {role_val}",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": role_val,
                    "profile_img": None
                }
            }
            
            # Add profile image URL if it exists
            try:
                user_profile = user.profile
                if user_profile.profile_img:
                    response_data["user"]["profile_img"] = request.build_absolute_uri(user_profile.profile_img.url)
            except:
                pass
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """User login endpoint"""
        from django.contrib.auth import authenticate
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(username=username, password=password)
        if user:
            try:
                # Fetch access level directly from database to get latest data
                access_level = UserAccessLevel.objects.get(user=user)
                role = access_level.role
                log_activity(
                    request=request,
                    actor=user,
                    action_type='login_success',
                    category='auth',
                    description=f"User '{user.username}' logged in successfully as {role}",
                    target_model='User',
                    target_id=user.id,
                    target_name=user.username,
                    details={'role': role, 'user_id': user.id}
                )
                return Response({
                    "message": "Login successful",
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": role
                }, status=status.HTTP_200_OK)
            except UserAccessLevel.DoesNotExist:
                # Try to get employee profile if user has one
                try:
                    employee = user.employee_profile
                    log_activity(
                        request=request,
                        actor=user,
                        action_type='login_success',
                        category='auth',
                        description=f"Employee user '{user.username}' ({employee.name}) logged in successfully",
                        target_model='Employee',
                        target_id=employee.emp_id,
                        target_name=employee.name,
                        details={'role': 'employee', 'emp_id': employee.emp_id, 'user_id': user.id}
                    )
                    return Response({
                        "message": "Login successful",
                        "user_id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "emp_id": employee.emp_id,
                        "name": employee.name,
                        "role": "employee"
                    }, status=status.HTTP_200_OK)
                except Employee.DoesNotExist:
                    log_activity(
                        request=request,
                        actor=user,
                        action_type='login_failed',
                        category='auth',
                        description=f"Login failed: User '{user.username}' has no active profile",
                        target_model='User',
                        target_id=user.id,
                        target_name=user.username,
                        details={'username': user.username, 'reason': 'No profile associated'}
                    )
                    return Response(
                        {"error": "User profile not found"},
                        status=status.HTTP_404_NOT_FOUND
                    )
        
        log_activity(
            request=request,
            actor=None,
            action_type='login_failed',
            category='auth',
            description=f"Failed login attempt for username '{username}'",
            target_model='User',
            target_name=str(username) if username else 'Anonymous',
            details={'attempted_username': username}
        )
        return Response(
            {"error": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """Change current user's password, or admin can change any user's password"""
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_id = serializer.validated_data.get('user_id')
        emp_id = serializer.validated_data.get('emp_id')
        target_username = serializer.validated_data.get('username')

        if (user_id or emp_id or target_username) and is_admin(request.user):
            target_user = None
            if user_id:
                try:
                    target_user = User.objects.get(pk=user_id)
                except User.DoesNotExist:
                    return Response({"error": f"User with id '{user_id}' not found."}, status=status.HTTP_404_NOT_FOUND)
            elif emp_id:
                try:
                    emp = Employee.objects.get(emp_id=emp_id)
                    if not emp.user:
                        return Response({"error": f"Employee '{emp_id}' has no associated user account."}, status=status.HTTP_400_BAD_REQUEST)
                    target_user = emp.user
                except Employee.DoesNotExist:
                    return Response({"error": f"Employee with emp_id '{emp_id}' not found."}, status=status.HTTP_404_NOT_FOUND)
            elif target_username:
                try:
                    target_user = User.objects.get(username=target_username)
                except User.DoesNotExist:
                    return Response({"error": f"User '{target_username}' not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            target_user = request.user
            old_pwd = serializer.validated_data.get('old_password')
            if not old_pwd:
                return Response({"old_password": ["Current password is required."]}, status=status.HTTP_400_BAD_REQUEST)
            if not target_user.check_password(old_pwd):
                return Response({"old_password": ["Current password is incorrect."]}, status=status.HTTP_400_BAD_REQUEST)

        new_pwd = serializer.validated_data['new_password']
        target_user.set_password(new_pwd)
        target_user.save()

        log_activity(
            request=request,
            actor=request.user,
            action_type='password_change',
            category='auth',
            description=f"Password updated for user '{target_user.username}' by '{request.user.username}'",
            target_model='User',
            target_id=target_user.id,
            target_name=target_user.username,
            details={'target_user': target_user.username}
        )

        return Response({
            "message": f"Password for user '{target_user.username}' updated successfully."
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    def update_password(self, request):
        """Admin endpoint to set/update password for any user/employee"""
        serializer = AdminSetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user_id = serializer.validated_data.get('user_id')
        emp_id = serializer.validated_data.get('emp_id')
        target_username = serializer.validated_data.get('username')
        new_pwd = serializer.validated_data['resolved_password']

        target_user = None
        if user_id:
            try:
                target_user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return Response({"error": f"User with id '{user_id}' not found."}, status=status.HTTP_404_NOT_FOUND)
        elif emp_id:
            try:
                emp = Employee.objects.get(emp_id=emp_id)
                if not emp.user:
                    return Response({"error": f"Employee '{emp_id}' has no associated user account."}, status=status.HTTP_400_BAD_REQUEST)
                target_user = emp.user
            except Employee.DoesNotExist:
                return Response({"error": f"Employee with emp_id '{emp_id}' not found."}, status=status.HTTP_404_NOT_FOUND)
        elif target_username:
            try:
                target_user = User.objects.get(username=target_username)
            except User.DoesNotExist:
                return Response({"error": f"User '{target_username}' not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({"error": "Please provide user_id, emp_id, or username."}, status=status.HTTP_400_BAD_REQUEST)

        target_user.set_password(new_pwd)
        target_user.save()

        log_activity(
            request=request,
            actor=request.user,
            action_type='password_reset',
            category='auth',
            description=f"Password reset/updated for user '{target_user.username}' by admin '{request.user.username}'",
            target_model='User',
            target_id=target_user.id,
            target_name=target_user.username,
            details={'target_user': target_user.username}
        )

        return Response({
            "message": f"Password for user '{target_user.username}' updated successfully."
        }, status=status.HTTP_200_OK)


class UserAccessLevelViewSet(viewsets.ModelViewSet):
    """Manage user accounts and access levels (admin/manager)"""
    queryset = UserAccessLevel.objects.all().select_related('user')
    serializer_class = UserAccessLevelSerializer
    permission_classes = [IsAdmin]

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_val = self.kwargs.get(lookup_url_kwarg)
        if lookup_val is not None:
            try:
                return UserAccessLevel.objects.get(pk=lookup_val)
            except (UserAccessLevel.DoesNotExist, ValueError):
                pass
            try:
                return UserAccessLevel.objects.get(Q(user__id=lookup_val) | Q(user__username=lookup_val))
            except (UserAccessLevel.DoesNotExist, ValueError):
                pass
        return super().get_object()

    def perform_create(self, serializer):
        instance = serializer.save()
        username = instance.user.username if instance.user else 'Unknown'
        log_activity(
            request=self.request,
            actor=self.request.user,
            action_type='user_create',
            category='user',
            description=f"Created portal user '{username}' with role '{instance.role}'",
            target_model='UserAccessLevel',
            target_id=instance.id,
            target_name=username,
            details={'username': username, 'role': instance.role}
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        old_role = instance.role
        kwargs['partial'] = True
        response = super().update(request, *args, **kwargs)
        if response.status_code < 400:
            instance.refresh_from_db()
            role_changed = old_role != instance.role
            action_type = 'role_change' if role_changed else 'user_update'
            username = instance.user.username if instance.user else 'Unknown'
            desc = f"Updated role for user '{username}' from '{old_role}' to '{instance.role}'" if role_changed else f"Updated user details for '{username}'"
            log_activity(
                request=request,
                actor=request.user,
                action_type=action_type,
                category='user',
                description=desc,
                target_model='UserAccessLevel',
                target_id=instance.id,
                target_name=username,
                details={'old_role': old_role, 'new_role': instance.role, 'username': username}
            )
        return response

    def perform_destroy(self, instance):
        username = instance.user.username if instance.user else 'Unknown'
        role = instance.role
        log_activity(
            request=self.request,
            actor=self.request.user,
            action_type='user_delete',
            category='user',
            description=f"Deleted user access level / account for '{username}' (role: {role})",
            target_model='UserAccessLevel',
            target_id=instance.id,
            target_name=username,
            details={'username': username, 'role': role}
        )
        instance.delete()

    @action(detail=False, methods=['get'])
    def admins(self, request):
        """Get all admin users"""
        admins = UserAccessLevel.objects.filter(role='admin')
        serializer = self.get_serializer(admins, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def managers(self, request):
        """Get all manager users"""
        managers = UserAccessLevel.objects.filter(role='manager')
        serializer = self.get_serializer(managers, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def change_password(self, request, pk=None):
        """Change password for this user: POST /api/users/{id}/change_password/ or /api/access-levels/{id}/change_password/"""
        ual = self.get_object()
        user = ual.user
        pwd = request.data.get('password') or request.data.get('new_password')
        if not pwd or len(str(pwd)) < 8:
            return Response({"password": ["Password must be at least 8 characters long."]}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(str(pwd))
        user.save()
        log_activity(
            request=request,
            actor=request.user,
            action_type='password_change',
            category='auth',
            description=f"Admin '{request.user.username}' changed password for user '{user.username}'",
            target_model='User',
            target_id=user.id,
            target_name=user.username,
            details={'target_user': user.username}
        )
        return Response({"message": f"Password for user '{user.username}' updated successfully."}, status=status.HTTP_200_OK)


# Filtering logic for Attendance
class AttendanceFilter(filters.FilterSet):
    date_from = filters.DateFilter(field_name="date", lookup_expr='gte')
    date_to = filters.DateFilter(field_name="date", lookup_expr='lte')
    employee = filters.CharFilter(field_name="employee__emp_id")
    status = filters.CharFilter(field_name="status")
    search = filters.CharFilter(method='filter_search')

    class Meta:
        model = Attendance
        fields = ['employee', 'date_from', 'date_to', 'status', 'search']

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(employee__name__icontains=value) |
            Q(employee__emp_id__icontains=value)
        )

class EmployeeFilter(filters.FilterSet):
    employee_id = filters.NumberFilter(field_name="emp_id", lookup_expr='exact')
    employee_name = filters.CharFilter(field_name="name", lookup_expr='icontains')
    status = filters.CharFilter(field_name="status")
    current_shift = filters.NumberFilter(field_name="current_shift__id")

    class Meta:
        model = Employee
        fields = ['employee_id', 'employee_name', 'status', 'current_shift']

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all().order_by('emp_id')
    serializer_class = EmployeeSerializer
    filterset_class = EmployeeFilter
    filter_backends = (filters.DjangoFilterBackend,)
    lookup_field = 'emp_id'  # Use emp_id for URL lookups like /employees/EMP001/
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        employee = serializer.save()
        log_activity(
            request=self.request,
            actor=self.request.user,
            action_type='employee_create',
            category='employee',
            description=f"Created employee '{employee.name}' (ID: {employee.emp_id}, Designation: {employee.designation or 'N/A'})",
            target_model='Employee',
            target_id=employee.emp_id,
            target_name=employee.name,
            details={
                'emp_id': employee.emp_id,
                'name': employee.name,
                'designation': employee.designation,
                'status': employee.status,
                'current_shift': employee.current_shift.name if employee.current_shift else None
            }
        )

    def update(self, request, *args, **kwargs):
        emp_before = self.get_object()
        old_status = emp_before.status
        kwargs['partial'] = True
        # Perform the update first
        response = super().update(request, *args, **kwargs)

        if response.status_code < 400:
            emp = self.get_object()
            new_status = emp.status

            # If status was set to inactive during this update, record who deactivated and when
            if old_status != 'inactive' and new_status == 'inactive':
                try:
                    if not emp.deactivated_at:
                        emp.deactivated_by = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
                        emp.deactivated_at = timezone.now()
                        emp.save(update_fields=['deactivated_by', 'deactivated_at'])
                except Exception:
                    pass

                log_activity(
                    request=request,
                    actor=request.user,
                    action_type='employee_deactivate',
                    category='employee',
                    description=f"Deactivated employee '{emp.name}' (ID: {emp.emp_id})",
                    target_model='Employee',
                    target_id=emp.emp_id,
                    target_name=emp.name,
                    details={'emp_id': emp.emp_id, 'name': emp.name, 'previous_status': old_status, 'new_status': new_status}
                )
            elif old_status == 'inactive' and new_status == 'active':
                try:
                    emp.deactivated_by = None
                    emp.deactivated_at = None
                    emp.save(update_fields=['deactivated_by', 'deactivated_at'])
                except Exception:
                    pass

                log_activity(
                    request=request,
                    actor=request.user,
                    action_type='employee_activate',
                    category='employee',
                    description=f"Reactivated employee '{emp.name}' (ID: {emp.emp_id})",
                    target_model='Employee',
                    target_id=emp.emp_id,
                    target_name=emp.name,
                    details={'emp_id': emp.emp_id, 'name': emp.name, 'previous_status': old_status, 'new_status': new_status}
                )
            else:
                log_activity(
                    request=request,
                    actor=request.user,
                    action_type='employee_update',
                    category='employee',
                    description=f"Updated employee '{emp.name}' (ID: {emp.emp_id})",
                    target_model='Employee',
                    target_id=emp.emp_id,
                    target_name=emp.name,
                    details={'emp_id': emp.emp_id, 'name': emp.name, 'status': new_status}
                )

        return response

    def perform_destroy(self, instance):
        emp_id = instance.emp_id
        emp_name = instance.name
        log_activity(
            request=self.request,
            actor=self.request.user,
            action_type='employee_delete',
            category='employee',
            description=f"Deleted employee '{emp_name}' (ID: {emp_id})",
            target_model='Employee',
            target_id=emp_id,
            target_name=emp_name,
            details={'emp_id': emp_id, 'name': emp_name}
        )
        instance.delete()

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def change_password(self, request, emp_id=None):
        """Change password for an employee's user account"""
        employee = self.get_object()
        if not employee.user:
            return Response({"error": "This employee does not have an associated user account."}, status=status.HTTP_400_BAD_REQUEST)
        pwd = request.data.get('password') or request.data.get('new_password')
        if not pwd or len(str(pwd)) < 8:
            return Response({"password": ["Password must be at least 8 characters long."]}, status=status.HTTP_400_BAD_REQUEST)
        employee.user.set_password(str(pwd))
        employee.user.save()
        log_activity(
            request=request,
            actor=request.user,
            action_type='password_change',
            category='auth',
            description=f"Admin '{request.user.username}' changed password for employee '{employee.name}' (User: {employee.user.username})",
            target_model='Employee',
            target_id=employee.emp_id,
            target_name=employee.name,
            details={'emp_id': employee.emp_id, 'username': employee.user.username}
        )
        return Response({"message": f"Password for employee '{employee.name}' updated successfully."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def calculate_payout(self, request, emp_id=None):
        """Calculates salary based on shift history, attendance, holidays, leaves, and overtime."""
        employee = self.get_object()
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not start_date or not end_date:
            return Response(
                {"error": "Please provide start_date and end_date (YYYY-MM-DD)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if start_date > end_date:
            return Response(
                {"error": "start_date must be before end_date"},
                status=status.HTTP_400_BAD_REQUEST
            )

        def days_in_month(d):
            if d.month == 12:
                return (date(d.year + 1, 1, 1) - date(d.year, 12, 1)).days
            return (date(d.year, d.month + 1, 1) - date(d.year, d.month, 1)).days

        def month_days_for_period(p_start, p_end):
            total = 0
            current = p_start
            while current <= p_end:
                total += days_in_month(current)
                current = date(current.year, current.month + 1, 1)
            return total / ((p_end - p_start).days + 1) if p_start == p_end else total

        shift_entries = EmployeeShiftHistory.objects.filter(
            employee=employee,
            from_date__lte=end_date
        ).filter(
            Q(to_date__isnull=True) | Q(to_date__gte=start_date)
        ).order_by('from_date')

        total_payout = 0.0
        total_present_days = 0
        total_absent_days = 0
        total_holiday_pay = 0.0
        total_leave_pay = 0.0
        total_off_day_pay = 0.0
        total_overtime_pay = 0.0
        periods_data = []
        weekly_off = employee.weekly_off_day

        for entry in shift_entries:
            period_start = max(entry.from_date, start_date)
            period_end = entry.to_date if entry.to_date and entry.to_date < end_date else end_date

            if period_start > period_end:
                continue

            shift = entry.shift
            if not shift:
                continue

            shift_start_time = entry.shift_start_time or shift.start_time
            shift_end_time = entry.shift_end_time or shift.end_time
            if not shift_start_time or not shift_end_time:
                continue
            shift_seconds = (datetime.combine(date.today(), shift_end_time) -
                             datetime.combine(date.today(), shift_start_time)).total_seconds()
            if shift_seconds <= 0:
                shift_seconds += 86400  # cross-midnight
            shift_hours = shift_seconds / 3600

            period_days = (period_end - period_start).days + 1
            weekly_off_count = 0
            if weekly_off is not None:
                d = period_start
                while d <= period_end:
                    if d.weekday() == weekly_off:
                        weekly_off_count += 1
                    d += timedelta(days=1)

            working_days = period_days - weekly_off_count
            expected_hours = working_days * shift_hours

            # Calculate salary portion based on month days
            monthly_days = month_days_for_period(period_start, period_end)
            salary_value = float(get_salary_for_date(employee, period_start) or entry.salary or 0)
            salary_portion = salary_value * (period_days / monthly_days) if monthly_days > 0 else 0
            hourly_rate = salary_portion / expected_hours if expected_hours > 0 else 0

            period_present = 0
            period_absent = 0
            period_holiday_pay = 0.0
            period_leave_pay = 0.0
            period_off_day_pay = 0.0
            period_overtime_pay = 0.0
            period_regular_pay = 0.0
            period_worked_hours = 0.0

            holidays = {h.date: h for h in Holiday.objects.filter(
                date__gte=period_start, date__lte=period_end, is_paid=True
            )}

            overtimes = {
                (ot.date, ot.start_time): ot
                for ot in Overtime.objects.filter(
                    employee=employee,
                    date__gte=period_start,
                    date__lte=period_end,
                    status='approved'
                )
            }

            attendances = Attendance.objects.filter(
                employee=employee,
                date__gte=period_start,
                date__lte=period_end
            )
            att_map = {}
            for att in attendances:
                if att.date not in att_map:
                    att_map[att.date] = []
                att_map[att.date].append(att)

            leaves = {
                (l.start_time.date(), l.end_time.date())
                for l in PaidLeave.objects.filter(
                    employee=employee,
                    approved=True,
                    start_time__date__lte=period_end,
                    end_time__date__gte=period_start
                )
            }

            current = period_start
            while current <= period_end:
                is_off_day = (weekly_off is not None and current.weekday() == weekly_off)
                is_holiday = current in holidays
                is_on_leave = any(l_start <= current <= l_end for l_start, l_end in leaves)

                daily_overtime_pay = 0.0
                for (ot_date, ot_time), ot in overtimes.items():
                    if ot_date == current:
                        daily_overtime_pay += float(ot.total_hours) * hourly_rate

                if current in att_map:
                    day_atts = att_map[current]
                    day_hours = sum(a.total_hours for a in day_atts)
                    period_worked_hours += day_hours
                    period_regular_pay += day_hours * hourly_rate
                    period_present += 1
                elif is_off_day:
                    period_off_day_pay += shift_hours * hourly_rate
                    period_worked_hours += shift_hours
                elif is_holiday:
                    period_holiday_pay += shift_hours * hourly_rate
                elif is_on_leave:
                    period_leave_pay += shift_hours * hourly_rate
                else:
                    period_absent += 1

                if daily_overtime_pay > 0:
                    period_overtime_pay += daily_overtime_pay

                current += timedelta(days=1)

            period_total = period_regular_pay + period_holiday_pay + period_leave_pay + period_off_day_pay + period_overtime_pay
            total_payout += period_total
            total_present_days += period_present
            total_absent_days += period_absent
            total_holiday_pay += period_holiday_pay
            total_leave_pay += period_leave_pay
            total_off_day_pay += period_off_day_pay
            total_overtime_pay += period_overtime_pay

            periods_data.append({
                "shift_name": shift.name,
                "from_date": str(period_start),
                "to_date": str(period_end),
                "days_in_period": period_days,
                "weekly_off_days": weekly_off_count,
                "working_days": working_days,
                "expected_hours": round(expected_hours, 2),
                "salary_portion": round(salary_portion, 2),
                "hourly_rate": round(hourly_rate, 2),
                "present_days": period_present,
                "absent_days": period_absent,
                "total_worked_hours": round(period_worked_hours, 2),
                "regular_pay": round(period_regular_pay, 2),
                "holiday_pay": round(period_holiday_pay, 2),
                "leave_pay": round(period_leave_pay, 2),
                "off_day_pay": round(period_off_day_pay, 2),
                "overtime_pay": round(period_overtime_pay, 2),
                "total_pay": round(period_total, 2),
            })

        return Response({
            "employee_id": employee.emp_id,
            "employee_name": employee.name,
            "period": f"{start_date} to {end_date}",
            "salary": float(employee.salary or 0),
            "shift_periods": periods_data,
            "total_present_days": total_present_days,
            "total_absent_days": total_absent_days,
            "total_holiday_pay": round(total_holiday_pay, 2),
            "total_leave_pay": round(total_leave_pay, 2),
            "total_off_day_pay": round(total_off_day_pay, 2),
            "total_overtime_pay": round(total_overtime_pay, 2),
            "total_payout": round(total_payout, 2),
        })

    @action(detail=True, methods=['get'])
    def attendance_report(self, request, emp_id=None):
        """Get attendance report for an employee with filters"""
        employee = self.get_object()
        period = request.query_params.get('period', 'month')  # day, week, month, custom

        # If explicit start_date and end_date provided, prefer them regardless of `period`
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        if start_date_str or end_date_str:
            if not start_date_str or not end_date_str:
                return Response({"error": "Please provide both start_date and end_date (YYYY-MM-DD)"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            today = timezone.now().date()
            if period == 'day':
                start_date = today
                end_date = today
            elif period == 'week':
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=6)
            elif period == 'month':
                start_date = date(today.year, today.month, 1)
                if today.month == 12:
                    end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
            elif period == 'custom':
                # custom without explicit dates is invalid
                return Response({"error": "Please provide start_date and end_date for custom period"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"error": "Invalid period. Use: day, week, month, or custom"}, status=status.HTTP_400_BAD_REQUEST)

        attendances = Attendance.objects.filter(
            employee=employee,
            date__range=[start_date, end_date]
        ).order_by('-date')

        total_hours = round(sum(att.total_hours for att in attendances), 2)
        total_days = attendances.count()
        late_count = attendances.filter(status='late').count()
        on_time_count = attendances.filter(status='on_time').count()

        return Response({
            "employee_id": employee.emp_id,
            "employee_name": employee.name,
            "period": f"{start_date} to {end_date}",
            "total_days_worked": total_days,
            "total_hours": format_hours_display(total_hours),
            "total_hours_value": total_hours,
            "on_time": on_time_count,
            "late": late_count,
            "attendance_records": AttendanceSerializer(attendances, many=True).data
        })

    @action(detail=True, methods=['get'])
    def detailed_logs(self, request, *args, **kwargs):
        """Get complete, detailed attendance session breakdown for this employee on a date or date range."""
        employee = self.get_object()
        start_date, end_date, err = parse_date_range_params(request)
        if err:
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)
        data = build_employee_detailed_logs(employee, start_date, end_date)
        return Response(data)

    @action(detail=False, methods=['get'])
    def active_employees(self, request):
        """Get list of active employees"""
        employees = Employee.objects.filter(status='active')
        serializer = self.get_serializer(employees, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def employee_stats(self, request):
        """Get overall employee statistics"""
        total_employees = Employee.objects.count()
        active_employees = Employee.objects.filter(status='active').count()
        inactive_employees = Employee.objects.filter(status='inactive').count()
        
        today = timezone.now().date()
        present_today = Attendance.objects.filter(date=today).values('employee').distinct().count()
        
        return Response({
            "total_employees": total_employees,
            "active_employees": active_employees,
            "inactive_employees": inactive_employees,
            "present_today": present_today
        })

    @action(detail=False, methods=['get', 'post'], url_path='relatives')
    def relatives(self, request):
        """Get or set relatives for an employee.

        GET params:
        - emp_id (required): employee emp_id to query
        - transitive (optional): 'true' to return full connected relatives graph
        - name (optional): filter relatives by name (icontains)

        POST body (json):
        - emp_id (required): employee emp_id to update
        - relatives: comma-separated string of emp_id values OR list of ints

        Response: single variable `relatives` containing list of relatives (dicts).
        """
        if request.method == 'GET':
            emp_id = request.query_params.get('emp_id') or request.query_params.get('employee')
        else:
            emp_id = request.data.get('emp_id')

        if not emp_id:
            return Response({"error": "Please provide emp_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            employee = Employee.objects.get(emp_id=emp_id)
        except Employee.DoesNotExist:
            return Response({"error": f"Employee with id {emp_id} not found"}, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'POST':
            # accept comma-separated string or list of emp_id values or numeric PKs
            raw = request.data.get('relatives', '')
            rel_inputs = []
            if isinstance(raw, str):
                raw = raw.strip()
                if raw:
                    rel_inputs = [x.strip() for x in raw.split(',') if x.strip()]
            elif isinstance(raw, (list, tuple)):
                rel_inputs = [x for x in raw if x is not None]

            # Normalize inputs to emp_id values where possible
            resolved_emp_ids = []
            for v in rel_inputs:
                vs = str(v).strip()
                # try emp_id lookup first
                try:
                    obj = Employee.objects.get(emp_id=vs)
                    resolved_emp_ids.append(obj.emp_id)
                    continue
                except Employee.DoesNotExist:
                    pass
                # try pk lookup
                if vs.isdigit():
                    try:
                        obj = Employee.objects.get(pk=int(vs))
                        resolved_emp_ids.append(obj.emp_id)
                        continue
                    except Employee.DoesNotExist:
                        pass

            # Save comma-separated into legacy `relative` field (store emp_id values)
            employee.relative = ','.join(resolved_emp_ids)
            employee.save()

            # Update M2M relations using emp_id values
            relatives_qs = Employee.objects.filter(emp_id__in=resolved_emp_ids)
            employee.relatives.set(relatives_qs)

            # Prepare response (use emp_id as the identifier)
            data_qs = relatives_qs.order_by('emp_id')
            data = [{"emp_id": r.emp_id, "name": r.name} for r in data_qs]
            return Response({"relatives": data})

        # GET handling
        transitive = str(request.query_params.get('transitive', '')).lower() in ('1', 'true', 'yes')
        name_filter = request.query_params.get('name')

        if not transitive:
            relatives_qs = employee.relatives.all()
        else:
            visited = set()
            queue = [employee]
            visited.add(employee.pk)
            collected = set()
            while queue:
                current = queue.pop(0)
                for r in current.relatives.all():
                    if r.pk not in visited:
                        visited.add(r.pk)
                        queue.append(r)
                    if r.pk != employee.pk:
                        collected.add(r.pk)
            relatives_qs = Employee.objects.filter(pk__in=collected)

        if name_filter:
            relatives_qs = relatives_qs.filter(name__icontains=name_filter)

        data = [{"emp_id": r.emp_id, "name": r.name} for r in relatives_qs.order_by('emp_id')]
        return Response({"relatives": data})

    @action(detail=True, methods=['get', 'post'])
    def assign_shift(self, request, emp_id=None):
        """Get or assign a shift for an employee.

        GET: returns current active shift assignment.
        POST body: {"shift_id": <id>, "from_date": "YYYY-MM-DD"}
        """
        employee = self.get_object()

        if request.method == 'GET':
            active = employee.get_active_shift_entry()
            if active:
                serializer = EmployeeShiftHistorySerializer(active)
                return Response(serializer.data)
            return Response({"detail": "No active shift assignment found."})

        shift_id = request.data.get('shift_id')
        from_date_str = request.data.get('from_date')

        if not shift_id or not from_date_str:
            return Response(
                {"error": "shift_id and from_date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Invalid from_date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            shift = Shift.objects.get(id=shift_id)
        except Shift.DoesNotExist:
            return Response(
                {"error": f"Shift with id {shift_id} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Close current active shift
        current_active = employee.get_active_shift_entry()
        if current_active:
            current_active.close(from_date)

        # Create new shift assignment
        history_entry = EmployeeShiftHistory.objects.create(
            employee=employee,
            shift=shift,
            from_date=from_date,
            to_date=None,
            salary=employee.salary,
            shift_start_time=shift.start_time,
            shift_end_time=shift.end_time,
        )

        # Update employee's current_shift
        employee.current_shift = shift
        employee.save(update_fields=['current_shift'])

        log_activity(
            request=request,
            actor=request.user,
            action_type='shift_assign',
            category='shift',
            description=f"Assigned shift '{shift.name}' to employee '{employee.name}' (Effective: {from_date})",
            target_model='Employee',
            target_id=employee.emp_id,
            target_name=employee.name,
            details={'emp_id': employee.emp_id, 'shift_id': shift.id, 'shift_name': shift.name, 'from_date': str(from_date)}
        )

        serializer = EmployeeShiftHistorySerializer(history_entry)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get', 'post'])
    def salary(self, request, emp_id=None):
        """Get salary history or create a new salary record for an employee.

        GET: returns all salary records for the employee.
        POST body: {"salary": 50000, "effective_from": "YYYY-MM-DD"}
        """
        employee = self.get_object()

        if request.method == 'GET':
            salaries = Salary.objects.filter(employee=employee).order_by('-effective_from')
            serializer = SalarySerializer(salaries, many=True)
            return Response(serializer.data)

        salary_val = request.data.get('salary')
        effective_from_str = request.data.get('effective_from')

        if not salary_val or not effective_from_str:
            return Response(
                {"error": "salary and effective_from are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            effective_from = datetime.strptime(effective_from_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Invalid effective_from format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            salary_val = Decimal(str(salary_val))
        except Exception:
            return Response(
                {"error": "Invalid salary value"},
                status=status.HTTP_400_BAD_REQUEST
            )

        salary_entry = Salary(
            employee=employee,
            salary=salary_val,
            effective_from=effective_from,
        )
        salary_entry.save()

        log_activity(
            request=request,
            actor=request.user,
            action_type='salary_update',
            category='salary',
            description=f"Updated salary for employee '{employee.name}' to {salary_val} (Effective: {effective_from})",
            target_model='Employee',
            target_id=employee.emp_id,
            target_name=employee.name,
            details={'emp_id': employee.emp_id, 'salary': float(salary_val), 'effective_from': str(effective_from)}
        )

        serializer = SalarySerializer(salary_entry)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def shift_history(self, request, emp_id=None):
        """Get all shift assignments for an employee."""
        employee = self.get_object()
        history = EmployeeShiftHistory.objects.filter(employee=employee).order_by('-from_date')
        serializer = EmployeeShiftHistorySerializer(history, many=True)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def employee_list(request):
    """Return a simple list of all employees with `id` (emp_id) and `name`.

    No pagination is applied - returns the full list.
    The `id` field equals the employee `emp_id` as requested.
    """
    employees = Employee.objects.all().order_by('emp_id')
    data = [{"emp_id": e.emp_id, "name": e.name} for e in employees]
    return Response(data)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all().order_by('date')
    serializer_class = AttendanceSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = AttendanceFilter
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def perform_create(self, serializer):
        att = serializer.save()
        emp_name = att.employee.name if att.employee else 'Unknown'
        emp_id = att.employee.emp_id if att.employee else None
        log_activity(
            request=self.request,
            actor=self.request.user,
            action_type='attendance_manual_create',
            category='attendance',
            description=f"Manual attendance created for '{emp_name}' (ID: {emp_id}) on {att.date}",
            target_model='Attendance',
            target_id=att.id,
            target_name=emp_name,
            details={
                'emp_id': emp_id,
                'date': str(att.date),
                'check_in': str(att.check_in) if att.check_in else None,
                'check_out': str(att.check_out) if att.check_out else None,
                'status': att.status
            }
        )

    def perform_update(self, serializer):
        att = serializer.save()
        emp_name = att.employee.name if att.employee else 'Unknown'
        emp_id = att.employee.emp_id if att.employee else None
        log_activity(
            request=self.request,
            actor=self.request.user,
            action_type='attendance_update',
            category='attendance',
            description=f"Attendance updated for '{emp_name}' (ID: {emp_id}) on {att.date}",
            target_model='Attendance',
            target_id=att.id,
            target_name=emp_name,
            details={
                'emp_id': emp_id,
                'date': str(att.date),
                'check_in': str(att.check_in) if att.check_in else None,
                'check_out': str(att.check_out) if att.check_out else None,
                'status': att.status
            }
        )

    def perform_destroy(self, instance):
        att_id = instance.id
        emp_name = instance.employee.name if instance.employee else 'Unknown'
        emp_id = instance.employee.emp_id if instance.employee else None
        att_date = instance.date
        log_activity(
            request=self.request,
            actor=self.request.user,
            action_type='attendance_delete',
            category='attendance',
            description=f"Attendance deleted for '{emp_name}' (ID: {emp_id}) on {att_date}",
            target_model='Attendance',
            target_id=att_id,
            target_name=emp_name,
            details={'emp_id': emp_id, 'date': str(att_date)}
        )
        instance.delete()

    def list(self, request, *args, **kwargs):
        """Return attendance list with filters (date, date_from/date_to, employee, status).

        - If `date` is provided (single day) we include synthetic absent rows after shift end.
        - Otherwise use DRF filters (`AttendanceFilter`) and support pagination.
        """
        date_str = request.query_params.get('date')

        # Start with DRF-filtered queryset so filters like employee, date_from/date_to, status apply
        qs = self.filter_queryset(self.get_queryset())

        # Single-date behavior: include absent entries and day-level summary
        if date_str:
            try:
                report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Invalid date format"}, status=status.HTTP_400_BAD_REQUEST)

            attendances = qs.filter(date=report_date).order_by('employee', 'check_in')

            # Group attendances by employee so each present employee appears once with first IN, last OUT, and summed hours
            grouped_atts = {}
            for att in attendances:
                grouped_atts.setdefault(att.employee.emp_id, []).append(att)

            present_results = []
            for emp_id_val, att_list in grouped_atts.items():
                first_att = att_list[0]
                last_att = att_list[-1]
                day_total_hours = round(sum(a.total_hours for a in att_list), 2)
                is_late_val = any(a.status == 'late' for a in att_list)
                status_val = 'late' if is_late_val else 'on_time'

                present_results.append({
                    "id": first_att.id,
                    "employee": first_att.employee.emp_id,
                    "employee_name": first_att.employee.name,
                    "date": report_date.isoformat(),
                    "check_in": first_att.check_in.strftime('%I:%M:%S %p') if first_att.check_in else None,
                    "check_out": last_att.check_out.strftime('%I:%M:%S %p') if last_att.check_out else None,
                    "message_late": first_att.message_late,
                    "status": status_val,
                    "total_hours": format_hours_display(day_total_hours),
                    "total_hours_value": day_total_hours,
                    "sessions_count": len(att_list),
                    "is_late": is_late_val,
                    "created_at": first_att.created_at,
                    "updated_at": last_att.updated_at,
                })

            absent_entries, pending_count = build_absent_entries(report_date, request=request)
            results = present_results + absent_entries

            # Include any inactive-attendance attempts logged for this date
            inactive_attempts_qs = InactiveAttendanceAttempt.objects.filter(attempted_at__date=report_date)
            inactive_entries = []
            for att in inactive_attempts_qs.select_related('employee', 'attempted_by'):
                attempted_by = att.attempted_by.username if att.attempted_by else None
                msg = att.message or f"Attempted attendance while inactive by {attempted_by or 'unknown'}"
                deact_by = att.deactivated_by_username or (att.employee.deactivated_by.username if getattr(att.employee, 'deactivated_by', None) else None)
                inactive_entries.append({
                    "id": None,
                    "employee": att.employee.emp_id,
                    "employee_name": att.employee.name,
                    "date": report_date,
                    "check_in": None,
                    "check_out": None,
                    "message_late": msg,
                    "status": "inactive",
                    "total_hours": "0h 0m",
                    "is_late": False,
                    "created_at": att.attempted_at,
                    "updated_at": None,
                    "attempted_by": attempted_by,
                    "deactivated_by": deact_by,
                })

            results += inactive_entries
            present_count = attendances.values('employee').distinct().count()
            absent_count = len(absent_entries)
            inactive_count = len(inactive_entries)
            late_count = attendances.filter(status='late').values('employee').distinct().count()
            on_time_count = max(0, present_count - late_count)
            total_hours = round(sum(att.total_hours for att in attendances), 2)

            return Response({
                "date": report_date,
                "present": present_count,
                "absent": absent_count,
                "inactive_attempts": inactive_count,
                "pending": pending_count,
                "on_time": on_time_count,
                "late": late_count,
                "total_hours": format_hours_display(total_hours),
                "total_hours_value": total_hours,
                "count": len(results),
                "results": results,
            })

        # Multi-day / filtered list: use filtered queryset and support pagination
        queryset = qs.order_by('date', 'employee', 'check_in')

        # Compute aggregates on full queryset (not just page)
        total_hours = round(sum(att.total_hours for att in queryset), 2)
        present_count = queryset.values('employee').distinct().count()
        total_count = queryset.count()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AttendanceSerializer(page, many=True, context={'request': request})
            paginated = self.get_paginated_response(serializer.data).data
            # augment paginated response with summary fields
            paginated.update({
                "present": present_count,
                "total_hours": format_hours_display(total_hours),
                "total_hours_value": total_hours,
                "total_count": total_count,
            })
            return Response(paginated)

        serializer = AttendanceSerializer(queryset, many=True, context={'request': request})
        return Response({
            "present": present_count,
            "total_hours": format_hours_display(total_hours),
            "total_hours_value": total_hours,
            "count": total_count,
            "results": serializer.data,
        })

    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """Export attendance matrix to Excel: rows=dates, columns=employees.

        Query params:
        - date_from (YYYY-MM-DD) required
        - date_to (YYYY-MM-DD) required
        - employees: optional comma-separated emp_id list; defaults to active employees
        - employee: optional single emp_id to export for a specific employee
        """
        if openpyxl is None:
            return Response({"error": "openpyxl is required to export Excel. Please pip install openpyxl."}, status=500)

        start = request.query_params.get('date_from')
        end = request.query_params.get('date_to')
        if not start or not end:
            return Response({"error": "Please provide date_from and date_to in YYYY-MM-DD"}, status=400)
        try:
            start_date = datetime.strptime(start, '%Y-%m-%d').date()
            end_date = datetime.strptime(end, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=400)

        # Accept either `employee` (single emp_id) or `employees` (comma-separated)
        emp_single = request.query_params.get('employee')
        emp_param = request.query_params.get('employees')
        if emp_single and str(emp_single).strip().isdigit():
            employees = list(Employee.objects.filter(emp_id=int(emp_single)).order_by('emp_id'))
        elif emp_param:
            emp_ids = [int(x.strip()) for x in emp_param.split(',') if x.strip().isdigit()]
            employees = list(Employee.objects.filter(emp_id__in=emp_ids).order_by('emp_id'))
        else:
            employees = list(Employee.objects.filter(status='active').order_by('emp_id'))

        # Build workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Attendance'

        # Header row: Date + for each employee a single column with "CheckIn - CheckOut"
        headers = ['Date']
        for e in employees:
            label = e.name or str(e.emp_id)
            headers.append(f"{label} (In - Out)")

        for col_idx, head in enumerate(headers, start=1):
            ws.cell(row=1, column=col_idx, value=head)

        # Fill rows per date
        row = 2
        delta = (end_date - start_date).days
        # Use current time to decide whether a day should be considered absent or still pending
        current_time = datetime.now().time()
        today = timezone.now().date()

        for d_offset in range(delta + 1):
            rdate = start_date + timedelta(days=d_offset)
            ws.cell(row=row, column=1, value=rdate.strftime('%Y-%m-%d'))

            # for each employee write a single cell with "CheckIn - CheckOut"
            for idx, emp in enumerate(employees):
                col = 2 + idx
                # Find attendances for this employee on the row date, either by stored
                atts = Attendance.objects.filter(employee=emp, date=rdate).order_by('check_in')

                check_in_val = "--:--"
                check_out_val = "--:--"
                if atts.exists():
                    first = atts.first()
                    last = atts.last()
                    if first.check_in:
                        try:
                            check_in_val = first.check_in.strftime('%I:%M %p')
                        except Exception:
                            check_in_val = str(first.check_in)
                    if last.check_out:
                        try:
                            check_out_val = last.check_out.strftime('%I:%M %p')
                        except Exception:
                            check_out_val = str(last.check_out)

                if atts.exists():
                    if atts.count() > 1:
                        session_lines = []
                        for i, a in enumerate(atts):
                            ci = a.check_in.strftime('%I:%M %p') if a.check_in else '--:--'
                            co = a.check_out.strftime('%I:%M %p') if a.check_out else '--:--'
                            session_lines.append(f"#{i+1}: {ci} - {co}")
                        combined = "\n".join(session_lines)
                        ws.cell(row=row, column=col).alignment = openpyxl.styles.Alignment(horizontal='center', vertical='center', wrap_text=True)
                        ws.row_dimensions[row].height = max(20, 15 * len(session_lines) + 6)
                    else:
                        first = atts.first()
                        ci = first.check_in.strftime('%I:%M %p') if first.check_in else '--:--'
                        co = first.check_out.strftime('%I:%M %p') if first.check_out else '--:--'
                        combined = f"{ci} - {co}"
                else:
                    # If no attendance, check for approved paid leave covering the date
                    leave = PaidLeave.objects.filter(
                        employee=emp,
                        approved=True,
                        start_time__date__lte=rdate,
                        end_time__date__gte=rdate,
                    ).first()
                    if leave:
                        combined = "Leave"
                    else:
                        holiday = Holiday.objects.filter(date=rdate).first()
                        if holiday:
                            combined = f"Holiday ({holiday.name})"
                        elif emp.weekly_off_day is not None and rdate.weekday() == emp.weekly_off_day:
                            combined = "Off Day"
                        else:
                            s_start, s_end = get_employee_shift_times(emp, rdate)
                            if not s_start or not s_end:
                                if rdate < today:
                                    combined = "Absent"
                                else:
                                    combined = f"{check_in_val} - {check_out_val}"
                            else:
                                if rdate < today or (rdate == today and current_time >= s_end):
                                    combined = "Absent"
                                else:
                                    combined = f"{check_in_val} - {check_out_val}"

                ws.cell(row=row, column=col, value=combined)

            row += 1

        # Auto-fit column widths (simple heuristic)
        for i, column_cells in enumerate(ws.columns, start=1):
            max_length = 0
            for cell in column_cells:
                try:
                    val = str(cell.value) if cell.value is not None else ''
                except Exception:
                    val = ''
                if len(val) > max_length:
                    max_length = len(val)
            ws.column_dimensions[get_column_letter(i)].width = min(max_length + 2, 50)

        # Save to bytes
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f"attendance_{start}_{end}.xlsx"
        resp = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp['Content-Disposition'] = f'attachment; filename="{filename}"'
        return resp

    @action(detail=False, methods=['get'])
    def export_payout(self, request):
        """Export attendance matrix with payout row: last row contains salary = total_hours * hourly_rate

        Query params:
        - date_from (YYYY-MM-DD) required
        - date_to (YYYY-MM-DD) required
        - employees: optional comma-separated emp_id list; defaults to active employees
        - employee: optional single emp_id to export for a specific employee
        """
        if openpyxl is None:
            return Response({"error": "openpyxl is required to export Excel. Please pip install openpyxl."}, status=500)

        start = request.query_params.get('date_from')
        end = request.query_params.get('date_to')
        if not start or not end:
            return Response({"error": "Please provide date_from and date_to in YYYY-MM-DD"}, status=400)
        try:
            start_date = datetime.strptime(start, '%Y-%m-%d').date()
            end_date = datetime.strptime(end, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=400)

        # Accept either `employee` (single emp_id) or `employees` (comma-separated)
        emp_single = request.query_params.get('employee')
        emp_param = request.query_params.get('employees')
        if emp_single and str(emp_single).strip().isdigit():
            employees = list(Employee.objects.filter(emp_id=int(emp_single)).order_by('emp_id'))
        elif emp_param:
            emp_ids = [int(x.strip()) for x in emp_param.split(',') if x.strip().isdigit()]
            employees = list(Employee.objects.filter(emp_id__in=emp_ids).order_by('emp_id'))
        else:
            employees = list(Employee.objects.filter(status='active').order_by('emp_id'))

        # Build workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Payout'

        # Header row: Date + for each employee a single column with "CheckIn - CheckOut"
        headers = ['Date']
        for e in employees:
            label = e.name or str(e.emp_id)
            headers.append(f"{label} (In - Out)")

        for col_idx, head in enumerate(headers, start=1):
            ws.cell(row=1, column=col_idx, value=head)

        # Fill rows per date (reuse logic from export_excel)
        row = 2
        delta = (end_date - start_date).days
        current_time = datetime.now().time()
        today = timezone.now().date()

        # track totals per employee
        totals = {emp.emp_id: 0.0 for emp in employees}

        for d_offset in range(delta + 1):
            rdate = start_date + timedelta(days=d_offset)
            ws.cell(row=row, column=1, value=rdate.strftime('%Y-%m-%d'))

            for idx, emp in enumerate(employees):
                col = 2 + idx
                atts = Attendance.objects.filter(employee=emp, date=rdate).order_by('check_in')

                check_in_val = "--:--"
                check_out_val = "--:--"
                if atts.exists():
                    if atts.count() > 1:
                        session_lines = []
                        for i, a in enumerate(atts):
                            ci = a.check_in.strftime('%I:%M %p') if a.check_in else '--:--'
                            co = a.check_out.strftime('%I:%M %p') if a.check_out else '--:--'
                            session_lines.append(f"#{i+1}: {ci} - {co}")
                        val = "\n".join(session_lines)
                        ws.cell(row=row, column=col).alignment = openpyxl.styles.Alignment(horizontal='center', vertical='center', wrap_text=True)
                        ws.row_dimensions[row].height = max(20, 15 * len(session_lines) + 6)
                    else:
                        first = atts.first()
                        last = atts.last()
                        if first.check_in:
                            try:
                                check_in_val = first.check_in.strftime('%I:%M %p')
                            except Exception:
                                check_in_val = str(first.check_in)
                        if last.check_out:
                            try:
                                check_out_val = last.check_out.strftime('%I:%M %p')
                            except Exception:
                                check_out_val = str(last.check_out)
                        val = f"{check_in_val} - {check_out_val}"
                    # accumulate total hours for this day
                    totals[emp.emp_id] += sum(att.total_hours for att in atts)
                else:
                    # Leave handling
                    leave = PaidLeave.objects.filter(
                        employee=emp,
                        approved=True,
                        start_time__date__lte=rdate,
                        end_time__date__gte=rdate,
                    ).first()
                    if leave:
                        val = "Leave"
                    else:
                        holiday = Holiday.objects.filter(date=rdate).first()
                        if holiday:
                            val = f"Holiday ({holiday.name})"
                        elif emp.weekly_off_day is not None and rdate.weekday() == emp.weekly_off_day:
                            val = "Off Day"
                        else:
                            s_start, s_end = get_employee_shift_times(emp, rdate)
                            if not s_start or not s_end:
                                if rdate < today:
                                    val = "Absent"
                                else:
                                    val = "--:--"
                            else:
                                if rdate < today or (rdate == today and current_time >= s_end):
                                    val = "Absent"
                                else:
                                    val = "--:--"

                ws.cell(row=row, column=col, value=val)

            row += 1

        # Append totals row and salary row
        # blank separator
        row += 1
        totals_row = row
        ws.cell(row=totals_row, column=1, value='Total Hours')
        for idx, emp in enumerate(employees):
            col = 2 + idx
            hrs = round(totals.get(emp.emp_id, 0.0), 2)
            ws.cell(row=totals_row, column=col, value=hrs)

        # salary row
        row += 1
        salary_row = row
        ws.cell(row=salary_row, column=1, value='Salary')
        for idx, emp in enumerate(employees):
            col = 2 + idx
            hourly = float(emp.hourly_rate or 0)
            pay = round(totals.get(emp.emp_id, 0.0) * hourly, 2)
            ws.cell(row=salary_row, column=col, value=pay)

        # Auto-fit column widths
        for i, column_cells in enumerate(ws.columns, start=1):
            max_length = 0
            for cell in column_cells:
                try:
                    val = str(cell.value) if cell.value is not None else ''
                except Exception:
                    val = ''
                if len(val) > max_length:
                    max_length = len(val)
            ws.column_dimensions[get_column_letter(i)].width = min(max_length + 2, 50)

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f"payout_{start}_{end}.xlsx"
        resp = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp['Content-Disposition'] = f'attachment; filename="{filename}"'
        return resp

    @action(detail=False, methods=['get'])
    def daily_report(self, request):
        """Get daily attendance report for a specific date (defaults to today) with search, filter, and pagination support"""
        date_str = request.query_params.get('date')
        search_query = request.query_params.get('search', '').strip()
        employee_filter = request.query_params.get('employee', '').strip()
        status_filter = request.query_params.get('status', '').strip().lower()

        today = datetime.now().date()

        if not date_str:
            report_date = today
        else:
            try:
                report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

        attendances = Attendance.objects.filter(date=report_date).order_by('employee__emp_id', 'check_in')
        total_active_employees = Employee.objects.filter(status='active').count()

        # Group attendances by employee so each present employee appears once with first IN, last OUT, and summed hours
        grouped_atts = {}
        for att in attendances:
            grouped_atts.setdefault(att.employee.emp_id, []).append(att)

        attendance_details = []
        for emp_id_val, att_list in grouped_atts.items():
            first_att = att_list[0]
            last_att = att_list[-1]
            day_total_hours = round(sum(a.total_hours for a in att_list), 2)
            is_late_val = any(a.status == 'late' for a in att_list)
            status_val = 'late' if is_late_val else 'on_time'

            attendance_details.append({
                "id": first_att.id,
                "employee": first_att.employee.emp_id,
                "employee_name": first_att.employee.name,
                "date": report_date.isoformat(),
                "check_in": first_att.check_in.strftime('%I:%M:%S %p') if first_att.check_in else None,
                "check_out": last_att.check_out.strftime('%I:%M:%S %p') if last_att.check_out else None,
                "message_late": first_att.message_late,
                "status": status_val,
                "total_hours": format_hours_display(day_total_hours),
                "total_hours_value": day_total_hours,
                "sessions_count": len(att_list),
                "is_late": is_late_val,
                "created_at": first_att.created_at,
                "updated_at": last_att.updated_at,
            })

        # Count UNIQUE employees present today
        present_count = len(grouped_atts)
        total_hours = round(sum(att.total_hours for att in attendances), 2)

        active_employees = Employee.objects.filter(status='active')
        present_employee_ids = set(grouped_atts.keys())
        absent_details = []
        pending_count = 0
        current_time = datetime.now().time()

        for employee in active_employees:
            if employee.emp_id in present_employee_ids:
                continue

            s_start, s_end = get_employee_shift_times(employee, report_date)
            if not s_start or not s_end:
                pending_count += 1
                continue

            if report_date < today or (report_date == today and current_time >= s_end):
                on_leave = PaidLeave.objects.filter(
                    employee=employee,
                    approved=True,
                    start_time__date__lte=report_date,
                    end_time__date__gte=report_date,
                ).exists()

                status_val = "on_leave" if on_leave else "absent"
                absent_details.append({
                    "id": None,
                    "employee": employee.emp_id,
                    "employee_name": employee.name,
                    "date": report_date.isoformat(),
                    "check_in": None,
                    "check_out": None,
                    "message_late": None,
                    "status": status_val,
                    "total_hours": "0h 0m",
                    "total_hours_value": 0.0,
                    "sessions_count": 0,
                    "is_late": False,
                    "created_at": None,
                    "updated_at": None,
                })
            else:
                pending_count += 1

        absent_count = len(absent_details)

        # Count how many UNIQUE employees were late at least once today
        late_count = sum(1 for item in attendance_details if item['is_late'])
        on_time_count = max(0, present_count - late_count)

        # Helper to match search query against an entry
        def matches_search(item, query):
            q = query.lower()
            emp_name = str(item.get('employee_name') or '').lower()
            emp_id_str = str(item.get('employee') or '').lower()
            return q in emp_name or q in emp_id_str

        # Helper to match employee filter against an entry
        def matches_employee(item, emp_val):
            val = str(emp_val).strip().lower()
            emp_id_str = str(item.get('employee') or '').lower()
            emp_name = str(item.get('employee_name') or '').lower()
            return val == emp_id_str or val in emp_id_str or val in emp_name

        # Apply search filter if provided
        if search_query:
            attendance_details = [item for item in attendance_details if matches_search(item, search_query)]
            absent_details = [item for item in absent_details if matches_search(item, search_query)]

        # Apply employee filter if provided
        if employee_filter:
            attendance_details = [item for item in attendance_details if matches_employee(item, employee_filter)]
            absent_details = [item for item in absent_details if matches_employee(item, employee_filter)]

        # Apply status filter if provided
        if status_filter:
            if status_filter == 'present':
                absent_details = []
            elif status_filter in ('late', 'is_late'):
                attendance_details = [item for item in attendance_details if item.get('is_late') or item.get('status') == 'late']
                absent_details = []
            elif status_filter in ('on_time', 'ontime'):
                attendance_details = [item for item in attendance_details if not item.get('is_late') and item.get('status') == 'on_time']
                absent_details = []
            elif status_filter == 'absent':
                attendance_details = []
                absent_details = [item for item in absent_details if item.get('status') == 'absent']
            elif status_filter in ('on_leave', 'leave'):
                attendance_details = []
                absent_details = [item for item in absent_details if item.get('status') == 'on_leave']

        summary_data = {
            "date": report_date.isoformat(),
            "total_active_employees": total_active_employees,
            "present": present_count,
            "absent": absent_count,
            "pending": pending_count,
            "on_time": on_time_count,
            "late": late_count,
            "total_hours": format_hours_display(total_hours),
            "total_hours_value": total_hours,
            "absent_details": absent_details,
        }

        # Apply pagination to attendance_details
        page = self.paginate_queryset(attendance_details)
        if page is not None:
            paginated_response = self.get_paginated_response(page).data
            paginated_response.update({
                **summary_data,
                "attendance_details": page,
                "results": page,
            })
            return Response(paginated_response)

        return Response({
            **summary_data,
            "count": len(attendance_details),
            "attendance_details": attendance_details,
            "results": attendance_details,
        })

    @action(detail=False, methods=['get'])
    def weekly_report(self, request):
        """Get weekly attendance report with rounded hours and unique counts"""
        today = datetime.now().date()
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)

        attendances = Attendance.objects.filter(
            date__range=[start_date, end_date],
            employee__status='active'
        )

        # Optional employee filter by emp_id
        emp_param = request.query_params.get('employee')
        employee_obj = None
        if emp_param and str(emp_param).strip().isdigit():
            try:
                employee_obj = Employee.objects.get(emp_id=int(emp_param))
                attendances = attendances.filter(employee=employee_obj)
            except Employee.DoesNotExist:
                return Response({"error": f"Employee with id {emp_param} not found"}, status=404)

        # FIX: Round the total hours to 2 decimal places
        total_hours = round(sum(att.total_hours for att in attendances), 2)
        
        # Count unique employee-day combinations
        total_working_records = attendances.values('employee', 'date').distinct().count()
        late_arrivals = attendances.filter(status='late').values('employee', 'date').distinct().count()
        active_employees_count = Employee.objects.filter(status='active').count()

        return Response({
            "employee_id": employee_obj.emp_id if employee_obj else None,
            "employee_name": employee_obj.name if employee_obj else None,
            "week": f"{start_date} to {end_date}",
            "total_records": total_working_records,
            "total_hours": format_hours_display(total_hours),
            "total_hours_value": total_hours,
            "late_arrivals": late_arrivals,
            "average_hours_per_day": round(total_hours / 7, 2) if total_working_records > 0 else 0,
            "active_employees": active_employees_count
        })

    @action(detail=False, methods=['get'])
    def monthly_report(self, request):
        """Get monthly attendance report with rounded hours and unique counts"""
        today = datetime.now().date()
        month = int(request.query_params.get('month', today.month))
        year = int(request.query_params.get('year', today.year))

        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)


        attendances = Attendance.objects.filter(date__range=[start_date, end_date])

        # Optional employee filter by emp_id
        emp_param = request.query_params.get('employee')
        employee_obj = None
        if emp_param and str(emp_param).strip().isdigit():
            try:
                employee_obj = Employee.objects.get(emp_id=int(emp_param))
                attendances = attendances.filter(employee=employee_obj)
            except Employee.DoesNotExist:
                return Response({"error": f"Employee with id {emp_param} not found"}, status=404)

        # FIX: Round total hours
        total_hours = round(sum(att.total_hours for att in attendances), 2)
        
        # FIX: Count unique employee-day instances (Working Days)
        unique_working_days = attendances.values('employee', 'date').distinct().count()
        unique_employees = attendances.values('employee').distinct().count()
        late_arrivals = attendances.filter(status='late').values('employee', 'date').distinct().count()

        return Response({
            "employee_id": employee_obj.emp_id if employee_obj else None,
            "employee_name": employee_obj.name if employee_obj else None,
            "month": f"{year}-{month:02d}",
            "total_working_days": unique_working_days,
            "total_hours_worked": format_hours_display(total_hours),
            "total_hours_worked_value": total_hours,
            "unique_employees": unique_employees,
            "late_arrivals": late_arrivals,
            "average_daily_attendance": round(unique_working_days / unique_employees, 2) if unique_employees > 0 else 0
        })

    @action(detail=False, methods=['get'])
    def employee_logs(self, request):
        """Get complete, detailed attendance session breakdown for a selected employee on a date or date range.

        Query params:
        - emp_id or employee (required): employee ID
        - date (optional): single date (YYYY-MM-DD)
        - start_date / date_from and end_date / date_to (optional): date range
        """
        emp_param = request.query_params.get('emp_id') or request.query_params.get('employee')
        if not emp_param:
            return Response({"error": "emp_id or employee parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            if str(emp_param).strip().isdigit():
                employee = Employee.objects.filter(Q(emp_id=int(emp_param)) | Q(pk=int(emp_param))).first()
            else:
                employee = Employee.objects.filter(emp_id=emp_param).first()
            if not employee:
                return Response({"error": f"Employee with id '{emp_param}' not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        start_date, end_date, err = parse_date_range_params(request)
        if err:
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)

        data = build_employee_detailed_logs(employee, start_date, end_date)
        return Response(data)

    @action(detail=False, methods=['post'], permission_classes=[IsAdmin])
    def mark_absent(self, request):
        """Mark absent for employees who have no attendance and no approved leave.

        POST params:
        - date (YYYY-MM-DD) OR date_from/date_to
        - employees (optional comma-separated emp_id list) or employee (single emp_id)
        """
        # parse date range
        date_str = request.data.get('date') or request.query_params.get('date')
        start = request.data.get('date_from') or request.query_params.get('date_from')
        end = request.data.get('date_to') or request.query_params.get('date_to')

        if date_str:
            try:
                start_date = end_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Invalid date format"}, status=400)
        elif start and end:
            try:
                start_date = datetime.strptime(start, '%Y-%m-%d').date()
                end_date = datetime.strptime(end, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Invalid date format"}, status=400)
        else:
            return Response({"error": "Provide date or date_from and date_to (YYYY-MM-DD)"}, status=400)

        # employees filter
        emp_single = request.data.get('employee') or request.query_params.get('employee')
        emp_param = request.data.get('employees') or request.query_params.get('employees')
        if emp_single and str(emp_single).strip().isdigit():
            employees = list(Employee.objects.filter(emp_id=int(emp_single)).order_by('emp_id'))
        elif emp_param:
            emp_ids = [int(x.strip()) for x in str(emp_param).split(',') if x.strip().isdigit()]
            employees = list(Employee.objects.filter(emp_id__in=emp_ids).order_by('emp_id'))
        else:
            employees = list(Employee.objects.filter(status='active').order_by('emp_id'))

        created = []
        skipped = []

        delta = (end_date - start_date).days
        for d_offset in range(delta + 1):
            rdate = start_date + timedelta(days=d_offset)
            for emp in employees:
                s_start, s_end = get_employee_shift_times(emp, rdate)
                if not s_start or not s_end:
                    exists = Attendance.objects.filter(employee=emp).filter(
                        Q(date=rdate) | Q(check_in__date=rdate)
                    ).exists()
                    if exists:
                        skipped.append({"employee": emp.emp_id, "date": rdate.isoformat(), "reason": "has_attendance"})
                        continue
                    on_leave = PaidLeave.objects.filter(
                        employee=emp,
                        approved=True,
                        start_time__date__lte=rdate,
                        end_time__date__gte=rdate,
                    ).exists()
                    if on_leave:
                        skipped.append({"employee": emp.emp_id, "date": rdate.isoformat(), "reason": "on_leave"})
                        continue
                    check_dt = datetime.combine(rdate, time(0, 0))
                    att = Attendance.objects.create(
                        employee=emp,
                        date=rdate,
                        check_in=check_dt,
                        check_out=check_dt,
                        status='absent',
                        message_late='Marked absent by system'
                    )
                    created.append({"employee": emp.emp_id, "date": rdate.isoformat(), "id": att.id})
                    continue

                exists = Attendance.objects.filter(employee=emp).filter(
                    Q(date=rdate) | Q(check_in__date=rdate)
                ).exists()
                if exists:
                    skipped.append({"employee": emp.emp_id, "date": rdate.isoformat(), "reason": "has_attendance"})
                    continue

                on_leave = PaidLeave.objects.filter(
                    employee=emp,
                    approved=True,
                    start_time__date__lte=rdate,
                    end_time__date__gte=rdate,
                ).exists()
                if on_leave:
                    skipped.append({"employee": emp.emp_id, "date": rdate.isoformat(), "reason": "on_leave"})
                    continue

                check_dt = datetime.combine(rdate, s_start)
                att = Attendance.objects.create(
                    employee=emp,
                    date=rdate,
                    check_in=check_dt,
                    check_out=check_dt,
                    status='absent',
                    message_late='Marked absent by system'
                )
                created.append({"employee": emp.emp_id, "date": rdate.isoformat(), "id": att.id})

        return Response({"created_count": len(created), "created": created, "skipped": skipped})

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def check_in(self, request):
        """Check in an employee"""
        emp_id = request.data.get('emp_id')
        
        if not emp_id:
            return Response(
                {"error": "emp_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            employee = Employee.objects.get(emp_id=emp_id)
        except Employee.DoesNotExist:
            return Response(
                {"error": f"Employee with id {emp_id} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Prevent attendance for inactive employees; log the attempt
        if getattr(employee, 'status', '') != 'active':
            try:
                attempted_by = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
                InactiveAttendanceAttempt.objects.create(
                    employee=employee,
                    attempted_by=attempted_by,
                    method='check_in',
                    message='Attempted check-in while employee inactive',
                    deactivated_by_username=employee.deactivated_by.username if getattr(employee, 'deactivated_by', None) else None,
                    deactivated_at=employee.deactivated_at
                )
            except Exception:
                pass

            return Response({"error": "Employee is inactive. Attempt has been logged."}, status=status.HTTP_403_FORBIDDEN)

        today = timezone.now().date()
        now = timezone.now()

        # Consider the latest attendance record regardless of date so an open check-in
        # on a previous date will be treated as the next action's check-out.
        last_att = Attendance.objects.filter(employee=employee).order_by('-check_in').first()

        # Unified dedup: reject any scan within 10s of the last event (check_in or check_out)
        if last_att:
            last_event = last_att.check_out if last_att.check_out else last_att.check_in
            elapsed = int((now - last_event).total_seconds())
            if elapsed < 10:
                wait = 10 - elapsed
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "biometric_device",
                    {
                        "type": "biometric_duplicate",
                        "message": f"You already marked your attendance, Wait for {wait}s to try again",
                    }
                )
                return Response(
                    {
                        "message": f"You already marked your attendance, Wait for {wait}s to try again",
                        "duplicate": True,
                    },
                    status=status.HTTP_200_OK
                )

        # Get duty date and shift times for check-in
        duty_date = get_duty_date_for_check_in(employee, now)
        s_start, s_end = get_employee_shift_times(employee, duty_date)

        # If there's an open attendance (no check_out), treat this request as a check-out
        if last_att and last_att.check_out is None:
            duration = (now - last_att.check_in).total_seconds() / 3600
            max_allowed = get_overtime_max_allowed(employee, last_att.check_in)
            if duration > max_allowed:
                # Auto-check-out and create a new attendance (check-in)
                duty_date_new = get_duty_date_for_check_in(employee, now)
                s_start_new, _ = get_employee_shift_times(employee, duty_date_new)
                new_status = 'on_time'
                new_late_msg = None
                if s_start_new:
                    shift_start_dt = datetime.combine(duty_date_new, s_start_new)
                    is_late_new = now > shift_start_dt + timedelta(minutes=LATE_GRACE_MINUTES)
                    new_status = 'late' if is_late_new else 'on_time'
                    if is_late_new:
                        mins = int((now - shift_start_dt).total_seconds() / 60)
                        new_late_msg = f"you are late {mins}m"

                new_att = Attendance.objects.create(
                    employee=employee,
                    date=duty_date_new,
                    check_in=now,
                    status=new_status,
                    message_late=new_late_msg
                )

                total_hours_prev = round(min((last_att.check_out - last_att.check_in).total_seconds() / 3600, max_allowed), 2) if last_att.check_out else 0

                return Response(
                    {
                        "message": "Auto check-out performed and new check-in created",
                        "previous_record": AttendanceSerializer(last_att).data,
                        "new_record": AttendanceSerializer(new_att).data,
                        "previous_total_hours": format_hours_display(total_hours_prev),
                        "previous_total_hours_value": total_hours_prev
                    },
                    status=status.HTTP_200_OK
                )

            # Normal check-out within max_allowed hours
            last_att.check_out = now
            last_att.save()

            total_hours = round(min((now - last_att.check_in).total_seconds() / 3600, max_allowed), 2)

            log_activity(
                request=request,
                actor=request.user if (getattr(request, 'user', None) and request.user.is_authenticated) else None,
                action_type='attendance_checkout',
                category='attendance',
                description=f"Check-out: '{employee.name}' (ID: {employee.emp_id}) at {now.strftime('%I:%M %p')} (Worked: {format_hours_display(total_hours)})",
                target_model='Employee',
                target_id=employee.emp_id,
                target_name=employee.name,
                details={'emp_id': employee.emp_id, 'check_out': now.strftime('%I:%M %p'), 'total_hours': total_hours}
            )

            return Response(
                {
                    "message": "Check-out successful",
                    "total_hours": format_hours_display(total_hours),
                    "total_hours_value": total_hours,
                    "record": AttendanceSerializer(last_att).data
                },
                status=status.HTTP_200_OK
            )

        status_val = 'on_time'
        late_msg = None
        if s_start:
            shift_start_dt = datetime.combine(duty_date, s_start)
            is_late = now > shift_start_dt + timedelta(minutes=LATE_GRACE_MINUTES)
            status_val = 'late' if is_late else 'on_time'
            if is_late:
                minutes_late = int((now - shift_start_dt).total_seconds() / 60)
                late_msg = f"you are late {minutes_late}m"

        attendance = Attendance.objects.create(
            employee=employee,
            date=duty_date,
            check_in=now,
            status=status_val,
            message_late=late_msg
        )

        log_activity(
            request=request,
            actor=request.user if (getattr(request, 'user', None) and request.user.is_authenticated) else None,
            action_type='attendance_checkin',
            category='attendance',
            description=f"Check-in: '{employee.name}' (ID: {employee.emp_id}) at {now.strftime('%I:%M %p')} ({status_val})",
            target_model='Employee',
            target_id=employee.emp_id,
            target_name=employee.name,
            details={'emp_id': employee.emp_id, 'check_in': now.strftime('%I:%M %p'), 'status': status_val, 'date': str(duty_date)}
        )

        return Response(
            {
                "message": "Check-in successful",
                "record": AttendanceSerializer(attendance).data,
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def auto_attendance(self, request):
        emp_id = request.data.get('emp_id')
        
        if not emp_id:
            return Response({"error": "emp_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            employee = Employee.objects.get(emp_id=emp_id)
        except Employee.DoesNotExist:
            return Response({"error": f"Employee with id {emp_id} not found"}, status=status.HTTP_404_NOT_FOUND)

        # Prevent attendance for inactive employees; log the attempt
        if getattr(employee, 'status', '') != 'active':
            try:
                attempted_by = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
                InactiveAttendanceAttempt.objects.create(
                    employee=employee,
                    attempted_by=attempted_by,
                    method='auto_attendance',
                    message='Attempted auto-attendance while employee inactive',
                    deactivated_by_username=employee.deactivated_by.username if getattr(employee, 'deactivated_by', None) else None,
                    deactivated_at=employee.deactivated_at
                )
            except Exception:
                pass

            return Response({"error": "Employee is inactive. Attempt has been logged."}, status=status.HTTP_403_FORBIDDEN)

        # Prefer client-sent timestamp if provided, otherwise use system clock time
        timestamp_in = request.data.get('timestamp')
        now = None
        if timestamp_in:
            try:
                # Accept epoch seconds or milliseconds
                if isinstance(timestamp_in, (int, float)) or str(timestamp_in).isdigit():
                    now = datetime.fromtimestamp(float(timestamp_in))
                else:
                    # Accept ISO formatted string
                    try:
                        now = datetime.fromisoformat(str(timestamp_in))
                    except Exception:
                        # Fallback to common format
                        now = datetime.strptime(str(timestamp_in), '%Y-%m-%d %H:%M:%S')
            except Exception:
                now = datetime.now()
        else:
            now = datetime.now()
        # Debug logging for timestamp handling
        logger = logging.getLogger(__name__)
        try:
            logger.debug(f"auto_attendance called for emp_id={emp_id}, received_timestamp={timestamp_in}, using_now={now}")
        except Exception:
            pass

        today = now.date()
        
        # Look for the latest attendance record regardless of date so open check-ins carry over
        last_attendance = Attendance.objects.filter(employee=employee).order_by('-check_in').first()

        # Unified dedup: reject any scan within 10s of the last event (check_in or check_out)
        if last_attendance:
            last_event = last_attendance.check_out if last_attendance.check_out else last_attendance.check_in
            elapsed = int((now - last_event).total_seconds())
            if elapsed < 10:
                wait = 10 - elapsed
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "biometric_device",
                    {
                        "type": "biometric_duplicate",
                        "message": f"You already marked your attendance, Wait for {wait}s to try again",
                    }
                )
                return Response(
                    {
                        "message": f"You already marked your attendance, Wait for {wait}s to try again",
                        "duplicate": True,
                        "action": "rescan",
                    },
                    status=status.HTTP_200_OK
                )
        # For total hours calculation when checking out, use the last open check-in (the same record)
        first_checkin = None
        if last_attendance and last_attendance.check_out is None:
            first_checkin = last_attendance

        s_start, s_end = get_employee_shift_times(employee, today)

        attendance_info = {
            "emp_id": employee.emp_id,
            "employee_name": employee.name,
            "profile_img": f"http://{settings.SERVER_IP}:{settings.SERVER_PORT}{employee.profile_img.url}" if employee.profile_img else None,
            "shift_type": employee.current_shift.name if employee.current_shift else "N/A",
            "timestamp": now.strftime('%I:%M %p'), 
        }
        
        # Determine action: Check-in or Check-out
        did_modify = False
        action = "check_in"
        message = "Attendance marked"
        if not last_attendance or (last_attendance.check_out is not None):
            # ===== NEW CHECK-IN =====
            duty_date = get_duty_date_for_check_in(employee, now)
            s_start, s_end = get_employee_shift_times(employee, duty_date)

            is_late = False
            late_msg = "On time"
            if s_start:
                shift_start_dt = datetime.combine(duty_date, s_start)
                is_late = now > shift_start_dt + timedelta(minutes=LATE_GRACE_MINUTES)
                if is_late:
                    total_minutes = int((now - shift_start_dt).total_seconds() / 60)
                    if total_minutes >= 60:
                        hours = total_minutes // 60
                        minutes = total_minutes % 60
                        if minutes > 0:
                            late_msg = f"{hours}h {minutes}m late"
                        else:
                            late_msg = f"{hours}h late"
                    else:
                        late_msg = f"{total_minutes}m late"

            status_val = 'late' if is_late else 'on_time'

            Attendance.objects.create(
                employee=employee,
                date=duty_date,
                check_in=now,
                message_late=late_msg,
                status=status_val
            )
            did_modify = True
            action = "check_in"
            message = "Check-in successful"
            attendance_info.update({
                "action": action,
                "check_in": now.strftime('%I:%M %p'),
                "check_out": "--:--",
                "is_late": is_late,
                "late_message": late_msg,
                "total_hours_today": "0h 0m",
                "total_hours_today_value": 0
            })

            log_activity(
                request=request,
                actor=request.user if (getattr(request, 'user', None) and request.user.is_authenticated) else None,
                action_type='attendance_checkin',
                category='attendance',
                description=f"Check-in: '{employee.name}' (ID: {employee.emp_id}) at {now.strftime('%I:%M %p')} ({status_val})",
                target_model='Employee',
                target_id=employee.emp_id,
                target_name=employee.name,
                details={'emp_id': employee.emp_id, 'check_in': now.strftime('%I:%M %p'), 'status': status_val, 'date': str(duty_date)}
            )
        elif last_attendance.check_in is not None and last_attendance.check_out is None:
            # ===== CHECK-OUT =====
            try:
                logger.debug(f"Last attendance check_in={last_attendance.check_in}, now={now}")
            except Exception:
                pass
            duration = (now - last_attendance.check_in).total_seconds() / 3600
            try:
                logger.debug(f"Computed duration_hours={duration}")
            except Exception:
                pass
            max_allowed = get_overtime_max_allowed(employee, last_attendance.check_in)

            if duration > max_allowed:
                duty_date_new = get_duty_date_for_check_in(employee, now)
                s_start_new, _ = get_employee_shift_times(employee, duty_date_new)
                new_status = 'on_time'
                new_late_msg = "On time"
                if s_start_new:
                    new_shift_start = datetime.combine(duty_date_new, s_start_new)
                    is_late_new = now > new_shift_start + timedelta(minutes=LATE_GRACE_MINUTES)
                    new_status = 'late' if is_late_new else 'on_time'
                    if is_late_new:
                        mins = int((now - new_shift_start).total_seconds() / 60)
                        new_late_msg = f"you are late {mins}m"

                new_att = Attendance.objects.create(
                    employee=employee,
                    date=duty_date_new,
                    check_in=now,
                    status=new_status,
                    message_late=new_late_msg
                )
                did_modify = True
                action = "check_in"
                message = "Check-in successful"
                attendance_info.update({
                    "action": action,
                    "check_in": new_att.check_in.strftime('%I:%M %p'),
                    "check_out": "--:--",
                    "is_late": True if new_status == 'late' else False,
                    "late_message": new_late_msg,
                    "total_hours_today": "0h 0m",
                    "total_hours_today_value": 0
                })

                log_activity(
                    request=request,
                    actor=request.user if (getattr(request, 'user', None) and request.user.is_authenticated) else None,
                    action_type='attendance_checkin',
                    category='attendance',
                    description=f"Auto check-in: '{employee.name}' (ID: {employee.emp_id}) at {now.strftime('%I:%M %p')} ({new_status})",
                    target_model='Employee',
                    target_id=employee.emp_id,
                    target_name=employee.name,
                    details={'emp_id': employee.emp_id, 'check_in': now.strftime('%I:%M %p'), 'status': new_status, 'date': str(duty_date_new)}
                )
            else:
                last_attendance.check_out = now # Saves literal system time to DB
                last_attendance.save()
                did_modify = True

                total_hours = 0
                regular_hours = 0
                overtime_hours = 0
                if first_checkin:
                    total_duration = (now - first_checkin.check_in).total_seconds() / 3600
                    total_hours = round(min(total_duration, max_allowed), 2)
                    s_start_co, s_end_co = get_employee_shift_times(employee, first_checkin.date)
                    if s_end_co:
                        shift_end_dt = datetime.combine(first_checkin.date, s_end_co)
                        if s_start_co and s_end_co <= s_start_co:
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
                message = "Check-out successful"
                attendance_info.update({
                    "action": action,
                    "check_in": last_attendance.check_in.strftime('%I:%M %p'),
                    "check_out": now.strftime('%I:%M %p'),
                    "is_late": False,
                    "late_message": None,
                    "total_hours_today": format_hours_display(total_hours),
                    "total_hours_today_value": total_hours,
                    "regular_hours": regular_hours,
                    "overtime_hours": overtime_hours
                })

                log_activity(
                    request=request,
                    actor=request.user if (getattr(request, 'user', None) and request.user.is_authenticated) else None,
                    action_type='attendance_checkout',
                    category='attendance',
                    description=f"Check-out: '{employee.name}' (ID: {employee.emp_id}) at {now.strftime('%I:%M %p')} (Worked: {format_hours_display(total_hours)})",
                    target_model='Employee',
                    target_id=employee.emp_id,
                    target_name=employee.name,
                    details={'emp_id': employee.emp_id, 'check_out': now.strftime('%I:%M %p'), 'total_hours': total_hours, 'regular_hours': regular_hours, 'overtime_hours': overtime_hours}
                )

        response_payload = {
            "message": message,
            "action": action,
            "data": attendance_info
        }

        # Broadcast to WebSocket only if we created or updated a record
        if did_modify:
            try:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "biometric_device",
                    {
                        "type": "biometric_event",
                        "data": attendance_info 
                    }
                )
            except Exception as e:
                print(f"WS Error: {e}")

        return Response(response_payload, status=status.HTTP_200_OK)

class PaidLeaveViewSet(viewsets.ModelViewSet):
    queryset = PaidLeave.objects.all().order_by('-start_time')
    serializer_class = PaidLeaveSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        leave = serializer.save()
        emp_name = leave.employee.name if leave.employee else 'Unknown'
        emp_id = leave.employee.emp_id if leave.employee else None
        log_activity(
            request=self.request,
            actor=self.request.user,
            action_type='leave_apply',
            category='leave',
            description=f"Leave application created for '{emp_name}' ({leave.leave_type}, {leave.start_time.date()} to {leave.end_time.date()})",
            target_model='PaidLeave',
            target_id=leave.id,
            target_name=emp_name,
            details={
                'emp_id': emp_id,
                'leave_type': leave.leave_type,
                'start_time': str(leave.start_time),
                'end_time': str(leave.end_time),
                'reason': leave.reason
            }
        )

    def perform_update(self, serializer):
        leave = serializer.save()
        emp_name = leave.employee.name if leave.employee else 'Unknown'
        emp_id = leave.employee.emp_id if leave.employee else None
        log_activity(
            request=self.request,
            actor=self.request.user,
            action_type='leave_apply',
            category='leave',
            description=f"Leave updated for '{emp_name}' ({leave.leave_type}, approved={leave.approved})",
            target_model='PaidLeave',
            target_id=leave.id,
            target_name=emp_name,
            details={
                'emp_id': emp_id,
                'leave_type': leave.leave_type,
                'approved': leave.approved
            }
        )

    def perform_destroy(self, instance):
        emp_name = instance.employee.name if instance.employee else 'Unknown'
        emp_id = instance.employee.emp_id if instance.employee else None
        log_activity(
            request=self.request,
            actor=self.request.user,
            action_type='leave_delete',
            category='leave',
            description=f"Leave deleted for '{emp_name}' ({instance.leave_type}, {instance.start_time.date()})",
            target_model='PaidLeave',
            target_id=instance.id,
            target_name=emp_name,
            details={'emp_id': emp_id, 'leave_type': instance.leave_type}
        )
        instance.delete()

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a leave request"""
        leave = self.get_object()
        leave.approved = True
        leave.approved_by = request.data.get('approved_by', 'Admin')
        leave.save()
        emp_name = leave.employee.name if leave.employee else 'Unknown'
        emp_id = leave.employee.emp_id if leave.employee else None
        log_activity(
            request=request,
            actor=request.user,
            action_type='leave_approve',
            category='leave',
            description=f"Leave approved for '{emp_name}' ({leave.leave_type}, {leave.start_time.date()} to {leave.end_time.date()})",
            target_model='PaidLeave',
            target_id=leave.id,
            target_name=emp_name,
            details={'emp_id': emp_id, 'approved_by': leave.approved_by}
        )
        return Response(
            {"message": "Leave approved", "leave": PaidLeaveSerializer(leave).data}
        )

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a leave request"""
        leave = self.get_object()
        emp_name = leave.employee.name if leave.employee else 'Unknown'
        emp_id = leave.employee.emp_id if leave.employee else None
        leave_id = leave.id
        leave_type = leave.leave_type
        leave.delete()
        log_activity(
            request=request,
            actor=request.user,
            action_type='leave_reject',
            category='leave',
            description=f"Leave rejected and removed for '{emp_name}' ({leave_type})",
            target_model='PaidLeave',
            target_id=leave_id,
            target_name=emp_name,
            details={'emp_id': emp_id, 'leave_type': leave_type}
        )
        return Response(
            {"message": "Leave request rejected"},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """Get all pending leave requests"""
        pending = PaidLeave.objects.filter(approved=False)
        serializer = self.get_serializer(pending, many=True)
        return Response({
            "pending_count": pending.count(),
            "leaves": serializer.data
        })

    @action(detail=False, methods=['get'])
    def employee_leaves(self, request):
        """Get leaves for a specific employee"""
        emp_id = request.query_params.get('emp_id')
        if not emp_id:
            return Response(
                {"error": "emp_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        leaves = PaidLeave.objects.filter(employee__emp_id=emp_id)
        serializer = self.get_serializer(leaves, many=True)
        return Response(serializer.data)

class ShiftPagination(PageNumberPagination):
    page_size_query_param = 'page_size'


class ShiftViewSet(viewsets.ModelViewSet):
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ShiftPagination

    def perform_create(self, serializer):
        shift = serializer.save()
        log_activity(
            request=self.request,
            actor=self.request.user,
            action_type='shift_create',
            category='shift',
            description=f"Created shift '{shift.name}' ({shift.start_time} - {shift.end_time})",
            target_model='Shift',
            target_id=shift.id,
            target_name=shift.name,
            details={'name': shift.name, 'start_time': str(shift.start_time), 'end_time': str(shift.end_time)}
        )

    def perform_update(self, serializer):
        shift = serializer.save()
        log_activity(
            request=self.request,
            actor=self.request.user,
            action_type='shift_update',
            category='shift',
            description=f"Updated shift '{shift.name}' ({shift.start_time} - {shift.end_time})",
            target_model='Shift',
            target_id=shift.id,
            target_name=shift.name,
            details={'name': shift.name, 'start_time': str(shift.start_time), 'end_time': str(shift.end_time)}
        )

    def perform_destroy(self, instance):
        shift_id = instance.id
        shift_name = instance.name
        log_activity(
            request=self.request,
            actor=self.request.user,
            action_type='shift_delete',
            category='shift',
            description=f"Deleted shift '{shift_name}' (ID: {shift_id})",
            target_model='Shift',
            target_id=shift_id,
            target_name=shift_name,
            details={'shift_id': shift_id, 'name': shift_name}
        )
        instance.delete()


class HolidayViewSet(viewsets.ModelViewSet):
    queryset = Holiday.objects.all().order_by('date')
    serializer_class = HolidaySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        holiday = serializer.save()
        log_activity(
            request=self.request,
            actor=self.request.user,
            action_type='holiday_create',
            category='holiday',
            description=f"Created holiday '{holiday.name}' on {holiday.date} (Paid: {holiday.is_paid})",
            target_model='Holiday',
            target_id=holiday.id,
            target_name=holiday.name,
            details={'name': holiday.name, 'date': str(holiday.date), 'is_paid': holiday.is_paid}
        )

    def perform_update(self, serializer):
        holiday = serializer.save()
        log_activity(
            request=self.request,
            actor=self.request.user,
            action_type='holiday_update',
            category='holiday',
            description=f"Updated holiday '{holiday.name}' on {holiday.date}",
            target_model='Holiday',
            target_id=holiday.id,
            target_name=holiday.name,
            details={'name': holiday.name, 'date': str(holiday.date), 'is_paid': holiday.is_paid}
        )

    def perform_destroy(self, instance):
        h_id = instance.id
        h_name = instance.name
        h_date = instance.date
        log_activity(
            request=self.request,
            actor=self.request.user,
            action_type='holiday_delete',
            category='holiday',
            description=f"Deleted holiday '{h_name}' on {h_date}",
            target_model='Holiday',
            target_id=h_id,
            target_name=h_name,
            details={'name': h_name, 'date': str(h_date)}
        )
        instance.delete()


class OvertimeViewSet(viewsets.ModelViewSet):
    queryset = Overtime.objects.all().order_by('-date', '-start_time')
    serializer_class = OvertimeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ['date', 'employee__emp_id', 'status']

    def perform_create(self, serializer):
        ot = serializer.save()
        emp_name = ot.employee.name if ot.employee else 'Unknown'
        emp_id = ot.employee.emp_id if ot.employee else None
        tot_hrs = getattr(ot, 'total_hours', 0)
        log_activity(
            request=self.request,
            actor=self.request.user,
            action_type='overtime_create',
            category='overtime',
            description=f"Recorded overtime for '{emp_name}' on {ot.date} ({tot_hrs}h, status: {ot.status})",
            target_model='Overtime',
            target_id=ot.id,
            target_name=emp_name,
            details={'emp_id': emp_id, 'date': str(ot.date), 'hours': float(tot_hrs or 0), 'status': ot.status}
        )

    def perform_update(self, serializer):
        ot = serializer.save()
        emp_name = ot.employee.name if ot.employee else 'Unknown'
        log_activity(
            request=self.request,
            actor=self.request.user,
            action_type='overtime_create',
            category='overtime',
            description=f"Updated overtime for '{emp_name}' on {ot.date} (status: {ot.status})",
            target_model='Overtime',
            target_id=ot.id,
            target_name=emp_name,
            details={'emp_id': ot.employee.emp_id if ot.employee else None, 'date': str(ot.date), 'status': ot.status}
        )

    def perform_destroy(self, instance):
        ot_id = instance.id
        emp_name = instance.employee.name if instance.employee else 'Unknown'
        log_activity(
            request=self.request,
            actor=self.request.user,
            action_type='overtime_delete',
            category='overtime',
            description=f"Deleted overtime for '{emp_name}' on {instance.date}",
            target_model='Overtime',
            target_id=ot_id,
            target_name=emp_name,
            details={'emp_id': instance.employee.emp_id if instance.employee else None, 'date': str(instance.date)}
        )
        instance.delete()

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve an overtime request."""
        ot = self.get_object()
        if ot.status != 'pending':
            return Response({"error": "Overtime is not in pending status."}, status=status.HTTP_400_BAD_REQUEST)
        ot.status = 'approved'
        ot.approved_by = request.user if request.user.is_authenticated else None
        ot.save()
        emp_name = ot.employee.name if ot.employee else 'Unknown'
        tot_hrs = getattr(ot, 'total_hours', 0)
        log_activity(
            request=request,
            actor=request.user,
            action_type='overtime_approve',
            category='overtime',
            description=f"Approved overtime for '{emp_name}' on {ot.date} ({tot_hrs}h)",
            target_model='Overtime',
            target_id=ot.id,
            target_name=emp_name,
            details={'emp_id': ot.employee.emp_id if ot.employee else None, 'date': str(ot.date), 'hours': float(tot_hrs or 0)}
        )
        return Response(OvertimeSerializer(ot).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject an overtime request."""
        ot = self.get_object()
        if ot.status != 'pending':
            return Response({"error": "Overtime is not in pending status."}, status=status.HTTP_400_BAD_REQUEST)
        ot.status = 'rejected'
        ot.approved_by = request.user if request.user.is_authenticated else None
        ot.save()
        emp_name = ot.employee.name if ot.employee else 'Unknown'
        log_activity(
            request=request,
            actor=request.user,
            action_type='overtime_reject',
            category='overtime',
            description=f"Rejected overtime for '{emp_name}' on {ot.date}",
            target_model='Overtime',
            target_id=ot.id,
            target_name=emp_name,
            details={'emp_id': ot.employee.emp_id if ot.employee else None, 'date': str(ot.date)}
        )
        return Response(OvertimeSerializer(ot).data)


WEEKDAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
MONTH_DAYS = 30


def _prorate_salary(salary_value, period_days):
    if not salary_value:
        return 0.0
    return float(salary_value) * period_days / MONTH_DAYS


def _build_excel_response(output_data, start_date, end_date):
    if openpyxl is None:
        return HttpResponse("openpyxl is required to generate Excel files", status=500)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Comprehensive Report"

    # Ensure grid lines are visible
    ws.views.sheetView[0].showGridLines = True

    # Typography & Fonts
    title_font = openpyxl.styles.Font(name="Calibri", size=14, bold=True, color="1E3A8A")
    subtitle_font = openpyxl.styles.Font(name="Calibri", size=10, italic=True, color="475569")
    
    header_font = openpyxl.styles.Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    meta_label_font = openpyxl.styles.Font(name="Calibri", size=10, bold=True, color="1E293B")
    meta_val_hours_font = openpyxl.styles.Font(name="Calibri", size=10, bold=True, color="1E40AF")
    meta_val_off_font = openpyxl.styles.Font(name="Calibri", size=10, bold=True, color="0F766E")
    
    regular_font = openpyxl.styles.Font(name="Calibri", size=10, color="0F172A")
    date_font = openpyxl.styles.Font(name="Calibri", size=10, bold=True, color="1E293B")
    weekend_date_font = openpyxl.styles.Font(name="Calibri", size=10, bold=True, color="B91C1C")
    
    summary_header_font = openpyxl.styles.Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    summary_label_font = openpyxl.styles.Font(name="Calibri", size=10, bold=True, color="1E293B")
    summary_val_font = openpyxl.styles.Font(name="Calibri", size=10, color="0F172A")
    grand_total_font = openpyxl.styles.Font(name="Calibri", size=11, bold=True, color="1E3A8A")

    # Fills
    header_fill = openpyxl.styles.PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    working_hours_fill = openpyxl.styles.PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")
    off_day_header_fill = openpyxl.styles.PatternFill(start_color="F0FDFA", end_color="F0FDFA", fill_type="solid")
    
    date_col_fill = openpyxl.styles.PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    weekend_row_fill = openpyxl.styles.PatternFill(start_color="FEF2F2", end_color="FEF2F2", fill_type="solid")
    
    cell_off_fill = openpyxl.styles.PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid")
    cell_absent_fill = openpyxl.styles.PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    cell_leave_fill = openpyxl.styles.PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    cell_holiday_fill = openpyxl.styles.PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    
    summary_header_fill = openpyxl.styles.PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    summary_row_fill = openpyxl.styles.PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    summary_total_fill = openpyxl.styles.PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")

    # Status Fonts
    status_off_font = openpyxl.styles.Font(name="Calibri", size=10, bold=True, color="0369A1")
    status_absent_font = openpyxl.styles.Font(name="Calibri", size=10, bold=True, color="DC2626")
    status_leave_font = openpyxl.styles.Font(name="Calibri", size=10, bold=True, color="B45309")
    status_holiday_font = openpyxl.styles.Font(name="Calibri", size=10, bold=True, color="15803D")

    # Borders
    thin_border_side = openpyxl.styles.Side(style='thin', color='CBD5E1')
    thin_border = openpyxl.styles.Border(
        left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side
    )
    thick_bottom_side = openpyxl.styles.Side(style='medium', color='1E3A8A')
    header_border = openpyxl.styles.Border(
        left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thick_bottom_side
    )
    double_bottom_side = openpyxl.styles.Side(style='double', color='1E3A8A')
    total_border = openpyxl.styles.Border(
        left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=double_bottom_side
    )

    # Alignments
    center_align = openpyxl.styles.Alignment(horizontal='center', vertical='center', wrap_text=False)
    left_align = openpyxl.styles.Alignment(horizontal='left', vertical='center')
    right_align = openpyxl.styles.Alignment(horizontal='right', vertical='center')

    currency_fmt = '#,##0.00'

    employees = output_data['employees']
    matrix = output_data['matrix']
    summary = output_data['summary']
    emp_ids = [str(e['emp_id']) for e in employees]
    num_cols = 2 + len(employees)

    # 1. Report Title & Subtitle
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
    title_cell = ws.cell(row=1, column=1, value="FDPP EMS - COMPREHENSIVE ATTENDANCE & PAYROLL REPORT")
    title_cell.font = title_font
    title_cell.alignment = left_align
    ws.row_dimensions[1].height = 26

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=num_cols)
    subtitle_cell = ws.cell(
        row=2, column=1,
        value=f"Report Period: {start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}   |   Generated: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}"
    )
    subtitle_cell.font = subtitle_font
    subtitle_cell.alignment = left_align
    ws.row_dimensions[2].height = 20

    # Row 3: Spacer
    ws.row_dimensions[3].height = 8

    # 2. Main Table Headers (Row 4)
    row_4 = 4
    ws.row_dimensions[row_4].height = 28
    cell_date = ws.cell(row=row_4, column=1, value="Date")
    cell_date.font = header_font
    cell_date.fill = header_fill
    cell_date.alignment = center_align
    cell_date.border = header_border

    cell_day = ws.cell(row=row_4, column=2, value="Weekday")
    cell_day.font = header_font
    cell_day.fill = header_fill
    cell_day.alignment = center_align
    cell_day.border = header_border

    for idx, emp in enumerate(employees):
        col = 3 + idx
        emp_label = f"{emp['name']} (ID: {emp['emp_id']})"
        cell = ws.cell(row=row_4, column=col, value=emp_label)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = header_border

    # Row 5: Working Hours
    row_5 = 5
    ws.row_dimensions[row_5].height = 24
    c_lbl1 = ws.cell(row=row_5, column=1, value="Working Hours")
    c_lbl1.font = meta_label_font
    c_lbl1.fill = working_hours_fill
    c_lbl1.alignment = left_align
    c_lbl1.border = thin_border

    c_sub1 = ws.cell(row=row_5, column=2, value="(Shift Time)")
    c_sub1.font = openpyxl.styles.Font(name="Calibri", size=9, italic=True, color="64748B")
    c_sub1.fill = working_hours_fill
    c_sub1.alignment = center_align
    c_sub1.border = thin_border

    for idx, emp in enumerate(employees):
        col = 3 + idx
        wh = emp.get('working_hours') or "No Shift Assigned"
        cell = ws.cell(row=row_5, column=col, value=wh)
        cell.font = meta_val_hours_font
        cell.fill = working_hours_fill
        cell.alignment = center_align
        cell.border = thin_border

    # Row 6: Weekly Off Day
    row_6 = 6
    ws.row_dimensions[row_6].height = 24
    c_lbl2 = ws.cell(row=row_6, column=1, value="Weekly Off Day")
    c_lbl2.font = meta_label_font
    c_lbl2.fill = off_day_header_fill
    c_lbl2.alignment = left_align
    c_lbl2.border = thin_border

    c_sub2 = ws.cell(row=row_6, column=2, value="(Rest Day)")
    c_sub2.font = openpyxl.styles.Font(name="Calibri", size=9, italic=True, color="64748B")
    c_sub2.fill = off_day_header_fill
    c_sub2.alignment = center_align
    c_sub2.border = thin_border

    for idx, emp in enumerate(employees):
        col = 3 + idx
        off_day = emp.get('weekly_off_day_name') or "None"
        cell = ws.cell(row=row_6, column=col, value=off_day)
        cell.font = meta_val_off_font
        cell.fill = off_day_header_fill
        cell.alignment = center_align
        cell.border = thin_border

    # 3. Daily Attendance Matrix Rows
    start_matrix_row = 7
    current_row = start_matrix_row

    for row_item in matrix:
        d = row_item['date']
        weekday_name = row_item['weekday']
        is_weekend = weekday_name in ('Sunday', 'Saturday')
        date_str = d.strftime('%Y-%m-%d')
        
        ws.row_dimensions[current_row].height = 22

        # Date cell
        c_date = ws.cell(row=current_row, column=1, value=date_str)
        c_date.font = weekend_date_font if is_weekend else date_font
        c_date.fill = weekend_row_fill if is_weekend else date_col_fill
        c_date.alignment = center_align
        c_date.border = thin_border

        # Weekday cell
        c_day = ws.cell(row=current_row, column=2, value=weekday_name)
        c_day.font = weekend_date_font if is_weekend else date_font
        c_day.fill = weekend_row_fill if is_weekend else date_col_fill
        c_day.alignment = center_align
        c_day.border = thin_border

        for idx, emp_id_str in enumerate(emp_ids):
            col = 3 + idx
            cell_data = row_item['cells'].get(emp_id_str, {})
            status_val = cell_data.get('status', '')
            c_val = ws.cell(row=current_row, column=col)
            c_val.border = thin_border
            c_val.alignment = center_align

            if status_val == 'off_day':
                c_val.value = "Off Day"
                c_val.font = status_off_font
                c_val.fill = cell_off_fill
            elif status_val == 'holiday':
                hn = cell_data.get('holiday_name', '')
                c_val.value = f"Holiday: {hn}" if hn else "Holiday"
                c_val.font = status_holiday_font
                c_val.fill = cell_holiday_fill
            elif status_val == 'leave':
                lt = cell_data.get('leave_type', '')
                c_val.value = f"Leave ({lt.capitalize()})" if lt else "Leave"
                c_val.font = status_leave_font
                c_val.fill = cell_leave_fill
            elif status_val == 'absent':
                c_val.value = "Absent"
                c_val.font = status_absent_font
                c_val.fill = cell_absent_fill
            else:
                sessions = cell_data.get('sessions', [])
                day_hours_str = cell_data.get('total_hours_display') or "0h 0m"
                if len(sessions) > 1:
                    lines = [f"#{i+1}: {s['check_in']} - {s['check_out']} ({s['total_hours_display']})" for i, s in enumerate(sessions)]
                    lines.append(f"[Total: {day_hours_str}]")
                    val = "\n".join(lines)
                    c_val.value = val
                    c_val.alignment = openpyxl.styles.Alignment(horizontal='center', vertical='center', wrap_text=True)
                    needed_height = max(22, 16 * len(lines) + 8)
                    if ws.row_dimensions[current_row].height is None or ws.row_dimensions[current_row].height < needed_height:
                        ws.row_dimensions[current_row].height = needed_height
                elif len(sessions) == 1:
                    s0 = sessions[0]
                    val = f"{s0['check_in']} - {s0['check_out']} ({s0['total_hours_display']})"
                    c_val.value = val
                    c_val.alignment = openpyxl.styles.Alignment(horizontal='center', vertical='center', wrap_text=False)
                else:
                    in_str = cell_data.get('in_time') or '--:--'
                    out_str = cell_data.get('out_time') or '--:--'
                    val = f"{in_str} - {out_str}"
                    if day_hours_str and day_hours_str != "0h 0m":
                        val += f" ({day_hours_str})"
                    elif cell_data.get('total_hours'):
                        val += f" ({cell_data.get('total_hours')}h)"
                    c_val.value = val
                    c_val.alignment = openpyxl.styles.Alignment(horizontal='center', vertical='center', wrap_text=False)
                
                c_val.font = regular_font

        current_row += 1

    # 4. Summary & Metrics Section
    summary_start_row = current_row + 2
    ws.row_dimensions[summary_start_row - 1].height = 12

    # Summary Section Header
    ws.merge_cells(start_row=summary_start_row, start_column=1, end_row=summary_start_row, end_column=2)
    s_hdr = ws.cell(row=summary_start_row, column=1, value="SUMMARY & PAYROLL BREAKDOWN")
    s_hdr.font = summary_header_font
    s_hdr.fill = summary_header_fill
    s_hdr.alignment = left_align
    s_hdr.border = header_border
    ws.cell(row=summary_start_row, column=2).border = header_border

    for idx, emp in enumerate(employees):
        col = 3 + idx
        c_emp_s = ws.cell(row=summary_start_row, column=col, value=emp['name'])
        c_emp_s.font = summary_header_font
        c_emp_s.fill = summary_header_fill
        c_emp_s.alignment = center_align
        c_emp_s.border = header_border
    ws.row_dimensions[summary_start_row].height = 26

    summary_rows_data = [
        ('Total Hours Worked', 'total_hours', 'hours'),
        ('Total Overtime Hours', 'total_overtime_hours', 'hours'),
        ('Days Present', 'days_present', 'int'),
        ('Days Absent', 'days_absent', 'int'),
        ('Days On Leave', 'days_leave', 'int'),
        ('Weekly Off Days', 'weekly_off_days', 'int'),
        ('Holiday Days', 'holiday_days', 'int'),
        ('Regular Pay', 'regular_pay', 'currency'),
        ('Overtime Pay', 'overtime_pay', 'currency'),
        ('Holiday Pay', 'holiday_pay', 'currency'),
        ('Leave Pay', 'leave_pay', 'currency'),
        ('Off Day Pay', 'off_day_pay', 'currency'),
        ('Total Calculated Salary', 'total_salary', 'total_currency'),
    ]

    for r_idx, (label, field, fmt_type) in enumerate(summary_rows_data):
        r_num = summary_start_row + 1 + r_idx
        ws.row_dimensions[r_num].height = 22
        
        is_total = (fmt_type == 'total_currency')

        ws.merge_cells(start_row=r_num, start_column=1, end_row=r_num, end_column=2)
        lbl_cell = ws.cell(row=r_num, column=1, value=label)
        lbl_cell.font = summary_header_font if is_total else summary_label_font
        lbl_cell.fill = summary_total_fill if is_total else summary_row_fill
        lbl_cell.alignment = left_align
        lbl_cell.border = total_border if is_total else thin_border
        ws.cell(row=r_num, column=2).border = total_border if is_total else thin_border

        for e_idx, emp_id_str in enumerate(emp_ids):
            col = 3 + e_idx
            emp_summary = summary.get(emp_id_str, {})
            val = emp_summary.get(field, 0)
            
            val_cell = ws.cell(row=r_num, column=col)
            val_cell.font = summary_header_font if is_total else summary_val_font
            val_cell.fill = summary_total_fill if is_total else summary_row_fill
            val_cell.border = total_border if is_total else thin_border
            val_cell.alignment = right_align if 'currency' in fmt_type else center_align

            if 'currency' in fmt_type:
                val_cell.value = float(val) if val is not None else 0.0
                val_cell.number_format = currency_fmt
            elif fmt_type == 'int':
                val_cell.value = int(val) if val is not None else 0
            elif fmt_type == 'hours':
                val_cell.value = f"{float(val):.2f} hrs" if val is not None else "0.00 hrs"
            else:
                val_cell.value = val

    # 5. Grand Totals Box
    gt_start_row = summary_start_row + 1 + len(summary_rows_data) + 1
    ws.row_dimensions[gt_start_row - 1].height = 10

    gt = output_data['grand_totals']
    ws.merge_cells(start_row=gt_start_row, start_column=1, end_row=gt_start_row, end_column=2)
    gt_hdr = ws.cell(row=gt_start_row, column=1, value="COMPANY GRAND TOTALS")
    gt_hdr.font = summary_header_font
    gt_hdr.fill = summary_header_fill
    gt_hdr.alignment = left_align
    gt_hdr.border = header_border
    ws.cell(row=gt_start_row, column=2).border = header_border

    ws.merge_cells(start_row=gt_start_row, start_column=3, end_row=gt_start_row, end_column=num_cols)
    gt_sub = ws.cell(row=gt_start_row, column=3, value=f"Total Active Employees Evaluated: {gt.get('total_employees', len(employees))}")
    gt_sub.font = summary_header_font
    gt_sub.fill = summary_header_fill
    gt_sub.alignment = center_align
    for c in range(3, num_cols + 1):
        ws.cell(row=gt_start_row, column=c).border = header_border
    ws.row_dimensions[gt_start_row].height = 26

    gt_items = [
        ('Grand Total Worked Hours', f"{gt.get('total_hours', 0):.2f} hrs"),
        ('Grand Total Overtime Hours', f"{gt.get('total_overtime_hours', 0):.2f} hrs"),
        ('Grand Total Payroll Budget', f"Rs {gt.get('total_salary', 0):,.2f}"),
    ]

    for g_idx, (gt_label, gt_value) in enumerate(gt_items):
        g_row = gt_start_row + 1 + g_idx
        ws.row_dimensions[g_row].height = 22

        ws.merge_cells(start_row=g_row, start_column=1, end_row=g_row, end_column=2)
        c_l = ws.cell(row=g_row, column=1, value=gt_label)
        c_l.font = summary_label_font
        c_l.fill = summary_row_fill
        c_l.alignment = left_align
        c_l.border = thin_border
        ws.cell(row=g_row, column=2).border = thin_border

        ws.merge_cells(start_row=g_row, start_column=3, end_row=g_row, end_column=num_cols)
        c_v = ws.cell(row=g_row, column=3, value=gt_value)
        c_v.font = grand_total_font
        c_v.fill = summary_total_fill if g_idx == 2 else summary_row_fill
        c_v.alignment = left_align
        for c in range(3, num_cols + 1):
            ws.cell(row=g_row, column=c).border = thin_border

    # 6. Dynamic Auto-Fitting Column Dimensions based on actual data
    for col_idx in range(1, num_cols + 1):
        col_letter = get_column_letter(col_idx)
        max_len = 0
        for r_idx in range(4, ws.max_row + 1):
            if r_idx in (1, 2, 3) or r_idx == summary_start_row or r_idx >= gt_start_row:
                continue
            if summary_start_row < r_idx < gt_start_row and col_idx == 2:
                continue
            cell = ws.cell(row=r_idx, column=col_idx)
            if cell.value is not None:
                val_str = str(cell.value)
                line_len = max((len(l) for l in val_str.split('\n')), default=0)
                if line_len > max_len:
                    max_len = line_len

        if col_idx == 1:
            ws.column_dimensions[col_letter].width = max(max_len + 4, 16)
        elif col_idx == 2:
            ws.column_dimensions[col_letter].width = max(max_len + 4, 14)
        else:
            ws.column_dimensions[col_letter].width = max(max_len + 5, 26)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"comprehensive_report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
    resp = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    resp['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp


class ExcelRenderer(BaseRenderer):
    media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    format = 'excel'
    charset = None

    def render(self, data, media_type=None, renderer_context=None):
        return data


class ComprehensiveReportView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [JSONRenderer, ExcelRenderer]

    def get(self, request):
        return self._handle(request)

    def post(self, request):
        return self._handle(request)

    def _handle(self, request):
        data = {}
        if request.method == 'GET':
            data = request.query_params.dict()
            emp_param = request.query_params.getlist('employee_ids')
            if emp_param:
                ids = []
                for part in emp_param:
                    for x in part.split(','):
                        x = x.strip()
                        if x:
                            try:
                                ids.append(int(x))
                            except ValueError:
                                pass
                if ids:
                    data['employee_ids'] = ids
        else:
            data = request.data

        serializer = ComprehensiveReportInputSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        start_date = serializer.validated_data['start_date']
        end_date = serializer.validated_data['end_date']
        fmt = serializer.validated_data.get('format', 'json')
        emp_ids = serializer.validated_data.get('employee_ids', None)

        employees_qs = Employee.objects.filter(status='active').select_related('current_shift').order_by('emp_id')
        if emp_ids:
            employees_qs = employees_qs.filter(emp_id__in=emp_ids)

        if not employees_qs.exists():
            return Response({"error": "No active employees found"}, status=status.HTTP_404_NOT_FOUND)

        attendances = Attendance.objects.filter(
            date__range=[start_date, end_date], employee__in=employees_qs
        ).select_related('employee')

        overtimes = Overtime.objects.filter(
            date__range=[start_date, end_date], employee__in=employees_qs, status='approved'
        ).select_related('employee')

        leaves = PaidLeave.objects.filter(
            start_time__date__lte=end_date, end_time__date__gte=start_date,
            employee__in=employees_qs, approved=True
        ).select_related('employee')

        holidays = Holiday.objects.filter(date__range=[start_date, end_date])
        holidays_by_date = {h.date: h for h in holidays}

        shift_history = EmployeeShiftHistory.objects.filter(
            employee__in=employees_qs, from_date__lte=end_date
        ).filter(
            Q(to_date__isnull=True) | Q(to_date__gte=start_date)
        ).select_related('shift', 'employee').order_by('employee', 'from_date')

        att_map = {}
        for a in attendances:
            att_map.setdefault(a.employee.emp_id, {}).setdefault(a.date, []).append(a)

        ot_map = {}
        for o in overtimes:
            ot_map.setdefault(o.employee.emp_id, {})[o.date] = o

        leaves_map = {}
        for lv in leaves:
            leaves_map.setdefault(lv.employee.emp_id, {}).setdefault(lv.start_time.date(), []).append(lv)

        sh_map = {}
        for sh in shift_history:
            sh_map.setdefault(sh.employee.emp_id, []).append(sh)

        employee_info_list = []
        for emp in employees_qs:
            shift_dict = None
            working_hours_display = "No Shift Assigned"
            if emp.current_shift:
                st = emp.current_shift.start_time
                et = emp.current_shift.end_time
                st_str = st.strftime('%I:%M %p') if st else ''
                et_str = et.strftime('%I:%M %p') if et else ''
                
                if st and et:
                    st_dt = datetime.combine(date.today(), st)
                    et_dt = datetime.combine(date.today(), et)
                    if et <= st:
                        et_dt += timedelta(days=1)
                    s_hours = (et_dt - st_dt).total_seconds() / 3600
                    working_hours_display = f"{st_str} - {et_str} ({s_hours:g} hrs)"
                elif st_str and et_str:
                    working_hours_display = f"{st_str} - {et_str}"
                else:
                    working_hours_display = emp.current_shift.name
                
                shift_dict = {
                    'id': emp.current_shift.id,
                    'name': emp.current_shift.name,
                    'start_time': st_str,
                    'end_time': et_str,
                    'working_hours': working_hours_display,
                }
            
            off_day_display = emp.get_weekly_off_day_display() if emp.weekly_off_day is not None else "None"

            employee_info_list.append({
                'emp_id': emp.emp_id,
                'name': emp.name or f"Emp {emp.emp_id}",
                'designation': emp.designation or '',
                'current_shift': shift_dict,
                'working_hours': working_hours_display,
                'weekly_off_day': emp.weekly_off_day,
                'weekly_off_day_name': off_day_display,
                'salary': emp.salary,
                'hourly_rate': emp.hourly_rate,
            })

        matrix = []
        current_date = start_date
        today = timezone.now().date()

        while current_date <= end_date:
            weekday = WEEKDAY_NAMES[current_date.weekday()]
            holiday = holidays_by_date.get(current_date)
            is_holiday = holiday is not None
            is_off = False
            cells = {}

            for emp in employees_qs:
                emp_id = emp.emp_id
                weekly_off = emp.weekly_off_day
                is_off = weekly_off is not None and current_date.weekday() == weekly_off

                raw_atts = att_map.get(emp_id, {}).get(current_date, [])
                att_list = sorted(raw_atts, key=lambda a: a.check_in if a.check_in else datetime.min)
                ot_rec = ot_map.get(emp_id, {}).get(current_date)
                lv_records = leaves_map.get(emp_id, {}).get(current_date, [])

                leave_type = None
                on_leave = False
                for lv in lv_records:
                    lv_start = lv.start_time.date()
                    lv_end = lv.end_time.date()
                    if lv_start <= current_date <= lv_end:
                        on_leave = True
                        leave_type = lv.leave_type
                        break

                in_time = None
                out_time = None
                status_val = 'absent'
                ot_hours = 0.0
                sessions = []

                if on_leave:
                    status_val = 'leave'
                elif is_holiday:
                    status_val = 'holiday'
                elif att_list:
                    first_att = att_list[0]
                    last_att = att_list[-1]
                    in_time = first_att.check_in.time() if first_att.check_in else None
                    out_time = last_att.check_out.time() if last_att.check_out else None
                    is_late_day = any(a.status == 'late' for a in att_list)
                    status_val = 'late' if is_late_day else 'on_time'

                    for a in att_list:
                        s_in = a.check_in.strftime('%I:%M:%S %p') if a.check_in else '--:--'
                        s_out = a.check_out.strftime('%I:%M:%S %p') if a.check_out else '--:--'
                        s_hrs = float(a.total_hours)
                        s_disp = format_hours_display(s_hrs)
                        sessions.append({
                            'id': a.id,
                            'check_in': s_in,
                            'check_out': s_out,
                            'total_hours': s_hrs,
                            'total_hours_display': s_disp,
                            'status': a.status,
                            'is_late': a.is_late,
                            'text': f"{s_in} - {s_out} ({s_disp})"
                        })

                    # Auto overtime from attendance (after shift end)
                    emp_sh = sh_map.get(emp_id, [])
                    app_sh = None
                    for sh_entry in emp_sh:
                        sh_from = sh_entry.from_date
                        sh_to = sh_entry.to_date if sh_entry.to_date else end_date
                        if sh_from <= current_date <= sh_to:
                            app_sh = sh_entry
                            break
                    if app_sh and app_sh.shift:
                        ot_s_start = app_sh.shift_start_time or app_sh.shift.start_time
                        ot_s_end = app_sh.shift_end_time or app_sh.shift.end_time
                        if last_att.check_out and ot_s_start and ot_s_end:
                            att_shift_end = datetime.combine(current_date, ot_s_end)
                            if ot_s_end <= ot_s_start:
                                att_shift_end += timedelta(days=1)
                            if last_att.check_out > att_shift_end:
                                auto_ot = (last_att.check_out - att_shift_end).total_seconds() / 3600
                                ot_hours += max(0, auto_ot)
                elif is_off:
                    status_val = 'off_day'
                else:
                    status_val = 'absent' if current_date < today else 'absent'

                if ot_rec:
                    ot_hours += float(ot_rec.total_hours)

                in_str = in_time.strftime('%I:%M:%S %p') if in_time else None
                out_str = out_time.strftime('%I:%M:%S %p') if out_time else None
                
                day_total_hours = round(sum(float(a.total_hours) for a in att_list), 2) if att_list else 0.0
                day_total_hours_display = format_hours_display(day_total_hours) if att_list else "0h 0m"

                cells[str(emp_id)] = {
                    'in_time': in_str,
                    'out_time': out_str if out_str else (' --:-- ' if in_str else None),
                    'status': status_val,
                    'total_hours': day_total_hours,
                    'total_hours_display': day_total_hours_display,
                    'sessions_count': len(sessions),
                    'sessions': sessions,
                    'overtime_hours': round(ot_hours, 2),
                    'leave': on_leave,
                    'leave_type': leave_type,
                    'absent': status_val == 'absent',
                    'off_day': is_off,
                    'holiday_name': holiday.name if holiday else None,
                }

            matrix.append({
                'date': current_date,
                'weekday': weekday,
                'is_holiday': is_holiday,
                'is_off_day': is_off,
                'cells': cells,
            })

            current_date += timedelta(days=1)

        summary = {}
        grand_hours = 0
        grand_ot_hours = 0
        grand_salary = 0

        for emp in employees_qs:
            emp_id = emp.emp_id
            total_hours = 0.0
            total_ot_hours = 0.0
            days_present = 0
            days_absent = 0
            days_leave = 0
            weekly_off_count = 0
            holiday_count = 0
            regular_pay = 0.0
            overtime_pay = 0.0
            holiday_pay = 0.0
            leave_pay = 0.0
            off_day_pay = 0.0

            emp_sh = sh_map.get(emp_id, [])

            date_shift_info = {}
            for row in matrix:
                d = row['date']
                cell = row['cells'].get(str(emp_id), {})
                if not cell:
                    continue

                applicable_sh = None
                for sh_entry in emp_sh:
                    sh_from = sh_entry.from_date
                    sh_to = sh_entry.to_date if sh_entry.to_date else end_date
                    if sh_from <= d <= sh_to:
                        applicable_sh = sh_entry
                        break

                if not applicable_sh:
                    continue

                shift = applicable_sh.shift
                if not shift:
                    continue
                s_start = applicable_sh.shift_start_time or shift.start_time
                s_end = applicable_sh.shift_end_time or shift.end_time
                if not s_start or not s_end:
                    continue

                s_seconds = (datetime.combine(date.today(), s_end) -
                             datetime.combine(date.today(), s_start)).total_seconds()
                if s_seconds <= 0:
                    s_seconds += 86400
                shift_hours = s_seconds / 3600
                salary_value = get_salary_for_date(emp, d) or applicable_sh.salary or emp.salary or 0
                hourly_rate_val = _prorate_salary(salary_value, 1) / shift_hours if shift_hours > 0 else 0

                date_shift_info[d] = {
                    'shift_hours': shift_hours,
                    'salary_value': float(salary_value),
                    'hourly_rate': hourly_rate_val,
                    's_start': s_start,
                    's_end': s_end,
                }

            for row in matrix:
                d = row['date']
                cell = row['cells'].get(str(emp_id), {})
                if not cell:
                    continue

                si = date_shift_info.get(d)
                if not si:
                    continue

                sh = si['shift_hours']
                hr = si['hourly_rate']
                st = cell.get('status')
                ot_h = float(cell.get('overtime_hours', 0) or 0)

                if st == 'on_time' or st == 'late':
                    day_hours = float(cell.get('total_hours', 0.0) or 0.0)
                    total_hours += day_hours
                    days_present += 1
                    regular_pay += day_hours * hr
                elif st == 'absent':
                    days_absent += 1
                elif st == 'leave':
                    days_leave += 1
                    total_hours += sh
                    leave_pay += sh * hr
                elif st == 'holiday':
                    holiday_count += 1
                    total_hours += sh
                    holiday_pay += sh * hr
                elif st == 'off_day':
                    weekly_off_count += 1
                    total_hours += sh
                    off_day_pay += sh * hr

                if ot_h > 0:
                    total_ot_hours += ot_h
                    overtime_pay += ot_h * hr

            total_salary = regular_pay + overtime_pay + holiday_pay + leave_pay + off_day_pay

            summary[str(emp_id)] = {
                'emp_id': emp_id,
                'name': emp.name,
                'total_hours': round(total_hours, 2),
                'total_overtime_hours': round(total_ot_hours, 2),
                'days_present': days_present,
                'days_absent': days_absent,
                'days_leave': days_leave,
                'weekly_off_days': weekly_off_count,
                'holiday_days': holiday_count,
                'regular_pay': round(regular_pay, 2),
                'overtime_pay': round(overtime_pay, 2),
                'holiday_pay': round(holiday_pay, 2),
                'leave_pay': round(leave_pay, 2),
                'off_day_pay': round(off_day_pay, 2),
                'total_salary': round(total_salary, 2),
            }

            grand_hours += total_hours
            grand_ot_hours += total_ot_hours
            grand_salary += total_salary

        grand_totals = {
            'total_employees': employees_qs.count(),
            'total_hours': round(grand_hours, 2),
            'total_overtime_hours': round(grand_ot_hours, 2),
            'total_salary': round(grand_salary, 2),
        }

        output_data = {
            'date_range': {'start': start_date, 'end': end_date},
            'generated_at': timezone.now(),
            'employees': employee_info_list,
            'matrix': matrix,
            'summary': summary,
            'grand_totals': grand_totals,
        }

        if fmt == 'excel':
            return _build_excel_response(output_data, start_date, end_date)

        return Response(output_data)


class ActivityLogFilter(filters.FilterSet):
    category = filters.CharFilter(field_name='category', lookup_expr='exact')
    action_type = filters.CharFilter(field_name='action_type', lookup_expr='exact')
    actor = filters.NumberFilter(field_name='actor__id', lookup_expr='exact')
    actor_username = filters.CharFilter(field_name='actor_username', lookup_expr='icontains')
    target_model = filters.CharFilter(field_name='target_model', lookup_expr='exact')
    target_id = filters.CharFilter(field_name='target_id', lookup_expr='exact')
    target_name = filters.CharFilter(field_name='target_name', lookup_expr='icontains')
    date_from = filters.DateFilter(field_name='created_at__date', lookup_expr='gte')
    date_to = filters.DateFilter(field_name='created_at__date', lookup_expr='lte')
    search = filters.CharFilter(method='filter_search')

    class Meta:
        model = ActivityLog
        fields = [
            'category', 'action_type', 'actor', 'actor_username',
            'target_model', 'target_id', 'target_name', 'date_from', 'date_to', 'search'
        ]

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        val = str(value).strip()
        return queryset.filter(
            Q(description__icontains=val) |
            Q(actor_username__icontains=val) |
            Q(actor_name__icontains=val) |
            Q(target_name__icontains=val) |
            Q(target_id__icontains=val) |
            Q(action_type__icontains=val) |
            Q(category__icontains=val)
        )


class ActivityLogPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing Activity Logs across the portal.
    Endpoints:
    - GET /api/activities/
    - GET /api/activities/{id}/
    - GET /api/activities/summary/
    - GET /api/activities/categories/
    """
    queryset = ActivityLog.objects.all().select_related('actor')
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAdmin]
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ActivityLogFilter
    pagination_class = ActivityLogPagination

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Returns statistics and overview breakdown of activity logs."""
        from django.db.models import Count
        today = timezone.now().date()
        total_count = ActivityLog.objects.count()
        today_count = ActivityLog.objects.filter(created_at__date=today).count()

        category_counts = list(
            ActivityLog.objects.values('category')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        action_counts = list(
            ActivityLog.objects.values('action_type')
            .annotate(count=Count('id'))
            .order_by('-count')[:15]
        )

        recent = ActivityLog.objects.all()[:10]
        recent_serialized = ActivityLogSerializer(recent, many=True).data

        return Response({
            "total_activities": total_count,
            "today_activities": today_count,
            "categories_breakdown": category_counts,
            "top_actions": action_counts,
            "recent_activities": recent_serialized
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Returns the dictionary/list of categories and actions available for filtering."""
        return Response({
            "categories": [{"key": c[0], "label": c[1]} for c in ActivityLog.CATEGORY_CHOICES],
            "actions": [{"key": a[0], "label": a[1]} for a in ActivityLog.ACTION_CHOICES],
        }, status=status.HTTP_200_OK)
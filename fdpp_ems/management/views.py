from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters import rest_framework as filters
from django.contrib.auth.models import User
from .models import Employee, Attendance, PaidLeave, Shift, UserAccessLevel
from .serializers import (
    EmployeeSerializer, AttendanceSerializer, PaidLeaveSerializer, 
    ShiftSerializer, UserSerializer, UserAccessLevelSerializer,
    CreateAdminManagerSerializer, RegisterSerializer
)
from django.db.models import Sum, Count, Q, Avg
from datetime import datetime, timedelta, date
from django.utils import timezone
from fdpp_ems import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# Permission check: Only admins can create admin/manager
def is_admin(user):
    """Check if user has admin role"""
    try:
        return user.access_level.role == 'admin'
    except (AttributeError, UserAccessLevel.DoesNotExist):
        return False

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
                    "phone": employee.phone,
                    "CNIC": employee.CNIC,
                    "shift_type": employee.shift_type,
                    "start_time": str(employee.start_time),
                    "end_time": str(employee.end_time),
                    # "profile_img": employee.profile_img.url if employee.profile_img else None
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
            
            response_data = {
                "message": f"User created successfully as {serializer.validated_data['role']}",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": serializer.validated_data['role'],
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
                return Response({
                    "message": "Login successful",
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": access_level.role
                }, status=status.HTTP_200_OK)
            except UserAccessLevel.DoesNotExist:
                # Try to get employee profile if user has one
                try:
                    employee = user.employee_profile
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
                    return Response(
                        {"error": "User profile not found"},
                        status=status.HTTP_404_NOT_FOUND
                    )
        return Response(
            {"error": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED
        )


class UserAccessLevelViewSet(viewsets.ModelViewSet):
    """Manage user access levels (admin/manager)"""
    queryset = UserAccessLevel.objects.all()
    serializer_class = UserAccessLevelSerializer
    permission_classes = [IsAdmin]
    
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


# Filtering logic for Attendance
class AttendanceFilter(filters.FilterSet):
    date_from = filters.DateFilter(field_name="date", lookup_expr='gte')
    date_to = filters.DateFilter(field_name="date", lookup_expr='lte')
    employee = filters.CharFilter(field_name="employee__emp_id")
    status = filters.CharFilter(field_name="status")

    class Meta:
        model = Attendance
        fields = ['employee', 'date_from', 'date_to', 'status']

class EmployeeFilter(filters.FilterSet):
    employee_id = filters.NumberFilter(field_name="emp_id", lookup_expr='exact')
    employee_name = filters.CharFilter(field_name="name", lookup_expr='icontains')
    status = filters.CharFilter(field_name="status")

    class Meta:
        model = Employee
        fields = ['employee_id', 'employee_name', 'status', 'shift_type']

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    filterset_class = EmployeeFilter
    filter_backends = (filters.DjangoFilterBackend,)
    lookup_field = 'emp_id'  # Use emp_id for URL lookups like /employees/EMP001/
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['get'])
    def calculate_payout(self, request, emp_id=None):
        """Calculates salary based on attendance and hourly rate."""
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

        attendances = Attendance.objects.filter(
            employee=employee, 
            date__range=[start_date, end_date]
        )
        
        total_worked_hours = sum(att.total_hours for att in attendances)
        payout = float(total_worked_hours) * float(employee.hourly_rate)

        return Response({
            "employee_id": employee.emp_id,
            "employee_name": employee.name,
            "period": f"{start_date} to {end_date}",
            "total_hours": total_worked_hours,
            "hourly_rate": float(employee.hourly_rate),
            "total_payout": float(payout)
        })

    @action(detail=True, methods=['get'])
    def attendance_report(self, request, emp_id=None):
        """Get attendance report for an employee with filters"""
        employee = self.get_object()
        period = request.query_params.get('period', 'month')  # day, week, month, custom
        
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
            start_date_str = request.query_params.get('start_date')
            end_date_str = request.query_params.get('end_date')
            if not start_date_str or not end_date_str:
                return Response(
                    {"error": "Please provide start_date and end_date for custom period"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                {"error": "Invalid period. Use: day, week, month, or custom"},
                status=status.HTTP_400_BAD_REQUEST
            )

        attendances = Attendance.objects.filter(
            employee=employee,
            date__range=[start_date, end_date]
        ).order_by('-date')

        total_hours = sum(att.total_hours for att in attendances)
        total_days = attendances.count()
        late_count = attendances.filter(status='late').count()
        on_time_count = attendances.filter(status='on_time').count()

        return Response({
            "employee_id": employee.emp_id,
            "employee_name": employee.name,
            "period": f"{start_date} to {end_date}",
            "total_days_worked": total_days,
            "total_hours": total_hours,
            "on_time": on_time_count,
            "late": late_count,
            "attendance_records": AttendanceSerializer(attendances, many=True).data
        })

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

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all().order_by('-date')
    serializer_class = AttendanceSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = AttendanceFilter
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def daily_report(self, request):
        """Get daily attendance report"""
        date_str = request.query_params.get('date')
        today = timezone.now().date()
        
        if not date_str:
            report_date = today
        else:
            try:
                report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        attendances = Attendance.objects.filter(date=report_date)
        total_employees = Employee.objects.filter(status='active').count()
        present = attendances.count()
        absent = total_employees - present
        late = attendances.filter(status='late').count()
        on_time = attendances.filter(status='on_time').count()

        return Response({
            "date": report_date,
            "total_active_employees": total_employees,
            "present": present,
            "absent": absent,
            "on_time": on_time,
            "late": late,
            "attendance_details": AttendanceSerializer(attendances, many=True).data
        })

    @action(detail=False, methods=['get'])
    def weekly_report(self, request):
        """Get weekly attendance report"""
        today = timezone.now().date()
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)

        attendances = Attendance.objects.filter(
            date__range=[start_date, end_date]
        )

        total_hours = sum(att.total_hours for att in attendances)
        late_arrivals = attendances.filter(status='late').count()

        return Response({
            "week": f"{start_date} to {end_date}",
            "total_records": attendances.count(),
            "total_hours": total_hours,
            "late_arrivals": late_arrivals,
            "average_hours_per_day": round(total_hours / 7, 2) if attendances.exists() else 0
        })

    @action(detail=False, methods=['get'])
    def monthly_report(self, request):
        """Get monthly attendance report"""
        today = timezone.now().date()
        month = request.query_params.get('month', today.month)
        year = request.query_params.get('year', today.year)

        try:
            month = int(month)
            year = int(year)
        except ValueError:
            return Response(
                {"error": "Invalid month or year"},
                status=status.HTTP_400_BAD_REQUEST
            )

        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        attendances = Attendance.objects.filter(
            date__range=[start_date, end_date]
        )

        total_hours = sum(att.total_hours for att in attendances)
        total_days = attendances.count()
        unique_employees = attendances.values('employee').distinct().count()
        late_arrivals = attendances.filter(status='late').count()

        return Response({
            "month": f"{year}-{month:02d}",
            "total_working_days": total_days,
            "total_hours_worked": total_hours,
            "unique_employees": unique_employees,
            "late_arrivals": late_arrivals,
            "average_daily_attendance": round(total_days / unique_employees, 2) if unique_employees > 0 else 0
        })

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

        today = timezone.now().date()
        now = timezone.now()

        # Check if already checked in today
        existing = Attendance.objects.filter(employee=employee, date=today).first()
        if existing:
            return Response(
                {"error": "Already checked in today", "record": AttendanceSerializer(existing).data},
                status=status.HTTP_400_BAD_REQUEST
            )

        attendance = Attendance.objects.create(
            employee=employee,
            date=today,
            check_in=now,
            status='on_time' if now.time() <= employee.start_time else 'late'
        )

        return Response(
            {
                "message": "Check-in successful",
                "record": AttendanceSerializer(attendance).data
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def check_out(self, request):
        """Check out an employee"""
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

        today = timezone.now().date()
        now = timezone.now()

        # Get today's attendance
        attendance = Attendance.objects.filter(employee=employee, date=today).first()
        
        if not attendance:
            return Response(
                {"error": "No check-in record found for today"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if attendance.check_out:
            return Response(
                {"error": "Already checked out today"},
                status=status.HTTP_400_BAD_REQUEST
            )

        attendance.check_out = now
        attendance.save()

        return Response(
            {
                "message": "Check-out successful",
                "total_hours": attendance.total_hours,
                "record": AttendanceSerializer(attendance).data
            },
            status=status.HTTP_200_OK
        )

  
    from datetime import datetime  # Make sure this is at the very top of views.py

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def auto_attendance(self, request):
        emp_id = request.data.get('emp_id')
        
        if not emp_id:
            return Response({"error": "emp_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            employee = Employee.objects.get(emp_id=emp_id)
        except Employee.DoesNotExist:
            return Response({"error": f"Employee with id {emp_id} not found"}, status=status.HTTP_404_NOT_FOUND)

        # UPDATED: Use system clock time (since USE_TZ = False)
        now = datetime.now() 
        today = now.date()
        current_time = now.time()
        
        last_attendance = Attendance.objects.filter(employee=employee, date=today).order_by('-check_in').first()
        first_checkin = Attendance.objects.filter(employee=employee, date=today).order_by('check_in').first()

        attendance_info = {
            "emp_id": employee.emp_id,
            "employee_name": employee.name,
            "profile_img": f"http://{settings.SERVER_IP}:{settings.SERVER_PORT}{employee.profile_img.url}" if employee.profile_img else None,
            "shift_type": employee.shift_type,
            "timestamp": now.strftime('%I:%M %p'), 
        }
        
        # Determine action: Check-in or Check-out
        if not last_attendance or (last_attendance.check_out is not None):
            # ===== NEW CHECK-IN =====
            shift_start = employee.start_time
            is_late = current_time > shift_start
            
            status_val = 'late' if is_late else 'on_time'
            
            late_msg = "On time"
            if is_late:
                # UPDATED: No timezone awareness needed because USE_TZ = False
                shift_start_dt = datetime.combine(today, shift_start)
                minutes_late = int((now - shift_start_dt).total_seconds() / 60)
                late_msg = f"{minutes_late} minutes late"
            
            attendance = Attendance.objects.create(
                employee=employee,
                date=today,
                check_in=now, # Saves literal system time to DB
                message_late=late_msg,
                status=status_val
            )
            
            action = "check_in"
            message = "Check-in successful"
            attendance_info.update({
                "action": action,
                "check_in": now.strftime('%I:%M %p'),
                "check_out": "--:--",
                "is_late": is_late,
                "late_message": late_msg,
                "total_hours_today": 0
            })
            
        elif last_attendance.check_in is not None and last_attendance.check_out is None:
            # ===== CHECK-OUT =====
            # Both are now "naive" datetimes, so math works perfectly
            duration = (now - last_attendance.check_in).total_seconds() / 3600
            if duration > 14:
                return Response({"error": "Duration exceeds 14-hour limit"}, status=status.HTTP_400_BAD_REQUEST)
            
            last_attendance.check_out = now # Saves literal system time to DB
            last_attendance.save()
            
            total_hours = 0
            if first_checkin:
                total_duration = (now - first_checkin.check_in).total_seconds() / 3600
                total_hours = round(min(total_duration, 14.0), 2)
            
            action = "check_out"
            message = "Check-out successful"
            attendance_info.update({
                "action": action,
                # UPDATED: Just use the time in DB directly (it's already local)
                "check_in": last_attendance.check_in.strftime('%I:%M %p'),
                "check_out": now.strftime('%I:%M %p'),
                "is_late": False,
                "late_message": None,
                "total_hours_today": total_hours
            })

        response_payload = {
            "message": message,
            "action": action,
            "data": attendance_info
        }

        # Broadcast to WebSocket
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

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a leave request"""
        leave = self.get_object()
        leave.approved = True
        leave.approved_by = request.data.get('approved_by', 'Admin')
        leave.save()
        return Response(
            {"message": "Leave approved", "leave": PaidLeaveSerializer(leave).data}
        )

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a leave request"""
        leave = self.get_object()
        leave.delete()
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

class ShiftViewSet(viewsets.ModelViewSet):
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer
    permission_classes = [IsAuthenticated]
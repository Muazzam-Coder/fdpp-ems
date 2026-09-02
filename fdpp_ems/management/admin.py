from django.contrib import admin
from .models import Employee, Attendance, PaidLeave, Shift, UserAccessLevel, EmployeeShiftHistory, Holiday, Overtime, Salary


@admin.register(UserAccessLevel)
class UserAccessLevelAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ['user']
        }),
        ('Access Level', {
            'fields': ['role']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    )


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['emp_id', 'name', 'designation', 'current_shift', 'weekly_off_day', 'status', 'date_joined']
    list_filter = ['status', 'designation', 'current_shift', 'date_joined']
    search_fields = ['emp_id', 'name', 'designation', 'CNIC', 'phone']
    readonly_fields = ['emp_id', 'last_modified']
    fieldsets = (
        ('Employee ID', {
            'fields': ['emp_id']
        }),
        ('Personal Information', {
            'fields': ['name', 'designation', 'profile_img', 'address', 'phone', 'CNIC']
        }),
        ('Emergency Contact', {
            'fields': ['relative', 'r_phone', 'r_address']
        }),
        ('Shift Information', {
            'fields': ['current_shift', 'weekly_off_day']
        }),
        ('Financial Information', {
            'fields': ['salary', 'hourly_rate']
        }),
        ('Status & Dates', {
            'fields': ['status', 'date_joined', 'last_modified']
        }),
    )


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['date', 'employee', 'check_in', 'check_out', 'total_hours', 'status']
    list_filter = ['date', 'status', 'employee__current_shift']
    search_fields = ['employee__emp_id', 'employee__name']
    readonly_fields = ['total_hours', 'overtime_hours', 'is_late', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Employee', {
            'fields': ['employee']
        }),
        ('Attendance Details', {
            'fields': ['date', 'check_in', 'check_out', 'status', 'message_late']
        }),
        ('Calculated Fields', {
            'fields': ['total_hours', 'overtime_hours', 'is_late'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    )


@admin.register(PaidLeave)
class PaidLeaveAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_time', 'end_time', 'approved']
    list_filter = ['leave_type', 'approved', 'start_time']
    search_fields = ['employee__emp_id', 'employee__name']
    readonly_fields = ['duration_days', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Employee & Leave Type', {
            'fields': ['employee', 'leave_type']
        }),
        ('Leave Duration', {
            'fields': ['start_time', 'end_time', 'duration_days']
        }),
        ('Details', {
            'fields': ['reason']
        }),
        ('Approval', {
            'fields': ['approved', 'approved_by']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    )


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_time', 'end_time']
    search_fields = ['name']


@admin.register(EmployeeShiftHistory)
class EmployeeShiftHistoryAdmin(admin.ModelAdmin):
    list_display = ['employee', 'shift', 'from_date', 'to_date', 'salary']
    list_filter = ['shift', 'from_date', 'to_date']
    search_fields = ['employee__name', 'employee__emp_id', 'shift__name']
    readonly_fields = ['salary', 'shift_start_time', 'shift_end_time']
    autocomplete_fields = ['employee', 'shift']


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ['date', 'name', 'is_paid']
    list_filter = ['is_paid', 'date']
    search_fields = ['name']


@admin.register(Overtime)
class OvertimeAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'start_time', 'end_time', 'status', 'approved_by']
    list_filter = ['status', 'date']
    search_fields = ['employee__name', 'employee__emp_id']


@admin.register(Salary)
class SalaryAdmin(admin.ModelAdmin):
    list_display = ['employee', 'salary', 'effective_from', 'effective_to', 'created_at']
    list_filter = ['effective_from']
    search_fields = ['employee__name', 'employee__emp_id']
    readonly_fields = ['created_at']

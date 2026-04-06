from django.contrib import admin
from .models import Employee, Attendance, PaidLeave, Shift

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['emp_id', 'name', 'shift_type', 'status', 'date_joined']
    list_filter = ['status', 'shift_type', 'date_joined']
    search_fields = ['emp_id', 'name', 'CNIC', 'phone']
    readonly_fields = ['date_joined', 'last_modified']
    fieldsets = (
        ('Personal Information', {
            'fields': ['emp_id', 'name', 'profile_img', 'address', 'phone', 'CNIC']
        }),
        ('Emergency Contact', {
            'fields': ['relative', 'r_phone', 'r_address']
        }),
        ('Shift Information', {
            'fields': ['shift_type', 'start_time', 'end_time']
        }),
        ('Financial Information', {
            'fields': ['salary', 'hourly_rate']
        }),
        ('Status', {
            'fields': ['status', 'date_joined', 'last_modified']
        }),
    )

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['date', 'employee', 'check_in', 'check_out', 'total_hours', 'status']
    list_filter = ['date', 'status', 'employee__shift_type']
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


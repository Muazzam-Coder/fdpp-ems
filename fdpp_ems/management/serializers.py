from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Employee, Attendance, PaidLeave, Shift
from django.utils import timezone

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = '__all__'

class EmployeeSerializer(serializers.ModelSerializer):
    total_hours_today = serializers.ReadOnlyField()
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'emp_id', 'user', 'username', 'email', 'name', 'profile_img', 
            'salary', 'hourly_rate', 'shift_type', 'start_time', 'end_time', 
            'address', 'phone', 'CNIC', 'relative', 'r_phone', 'r_address', 
            'status', 'date_joined', 'last_modified', 'total_hours_today'
        ]
        read_only_fields = ['emp_id', 'date_joined', 'last_modified']

class AttendanceSerializer(serializers.ModelSerializer):
    total_hours = serializers.ReadOnlyField()
    is_late = serializers.ReadOnlyField()
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'employee', 'employee_name', 'date', 'check_in', 'check_out',
            'message_late', 'status', 'total_hours', 'is_late',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, data):
        # Implement the 14-hour constraint during validation
        if data.get('check_in') and data.get('check_out'):
            if data['check_out'] < data['check_in']:
                raise serializers.ValidationError("Check-out cannot be before check-in.")
            
            duration = data['check_out'] - data['check_in']
            if duration.total_seconds() > 14 * 3600:
                raise serializers.ValidationError(
                    "Work duration cannot exceed 14 hours per shift."
                )
        return data

class PaidLeaveSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    duration_days = serializers.ReadOnlyField()
    
    class Meta:
        model = PaidLeave
        fields = [
            'id', 'employee', 'employee_name', 'leave_type', 'start_time',
            'end_time', 'reason', 'approved', 'approved_by', 'duration_days',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, data):
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError("End time must be after start time.")
        return data
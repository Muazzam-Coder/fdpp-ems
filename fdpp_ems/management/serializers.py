from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Employee, Attendance, PaidLeave, Shift, UserAccessLevel
from django.utils import timezone
from datetime import datetime

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class RegisterSerializer(serializers.Serializer):
    """Serializer for user registration with employee profile and image"""
    # User fields
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    
    # Employee fields
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    CNIC = serializers.CharField(max_length=20)
    address = serializers.CharField(required=False, allow_blank=True)
    relative = serializers.CharField(max_length=255, required=False, allow_blank=True)
    r_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    r_address = serializers.CharField(required=False, allow_blank=True)
    start_time = serializers.TimeField(required=False, default='09:00:00')
    end_time = serializers.TimeField(required=False, default='17:00:00')
    shift_type = serializers.CharField(max_length=100, required=False, default='morning')
    
    # Image upload
    profile_img = serializers.ImageField(required=False, allow_null=True)
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value
    
    def validate_CNIC(self, value):
        if Employee.objects.filter(CNIC=value).exists():
            raise serializers.ValidationError("CNIC already exists.")
        return value
    
    def create(self, validated_data):
        # Extract user-related fields
        user_data = {
            'username': validated_data['username'],
            'email': validated_data['email'],
            'password': validated_data['password'],
            'first_name': validated_data.get('first_name', ''),
            'last_name': validated_data.get('last_name', ''),
        }
        user = User.objects.create_user(**user_data)
        
        # Extract profile image
        profile_img = validated_data.get('profile_img')
        
        # Create employee profile
        employee = Employee.objects.create(
            user=user,
            name=validated_data.get('first_name', user.username),
            phone=validated_data.get('phone', ''),
            CNIC=validated_data.get('CNIC'),
            address=validated_data.get('address', ''),
            relative=validated_data.get('relative', ''),
            r_phone=validated_data.get('r_phone', ''),
            r_address=validated_data.get('r_address', ''),
            start_time=validated_data.get('start_time', '09:00:00'),
            end_time=validated_data.get('end_time', '17:00:00'),
            shift_type=validated_data.get('shift_type', 'morning'),
            profile_img=profile_img
        )
        
        return {'user': user, 'employee': employee}

class UserAccessLevelSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    profile_img = serializers.SerializerMethodField()
    
    class Meta:
        model = UserAccessLevel
        fields = ['id', 'user', 'username', 'email', 'first_name', 'last_name', 'profile_img', 'role', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_profile_img(self, obj):
        """Get profile image from user profile or employee"""
        try:
            # First try UserProfile
            if hasattr(obj.user, 'profile') and obj.user.profile.profile_img:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.user.profile.profile_img.url)
                return obj.user.profile.profile_img.url
        except (AttributeError, Exception):
            pass
        
        try:
            # Then try Employee profile
            if obj.user.employee_profile and obj.user.employee_profile.profile_img:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.user.employee_profile.profile_img.url)
                return obj.user.employee_profile.profile_img.url
        except (AttributeError, Employee.DoesNotExist):
            pass
        
        return None

class CreateAdminManagerSerializer(serializers.Serializer):
    """Serializer for creating admin or manager users with optional profile image"""
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    role = serializers.ChoiceField(choices=['admin', 'manager'], default='manager')
    profile_img = serializers.ImageField(required=False, allow_null=True)
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value
    
    def create(self, validated_data):
        from .models import UserProfile
        
        role = validated_data.pop('role')
        profile_img = validated_data.pop('profile_img', None)
        
        user = User.objects.create_user(**validated_data)
        UserAccessLevel.objects.update_or_create(user=user, defaults={'role': role})
        
        # Create user profile with image if provided
        if profile_img:
            UserProfile.objects.create(user=user, profile_img=profile_img)
        else:
            UserProfile.objects.create(user=user)
        
        return user

class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = '__all__'

class EmployeeSerializer(serializers.ModelSerializer):
    total_hours_today = serializers.ReadOnlyField()
    username = serializers.CharField(source='user.username', read_only=True, allow_null=True)
    email = serializers.CharField(source='user.email', read_only=True, allow_null=True)
    profile_img = serializers.SerializerMethodField()
    
    class Meta:
        model = Employee
        fields = [
            'id', 'emp_id', 'username', 'email', 'name', 'profile_img', 
            'salary', 'hourly_rate', 'shift_type', 'start_time', 'end_time', 
            'address', 'phone', 'CNIC', 'relative', 'r_phone', 'r_address', 
            'status', 'date_joined', 'last_modified', 'total_hours_today'
        ]
        read_only_fields = ['emp_id', 'username', 'email', 'last_modified']
    
    def get_profile_img(self, obj):
        """Return full URL for profile image"""
        if obj.profile_img:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_img.url)
            return obj.profile_img.url
        return None

class AttendanceSerializer(serializers.ModelSerializer):
    total_hours = serializers.ReadOnlyField()
    is_late = serializers.ReadOnlyField()
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    check_in_time = serializers.TimeField(write_only=True, format='%H:%M:%S')
    check_out_time = serializers.TimeField(write_only=True, format='%H:%M:%S', required=False, allow_null=True)
    check_in = serializers.SerializerMethodField(read_only=True)
    check_out = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'employee', 'employee_name', 'date', 'check_in', 'check_out',
            'check_in_time', 'check_out_time', 'message_late', 'status', 'total_hours', 'is_late',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'check_in', 'check_out']

    def get_check_in(self, obj):
        """Return only time portion of check_in"""
        if obj.check_in:
            return obj.check_in.strftime('%H:%M:%S')
        return None
    
    def get_check_out(self, obj):
        """Return only time portion of check_out"""
        if obj.check_out:
            return obj.check_out.strftime('%H:%M:%S')
        return None

    def validate(self, data):
        # Implement the 14-hour constraint during validation
        check_in_time = data.get('check_in_time')
        check_out_time = data.get('check_out_time')
        
        if check_in_time and check_out_time:
            if check_out_time < check_in_time:
                raise serializers.ValidationError("Check-out cannot be before check-in.")
            
            # Create temporary datetime objects to check duration
            temp_date = datetime.now().date()
            temp_check_in = datetime.combine(temp_date, check_in_time)
            temp_check_out = datetime.combine(temp_date, check_out_time)
            
            duration = temp_check_out - temp_check_in
            if duration.total_seconds() > 14 * 3600:
                raise serializers.ValidationError(
                    "Work duration cannot exceed 14 hours per shift."
                )
        return data
    
    def create(self, validated_data):
        check_in_time = validated_data.pop('check_in_time')
        check_out_time = validated_data.pop('check_out_time', None)
        date = validated_data.get('date')
        
        # Combine date with times to create DateTimeField values
        check_in = timezone.make_aware(datetime.combine(date, check_in_time))
        check_out = timezone.make_aware(datetime.combine(date, check_out_time)) if check_out_time else None
        
        validated_data['check_in'] = check_in
        validated_data['check_out'] = check_out
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        check_in_time = validated_data.pop('check_in_time', None)
        check_out_time = validated_data.pop('check_out_time', None)
        date = validated_data.get('date', instance.date)
        
        if check_in_time:
            validated_data['check_in'] = timezone.make_aware(datetime.combine(date, check_in_time))
        if check_out_time:
            validated_data['check_out'] = timezone.make_aware(datetime.combine(date, check_out_time))
        
        return super().update(instance, validated_data)

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
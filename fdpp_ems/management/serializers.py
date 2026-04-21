from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Employee, Attendance, PaidLeave, Shift, UserAccessLevel
from django.utils import timezone
from datetime import datetime


def format_hours_display(hours_value):
    if not hours_value:
        return "0h 0m"

    total_minutes = int(round(float(hours_value) * 60))
    hours = total_minutes // 60
    minutes = total_minutes % 60

    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"

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
    first_name = serializers.CharField(max_length=150, required=False, allow_null=True, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_null=True, allow_blank=True)
    
    # Employee fields
    designation = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True)
    CNIC = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True)
    address = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    relative = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    referance = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    # Accept list of existing Employee `emp_id` values to link as relatives
    relatives = serializers.ListField(child=serializers.CharField(), required=False)
    r_phone = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True)
    r_address = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    start_time = serializers.TimeField(required=False, allow_null=True)
    end_time = serializers.TimeField(required=False, allow_null=True)
    shift_type = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    
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
        if value in (None, ''):
            return value
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
            name=validated_data.get('first_name') or user.username,
            designation=validated_data.get('designation'),
            phone=validated_data.get('phone'),
            CNIC=validated_data.get('CNIC'),
            address=validated_data.get('address'),
            relative=validated_data.get('relative'),
            referance=validated_data.get('referance'),
            r_phone=validated_data.get('r_phone'),
            r_address=validated_data.get('r_address'),
            start_time=validated_data.get('start_time'),
            end_time=validated_data.get('end_time'),
            shift_type=validated_data.get('shift_type') or 'morning',
            profile_img=profile_img
        )
        # Link relatives (if provided) by their `emp_id` values or PKs
        relatives_inputs = validated_data.get('relatives') or []
        if relatives_inputs:
            # `relatives_inputs` may be list of Employee objects (if deserialized by field),
            # or a list of strings/ints when coming from RegisterSerializer path.
            if all(hasattr(x, 'pk') for x in relatives_inputs):
                for rel in relatives_inputs:
                    employee.relatives.add(rel)
            else:
                emp_ids = []
                for v in relatives_inputs:
                    vstr = str(v).strip()
                    # try emp_id lookup first
                    try:
                        e = Employee.objects.get(emp_id=vstr)
                        emp_ids.append(e.emp_id)
                        continue
                    except Employee.DoesNotExist:
                        pass
                    # try pk lookup
                    if vstr.isdigit():
                        try:
                            e = Employee.objects.get(pk=int(vstr))
                            emp_ids.append(e.emp_id)
                        except Employee.DoesNotExist:
                            pass
                if emp_ids:
                    relatives_qs = Employee.objects.filter(emp_id__in=emp_ids)
                    for rel in relatives_qs:
                        employee.relatives.add(rel)
        
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
    profile_img = serializers.ImageField(required=False, allow_null=True)
    designation = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    # Raw reference input saved as provided
    referance = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    # Accept list of employee `emp_id` values OR DB PKs to link relatives; writeable
    # Use a small custom field that accepts either `emp_id` (string) or numeric PK
    class EmpIdOrPkField(serializers.SlugRelatedField):
        def to_internal_value(self, value):
            qs = self.get_queryset()
            # Normalize
            if value is None:
                return None
            if isinstance(value, int):
                # try pk lookup first
                try:
                    return qs.get(pk=value)
                except Exception:
                    raise serializers.ValidationError(f"Employee with pk '{value}' does not exist")

            v = str(value).strip()
            if v == '':
                return None
            # Try emp_id lookup first
            try:
                return qs.get(emp_id=v)
            except Exception:
                # If value looks numeric, try pk as fallback
                if v.isdigit():
                    try:
                        return qs.get(pk=int(v))
                    except Exception:
                        pass
                raise serializers.ValidationError(f"Employee with emp_id or pk '{value}' does not exist")

    relatives = EmpIdOrPkField(many=True, slug_field='emp_id', queryset=Employee.objects.all(), required=False)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'emp_id', 'username', 'email', 'name', 'designation', 'profile_img', 
            'salary', 'hourly_rate', 'shift_type', 'start_time', 'end_time', 
            'address', 'phone', 'CNIC', 'relative', 'r_phone', 'r_address', 
            'status', 'date_joined', 'last_modified', 'total_hours_today', 'referance', 'relatives'
        ]
        read_only_fields = ['emp_id', 'username', 'email', 'last_modified']

    # relatives_info removed; responses should use the `relatives` variable from the relatives endpoint

    def create(self, validated_data):
        relatives = validated_data.pop('relatives', [])
        employee = super().create(validated_data)
        # Add relatives (ManyToMany symmetrical ensures both sides are linked)
        if relatives:
            # Filter out None values (allowed by EmpIdOrPkField when blank inputs provided)
            relatives = [r for r in relatives if r is not None]
            for rel in relatives:
                employee.relatives.add(rel)
        return employee

    def update(self, instance, validated_data):
        relatives = validated_data.pop('relatives', None)
        instance = super().update(instance, validated_data)
        if relatives is not None:
            # Replace relatives list (accepts Emp objects from custom field)
            # Filter out None values that may come from blank selections
            relatives = [r for r in relatives if r is not None]
            instance.relatives.set(relatives)
        return instance

class AttendanceSerializer(serializers.ModelSerializer):
    total_hours = serializers.SerializerMethodField()
    total_hours_value = serializers.SerializerMethodField()
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
            'total_hours_value', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'check_in', 'check_out']

    def get_total_hours(self, obj):
        return format_hours_display(obj.total_hours)

    def get_total_hours_value(self, obj):
        return obj.total_hours

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
    
    # management/serializers.py

    def create(self, validated_data):
        check_in_time = validated_data.pop('check_in_time')
        check_out_time = validated_data.pop('check_out_time', None)
        date = validated_data.get('date')
        
        # REMOVED: timezone.make_aware
        # UPDATED: Use standard datetime.combine
        check_in = datetime.combine(date, check_in_time)
        check_out = datetime.combine(date, check_out_time) if check_out_time else None
        
        validated_data['check_in'] = check_in
        validated_data['check_out'] = check_out
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        check_in_time = validated_data.pop('check_in_time', None)
        check_out_time = validated_data.pop('check_out_time', None)
        date = validated_data.get('date', instance.date)
        
        # REMOVED: timezone.make_aware
        if check_in_time:
            validated_data['check_in'] = datetime.combine(date, check_in_time)
        if check_out_time:
            validated_data['check_out'] = datetime.combine(date, check_out_time)
        
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
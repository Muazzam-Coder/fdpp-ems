from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Employee, Attendance, PaidLeave, Shift, UserAccessLevel,
    UserProfile, EmployeeShiftHistory, Holiday, Overtime, Salary,
    ActivityLog,
    get_overtime_max_allowed, get_employee_shift_times,
)
from datetime import datetime, timedelta


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
    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'username': {'required': True},
            'email': {'required': False, 'allow_blank': True, 'allow_null': True}
        }

    def validate_username(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError("Username is required.")
        qs = User.objects.filter(username=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def validate_email(self, value):
        if not value or not str(value).strip():
            return ""
        qs = User.objects.filter(email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def create(self, validated_data):
        if 'email' not in validated_data or validated_data['email'] is None:
            validated_data['email'] = ''
        user = User.objects.create_user(**validated_data)
        return user


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False, allow_null=True, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_null=True, allow_blank=True)

    designation = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True)
    CNIC = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True)
    address = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    relative = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    referance = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    relatives = serializers.ListField(child=serializers.CharField(), required=False)
    r_phone = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True)
    r_address = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    current_shift = serializers.PrimaryKeyRelatedField(
        queryset=Shift.objects.all(), required=False, allow_null=True
    )
    weekly_off_day = serializers.IntegerField(required=False, allow_null=True)

    profile_img = serializers.ImageField(required=False, allow_null=True)

    def validate_username(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError("Username is required.")
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def validate_email(self, value):
        if not value or not str(value).strip():
            return ""
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
        user_data = {
            'username': validated_data['username'],
            'email': validated_data.get('email') or '',
            'password': validated_data['password'],
            'first_name': validated_data.get('first_name', '') or '',
            'last_name': validated_data.get('last_name', '') or '',
        }
        user = User.objects.create_user(**user_data)

        profile_img = validated_data.get('profile_img')

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
            current_shift=validated_data.get('current_shift'),
            weekly_off_day=validated_data.get('weekly_off_day'),
            profile_img=profile_img
        )

        relatives_inputs = validated_data.get('relatives') or []
        if relatives_inputs:
            if all(hasattr(x, 'pk') for x in relatives_inputs):
                for rel in relatives_inputs:
                    employee.relatives.add(rel)
            else:
                emp_ids = []
                for v in relatives_inputs:
                    vstr = str(v).strip()
                    try:
                        e = Employee.objects.get(emp_id=vstr)
                        emp_ids.append(e.emp_id)
                        continue
                    except Employee.DoesNotExist:
                        pass
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
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    username = serializers.CharField(source='user.username', required=False)
    email = serializers.CharField(source='user.email', required=False, allow_null=True, allow_blank=True)
    first_name = serializers.CharField(source='user.first_name', required=False, allow_null=True, allow_blank=True)
    last_name = serializers.CharField(source='user.last_name', required=False, allow_null=True, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True, min_length=8)
    profile_img = serializers.SerializerMethodField()

    address = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    r_address = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    r_phone = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    relative = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    phone = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    CNIC = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    designation = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    start_time = serializers.TimeField(required=False, allow_null=True, write_only=True)
    end_time = serializers.TimeField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = UserAccessLevel
        fields = [
            'id', 'user', 'username', 'email', 'first_name', 'last_name', 'password',
            'profile_img', 'role', 'address', 'r_address', 'r_phone', 'relative',
            'phone', 'CNIC', 'designation', 'start_time', 'end_time',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']

    def get_profile_img(self, obj):
        try:
            if hasattr(obj.user, 'profile') and obj.user.profile.profile_img:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.user.profile.profile_img.url)
                return obj.user.profile.profile_img.url
        except (AttributeError, Exception):
            pass

        try:
            if obj.user.employee_profile and obj.user.employee_profile.profile_img:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.user.employee_profile.profile_img.url)
                return obj.user.employee_profile.profile_img.url
        except (AttributeError, Employee.DoesNotExist):
            pass

        return None

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        password = validated_data.pop('password', None)
        
        emp_fields = {}
        for field in ['address', 'r_address', 'r_phone', 'relative', 'phone', 'CNIC', 'designation', 'start_time', 'end_time']:
            if field in validated_data:
                emp_fields[field] = validated_data.pop(field)

        user = instance.user

        if 'username' in user_data:
            new_username = str(user_data['username'] or '').strip()
            if not new_username:
                raise serializers.ValidationError({"username": "Username is required."})
            if User.objects.filter(username=new_username).exclude(pk=user.pk).exists():
                raise serializers.ValidationError({"username": "Username already exists."})
            user.username = new_username

        if 'email' in user_data:
            new_email = str(user_data['email'] or '').strip()
            if new_email and User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
                raise serializers.ValidationError({"email": "Email already exists."})
            user.email = new_email

        if 'first_name' in user_data:
            user.first_name = user_data['first_name'] or ''
        if 'last_name' in user_data:
            user.last_name = user_data['last_name'] or ''
        if password:
            user.set_password(password)
        user.save()

        try:
            if hasattr(user, 'employee_profile') and user.employee_profile:
                emp = user.employee_profile
                for k, v in emp_fields.items():
                    if hasattr(emp, k) and v is not None:
                        setattr(emp, k, v)
                if 'first_name' in user_data or 'last_name' in user_data:
                    full_name = f"{user.first_name} {user.last_name}".strip()
                    if full_name:
                        emp.name = full_name
                emp.save()
        except (AttributeError, Employee.DoesNotExist):
            pass

        return super().update(instance, validated_data)


class CreateAdminManagerSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False, allow_null=True, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_null=True, allow_blank=True)
    role = serializers.ChoiceField(choices=['admin', 'manager'], default='manager')
    profile_img = serializers.ImageField(required=False, allow_null=True)

    def validate_username(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError("Username is required.")
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def validate_email(self, value):
        if not value or not str(value).strip():
            return ""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def create(self, validated_data):
        role = validated_data.pop('role')
        profile_img = validated_data.pop('profile_img', None)
        if 'email' not in validated_data or validated_data['email'] is None:
            validated_data['email'] = ''

        user = User.objects.create_user(**validated_data)
        UserAccessLevel.objects.update_or_create(user=user, defaults={'role': role})

        if profile_img:
            UserProfile.objects.create(user=user, profile_img=profile_img)
        else:
            UserProfile.objects.create(user=user)

        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=False, write_only=True, allow_null=True, allow_blank=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    confirm_password = serializers.CharField(required=False, write_only=True, min_length=8, allow_null=True, allow_blank=True)
    user_id = serializers.IntegerField(required=False, allow_null=True)
    emp_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    username = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def validate(self, data):
        new_pwd = data.get('new_password')
        confirm_pwd = data.get('confirm_password')
        if confirm_pwd and new_pwd != confirm_pwd:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data


class AdminSetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(required=False, write_only=True, min_length=8, allow_null=True, allow_blank=True)
    new_password = serializers.CharField(required=False, write_only=True, min_length=8, allow_null=True, allow_blank=True)
    user_id = serializers.IntegerField(required=False, allow_null=True)
    emp_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    username = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def validate(self, data):
        pwd = data.get('new_password') or data.get('password')
        if not pwd or len(str(pwd)) < 8:
            raise serializers.ValidationError({"password": "Password must be at least 8 characters long."})
        data['resolved_password'] = str(pwd)
        return data


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = '__all__'


class EmployeeShiftHistorySerializer(serializers.ModelSerializer):
    shift_name = serializers.CharField(source='shift.name', read_only=True)
    shift_id = serializers.IntegerField(source='shift.id', read_only=True)

    class Meta:
        model = EmployeeShiftHistory
        fields = [
            'id', 'employee', 'shift', 'shift_id', 'shift_name',
            'from_date', 'to_date', 'salary',
            'shift_start_time', 'shift_end_time'
        ]
        read_only_fields = ['id', 'employee', 'salary', 'shift_start_time', 'shift_end_time']


class EmployeeSerializer(serializers.ModelSerializer):
    total_hours_today = serializers.ReadOnlyField()
    username = serializers.CharField(source='user.username', required=False, allow_null=True, allow_blank=True)
    email = serializers.CharField(source='user.email', required=False, allow_null=True, allow_blank=True)
    profile_img = serializers.ImageField(required=False, allow_null=True)
    designation = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    referance = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    current_shift_detail = ShiftSerializer(source='current_shift', read_only=True)

    class EmpIdOrPkField(serializers.SlugRelatedField):
        def to_internal_value(self, data):
            qs = self.get_queryset()
            if qs is None or data is None:
                return None
            if isinstance(data, int):
                try:
                    return qs.get(pk=data)
                except Exception:
                    raise serializers.ValidationError(f"Employee with pk '{data}' does not exist")

            v = str(data).strip()
            if v == '':
                return None
            try:
                return qs.get(emp_id=v)
            except Exception:
                if v.isdigit():
                    try:
                        return qs.get(pk=int(v))
                    except Exception:
                        pass
                raise serializers.ValidationError(f"Employee with emp_id or pk '{data}' does not exist")

    relatives = EmpIdOrPkField(many=True, slug_field='emp_id', queryset=Employee.objects.all(), required=False)

    class Meta:
        model = Employee
        fields = [
            'id', 'emp_id', 'username', 'email', 'name', 'designation', 'profile_img',
            'salary', 'hourly_rate', 'current_shift', 'current_shift_detail',
            'weekly_off_day',
            'address', 'phone', 'CNIC', 'relative', 'r_phone', 'r_address',
            'status', 'date_joined', 'last_modified', 'total_hours_today', 'referance', 'relatives'
        ]
        read_only_fields = ['emp_id', 'last_modified']

    def create(self, validated_data):
        relatives = validated_data.pop('relatives', [])
        user_data = validated_data.pop('user', {})
        employee = super().create(validated_data)
        if relatives:
            relatives = [r for r in relatives if r is not None]
            for rel in relatives:
                employee.relatives.add(rel)
        return employee

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        if instance.user and user_data:
            user = instance.user
            if 'username' in user_data:
                new_username = str(user_data['username'] or '').strip()
                if not new_username:
                    raise serializers.ValidationError({"username": "Username cannot be empty."})
                if User.objects.filter(username=new_username).exclude(pk=user.pk).exists():
                    raise serializers.ValidationError({"username": "Username already exists."})
                user.username = new_username
            if 'email' in user_data:
                new_email = str(user_data['email'] or '').strip()
                if new_email and User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
                    raise serializers.ValidationError({"email": "Email already exists."})
                user.email = new_email
            user.save()

        relatives = validated_data.pop('relatives', None)
        instance = super().update(instance, validated_data)
        if relatives is not None:
            relatives = [r for r in relatives if r is not None]
            instance.relatives.set(relatives)
        return instance


class AttendanceSerializer(serializers.ModelSerializer):
    total_hours = serializers.SerializerMethodField()
    total_hours_value = serializers.SerializerMethodField()
    is_late = serializers.ReadOnlyField()
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    check_in_time = serializers.TimeField(write_only=True, input_formats=['%I:%M:%S %p', '%I:%M %p', '%H:%M:%S', '%H:%M'])
    check_out_time = serializers.TimeField(write_only=True, input_formats=['%I:%M:%S %p', '%I:%M %p', '%H:%M:%S', '%H:%M'], required=False, allow_null=True)
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
        if obj.check_in:
            return obj.check_in.strftime('%I:%M:%S %p')
        return None

    def get_check_out(self, obj):
        if obj.check_out:
            return obj.check_out.strftime('%I:%M:%S %p')
        return None

    def validate(self, attrs):
        check_in_time = attrs.get('check_in_time')
        check_out_time = attrs.get('check_out_time')

        if check_in_time and check_out_time:
            if check_out_time < check_in_time:
                raise serializers.ValidationError("Check-out cannot be before check-in.")

            temp_date = datetime.now().date()
            temp_check_in = datetime.combine(temp_date, check_in_time)
            temp_check_out = datetime.combine(temp_date, check_out_time)

            duration_hours = (temp_check_out - temp_check_in).total_seconds() / 3600
            max_allowed = 14.0
            employee_val = attrs.get('employee')
            if employee_val:
                if isinstance(employee_val, Employee):
                    emp = employee_val
                    max_allowed = get_overtime_max_allowed(emp, temp_check_in)
                else:
                    try:
                        emp = Employee.objects.get(emp_id=employee_val)
                        max_allowed = get_overtime_max_allowed(emp, temp_check_in)
                    except Employee.DoesNotExist:
                        pass
            if duration_hours > max_allowed:
                raise serializers.ValidationError(
                    f"Work duration cannot exceed {max_allowed:.0f} hours per shift."
                )
        return attrs

    def create(self, validated_data):
        check_in_time = validated_data.pop('check_in_time')
        check_out_time = validated_data.pop('check_out_time', None)
        date = validated_data.get('date')

        check_in = datetime.combine(date, check_in_time)
        check_out = datetime.combine(date, check_out_time) if check_out_time else None

        validated_data['check_in'] = check_in
        validated_data['check_out'] = check_out

        return super().create(validated_data)

    def update(self, instance, validated_data):
        check_in_time = validated_data.pop('check_in_time', None)
        check_out_time = validated_data.pop('check_out_time', None)
        date = validated_data.get('date', instance.date)

        if check_in_time:
            validated_data['check_in'] = datetime.combine(date, check_in_time)
        if check_out_time:
            validated_data['check_out'] = datetime.combine(date, check_out_time)

        return super().update(instance, validated_data)


class PaidLeaveSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    duration_days = serializers.ReadOnlyField()
    employee = serializers.SlugRelatedField(slug_field='emp_id', queryset=Employee.objects.all())

    class Meta:
        model = PaidLeave
        fields = [
            'id', 'employee', 'employee_name', 'leave_type', 'start_time',
            'end_time', 'reason', 'approved', 'approved_by', 'duration_days',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        if attrs['start_time'] >= attrs['end_time']:
            raise serializers.ValidationError("End time must be after start time.")
        return attrs


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = '__all__'


class OvertimeSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    total_hours = serializers.ReadOnlyField()
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True, allow_null=True)
    employee = serializers.SlugRelatedField(slug_field='emp_id', queryset=Employee.objects.all())

    class Meta:
        model = Overtime
        fields = [
            'id', 'employee', 'employee_name', 'date',
            'start_time', 'end_time', 'total_hours',
            'approved_by', 'approved_by_name',
            'status', 'note', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'approved_by', 'status']

    def validate(self, attrs):
        employee = attrs.get('employee')
        date = attrs.get('date')
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')

        if employee and date and start_time and end_time:
            if end_time <= start_time:
                raise serializers.ValidationError("End time must be after start time.")

            is_holiday = Holiday.objects.filter(date=date).exists()
            is_off_day = (employee.weekly_off_day is not None and
                          date.weekday() == employee.weekly_off_day)

            if not is_holiday and not is_off_day:
                s_start, s_end = get_employee_shift_times(employee, date)

                if s_start and s_end:
                    shift_start_dt = datetime.combine(date, s_start)
                    shift_end_dt = datetime.combine(date, s_end)
                    if shift_end_dt <= shift_start_dt:
                        shift_end_dt += timedelta(days=1)

                    ot_start_dt = datetime.combine(date, start_time)
                    ot_end_dt = datetime.combine(date, end_time)
                    if ot_end_dt <= ot_start_dt:
                        ot_end_dt += timedelta(days=1)

                    if ot_start_dt < shift_end_dt and ot_end_dt > shift_start_dt:
                        raise serializers.ValidationError(
                            "Overtime must start after shift end time."
                        )

        return attrs


class SalarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Salary
        fields = ['id', 'employee', 'salary', 'effective_from', 'effective_to', 'created_at']
        read_only_fields = ['id', 'employee', 'effective_to', 'created_at']


class ComprehensiveReportInputSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)
    employee_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )
    format = serializers.ChoiceField(
        choices=[('json', 'json'), ('excel', 'excel')],
        default='json',
        required=False,
    )

    def validate(self, attrs):
        if attrs['start_date'] > attrs['end_date']:
            raise serializers.ValidationError("start_date must be before or equal to end_date")
        if (attrs['end_date'] - attrs['start_date']).days > 90:
            raise serializers.ValidationError("Date range cannot exceed 90 days")
        return attrs


class ActivityLogSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    formatted_created_at = serializers.SerializerMethodField()
    ip_address = serializers.CharField(required=False, allow_null=True, allow_blank=True, read_only=True)

    class Meta:
        model = ActivityLog
        fields = [
            'id', 'actor', 'actor_username', 'actor_name', 'actor_role',
            'action_type', 'action_type_display',
            'category', 'category_display',
            'description',
            'target_model', 'target_id', 'target_name',
            'ip_address', 'user_agent', 'details',
            'created_at', 'formatted_created_at'
        ]
        read_only_fields = [
            'id', 'actor', 'actor_username', 'actor_name', 'actor_role',
            'action_type', 'action_type_display',
            'category', 'category_display',
            'description',
            'target_model', 'target_id', 'target_name',
            'ip_address', 'user_agent', 'details',
            'created_at', 'formatted_created_at'
        ]

    def get_formatted_created_at(self, obj):
        if not obj.created_at:
            return ""
        return obj.created_at.strftime('%Y-%m-%d %I:%M:%S %p')


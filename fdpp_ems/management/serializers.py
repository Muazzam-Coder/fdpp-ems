from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Employee, Attendance, PaidLeave, Shift, UserAccessLevel, EmployeeShiftHistory, Holiday, Overtime, get_overtime_max_allowed
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
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
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
        user_data = {
            'username': validated_data['username'],
            'email': validated_data['email'],
            'password': validated_data['password'],
            'first_name': validated_data.get('first_name', ''),
            'last_name': validated_data.get('last_name', ''),
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


class CreateAdminManagerSerializer(serializers.Serializer):
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

        if profile_img:
            UserProfile.objects.create(user=user, profile_img=profile_img)
        else:
            UserProfile.objects.create(user=user)

        return user


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
    username = serializers.CharField(source='user.username', read_only=True, allow_null=True)
    email = serializers.CharField(source='user.email', read_only=True, allow_null=True)
    profile_img = serializers.ImageField(required=False, allow_null=True)
    designation = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    referance = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    current_shift_detail = ShiftSerializer(source='current_shift', read_only=True)

    class EmpIdOrPkField(serializers.SlugRelatedField):
        def to_internal_value(self, value):
            qs = self.get_queryset()
            if value is None:
                return None
            if isinstance(value, int):
                try:
                    return qs.get(pk=value)
                except Exception:
                    raise serializers.ValidationError(f"Employee with pk '{value}' does not exist")

            v = str(value).strip()
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
                raise serializers.ValidationError(f"Employee with emp_id or pk '{value}' does not exist")

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
        read_only_fields = ['emp_id', 'username', 'email', 'last_modified']

    def create(self, validated_data):
        relatives = validated_data.pop('relatives', [])
        employee = super().create(validated_data)
        if relatives:
            relatives = [r for r in relatives if r is not None]
            for rel in relatives:
                employee.relatives.add(rel)
        return employee

    def update(self, instance, validated_data):
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
        if obj.check_in:
            return obj.check_in.strftime('%H:%M:%S')
        return None

    def get_check_out(self, obj):
        if obj.check_out:
            return obj.check_out.strftime('%H:%M:%S')
        return None

    def validate(self, data):
        check_in_time = data.get('check_in_time')
        check_out_time = data.get('check_out_time')

        if check_in_time and check_out_time:
            if check_out_time < check_in_time:
                raise serializers.ValidationError("Check-out cannot be before check-in.")

            temp_date = datetime.now().date()
            temp_check_in = datetime.combine(temp_date, check_in_time)
            temp_check_out = datetime.combine(temp_date, check_out_time)

            duration_hours = (temp_check_out - temp_check_in).total_seconds() / 3600
            max_allowed = 14.0
            employee_id = data.get('employee')
            if employee_id:
                try:
                    emp = Employee.objects.get(pk=employee_id)
                    max_allowed = get_overtime_max_allowed(emp, temp_check_in)
                except Employee.DoesNotExist:
                    pass
            if duration_hours > max_allowed:
                raise serializers.ValidationError(
                    f"Work duration cannot exceed {max_allowed:.0f} hours per shift."
                )
        return data

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


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = '__all__'


class OvertimeSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    total_hours = serializers.ReadOnlyField()
    approved_by_name = serializers.CharField(source='approved_by.username', read_only=True, allow_null=True)

    class Meta:
        model = Overtime
        fields = [
            'id', 'employee', 'employee_name', 'date',
            'start_time', 'end_time', 'total_hours',
            'approved_by', 'approved_by_name',
            'status', 'note', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'approved_by', 'status']

    def validate(self, data):
        employee = data.get('employee')
        date = data.get('date')
        start_time = data.get('start_time')
        end_time = data.get('end_time')

        if employee and date and start_time and end_time:
            if end_time <= start_time:
                raise serializers.ValidationError("End time must be after start time.")

            is_holiday = Holiday.objects.filter(date=date).exists()
            is_off_day = (employee.weekly_off_day is not None and
                          date.weekday() == employee.weekly_off_day)

            if not is_holiday and not is_off_day:
                from .models import get_employee_shift_times
                s_start, s_end = get_employee_shift_times(employee, date)

                if s_start and s_end:
                    from datetime import timedelta

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

        return data

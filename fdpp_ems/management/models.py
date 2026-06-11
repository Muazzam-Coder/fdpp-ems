from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from datetime import timedelta, datetime, time
from decimal import Decimal

def get_current_date():
    """Get current date for default field value"""
    return timezone.now().date()

WEEKDAY_CHOICES = [
    (0, 'Monday'),
    (1, 'Tuesday'),
    (2, 'Wednesday'),
    (3, 'Thursday'),
    (4, 'Friday'),
    (5, 'Saturday'),
    (6, 'Sunday'),
]

# User Access Level Model
class UserAccessLevel(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='access_level')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='manager')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Access Level'
        verbose_name_plural = 'User Access Levels'

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

# User Profile Model (for admin/manager profile pictures)
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_img = models.ImageField(upload_to='profiles/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"Profile - {self.user.username}"


class Shift(models.Model):
    """Model to manage shift configurations"""
    name = models.CharField(max_length=100, unique=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='employee_profile')

    emp_id = models.IntegerField(unique=True, editable=False, db_index=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    designation = models.CharField(max_length=255, null=True, blank=True)
    profile_img = models.ImageField(upload_to='profiles/', null=True, blank=True)

    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=None)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=None)

    current_shift = models.ForeignKey(
        Shift, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='current_employees'
    )
    weekly_off_day = models.IntegerField(
        null=True, blank=True, choices=WEEKDAY_CHOICES,
        verbose_name="Weekly Off Day"
    )

    address = models.TextField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    CNIC = models.CharField(max_length=20, unique=True, null=True, blank=True)
    relative = models.CharField(max_length=255, null=True, blank=True)
    referance = models.TextField(null=True, blank=True)
    relatives = models.ManyToManyField('self', symmetrical=True, blank=True, related_name='related_to')
    r_phone = models.CharField(max_length=20, null=True, blank=True)
    r_address = models.TextField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=[('active', 'Active'), ('inactive', 'Inactive')],
        default='active',
        null=True,
        blank=True,
    )
    deactivated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='deactivated_employees'
    )
    deactivated_at = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateField(null=True, blank=True, default=None)
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['emp_id']),
            models.Index(fields=['status']),
            models.Index(fields=['date_joined']),
        ]

    def __str__(self):
        return f"{self.name} ({self.emp_id})"

    @property
    def total_hours_today(self):
        today = timezone.now().date()
        today_attendance = self.attendances.filter(date=today)
        return sum(att.total_hours for att in today_attendance)

    def get_shift_for_date(self, target_date):
        """Get the EmployeeShiftHistory entry active on a given date."""
        return EmployeeShiftHistory.objects.filter(
            employee=self,
            from_date__lte=target_date
        ).filter(
            models.Q(to_date__isnull=True) | models.Q(to_date__gte=target_date)
        ).order_by('-from_date').first()

    def get_active_shift_entry(self):
        """Get the currently active EmployeeShiftHistory entry."""
        return EmployeeShiftHistory.objects.filter(
            employee=self,
            to_date__isnull=True
        ).order_by('-from_date').first()


class EmployeeShiftHistory(models.Model):
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name='shift_history'
    )
    shift = models.ForeignKey(
        Shift, on_delete=models.SET_NULL, null=True, related_name='assignment_history'
    )
    from_date = models.DateField()
    to_date = models.DateField(null=True, blank=True)
    salary = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Salary at time of assignment"
    )
    shift_start_time = models.TimeField(null=True, blank=True)
    shift_end_time = models.TimeField(null=True, blank=True)

    class Meta:
        ordering = ['-from_date']
        indexes = [
            models.Index(fields=['employee', 'from_date']),
            models.Index(fields=['employee', 'to_date']),
        ]

    def __str__(self):
        return f"{self.employee.name} - {self.shift.name} ({self.from_date})"

    def save(self, *args, **kwargs):
        if not self.shift_start_time and self.shift:
            self.shift_start_time = self.shift.start_time
        if not self.shift_end_time and self.shift:
            self.shift_end_time = self.shift.end_time
        if not self.salary and self.employee:
            self.salary = self.employee.salary
        super().save(*args, **kwargs)

    def close(self, on_date):
        """Close this shift assignment on the given date."""
        self.to_date = on_date - timedelta(days=1)
        self.save()


class Holiday(models.Model):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=200)
    is_paid = models.BooleanField(default=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"{self.name} ({self.date})"


class Overtime(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name='overtimes'
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    approved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    note = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-start_time']

    def __str__(self):
        return f"OT: {self.employee.name} on {self.date}"

    @property
    def total_hours(self):
        start = datetime.combine(self.date, self.start_time)
        end = datetime.combine(self.date, self.end_time)
        if end <= start:
            end += timedelta(days=1)
        duration = (end - start).total_seconds() / 3600
        return round(min(duration, 14.0), 2)


def get_employee_shift_times(employee, target_date=None):
    """Get shift start/end times for an employee, using EmployeeShiftHistory.
    Returns (start_time, end_time) or (None, None) if no shift found.
    """
    if target_date:
        entry = employee.get_shift_for_date(target_date)
    else:
        entry = employee.get_active_shift_entry()
    if entry and entry.shift:
        return (entry.shift_start_time or entry.shift.start_time,
                entry.shift_end_time or entry.shift.end_time)
    if employee.current_shift:
        return (employee.current_shift.start_time, employee.current_shift.end_time)
    return (None, None)


def get_approved_overtime_for_date(employee, target_date):
    """Returns the first approved Overtime record for an employee on a date, or None."""
    return Overtime.objects.filter(
        employee=employee, date=target_date, status='approved'
    ).first()


def get_overtime_max_allowed(employee, check_in_dt):
    """Calculate overtime-adjusted max hours for an attendance record.
    
    If approved overtime exists for the attendance date, returns the max of
    14 hours and the hours from check_in to overtime end.
    Otherwise returns 14.0.
    """
    target_date = check_in_dt.date()
    ot = get_approved_overtime_for_date(employee, target_date)
    if ot:
        ot_end = datetime.combine(target_date, ot.end_time)
        if ot.end_time <= ot.start_time:
            ot_end += timedelta(days=1)
        ot_allowed = (ot_end - check_in_dt).total_seconds() / 3600
        return max(14.0, ot_allowed)
    return 14.0


def get_approved_overtime_hours_for_date(employee, target_date):
    """Get total overtime hours for an employee on a date (approved only)."""
    ot = get_approved_overtime_for_date(employee, target_date)
    if ot:
        return float(ot.total_hours)
    return 0.0


class InactiveAttendanceAttempt(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='inactive_attempts',
        to_field='emp_id'
    )
    attempted_at = models.DateTimeField(auto_now_add=True)
    attempted_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    method = models.CharField(max_length=50, null=True, blank=True)
    message = models.TextField(null=True, blank=True)

    deactivated_by_username = models.CharField(max_length=150, null=True, blank=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-attempted_at']

    def __str__(self):
        return f"InactiveAttempt: {self.employee.emp_id} at {self.attempted_at}"


@receiver(pre_save, sender=Employee)
def auto_generate_emp_id(sender, instance, **kwargs):
    if not instance.emp_id:
        last_employee = Employee.objects.all().order_by('-emp_id').first()
        if last_employee:
            new_id = last_employee.emp_id + 1
        else:
            new_id = 1
        instance.emp_id = new_id


@receiver(post_save, sender=User)
def create_access_level(sender, instance, created, **kwargs):
    if created:
        UserAccessLevel.objects.get_or_create(user=instance)


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('on_time', 'On Time'),
        ('late', 'Late'),
        ('absent', 'Absent'),
        ('on_leave', 'On Leave'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='attendances',
        to_field='emp_id'
    )
    date = models.DateField(db_index=True)
    check_in = models.DateTimeField()
    check_out = models.DateTimeField(null=True, blank=True)
    message_late = models.TextField(null=True, blank=True, verbose_name="Message (late)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='on_time')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['-date', '-check_in']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Attendance: {self.employee.name} - {self.date}"

    @property
    def total_hours(self):
        if self.check_in and self.check_out:
            duration = self.check_out - self.check_in
            hours = duration.total_seconds() / 3600
            max_allowed = get_overtime_max_allowed(self.employee, self.check_in)
            return round(min(hours, max_allowed), 2)
        return 0

    @property
    def overtime_hours(self):
        return get_approved_overtime_hours_for_date(self.employee, self.date)

    @property
    def is_late(self):
        if not self.check_in:
            return False
        shift_entry = self.employee.get_shift_for_date(self.date)
        if not shift_entry or not shift_entry.shift_start_time:
            return False
        shift_start_time = shift_entry.shift_start_time
        shift_start = datetime.combine(self.date, shift_start_time)
        end_time = shift_entry.shift_end_time
        if end_time and end_time <= shift_start_time and shift_start > self.check_in:
            shift_start = shift_start - timedelta(days=1)
        return self.check_in > shift_start


class PaidLeave(models.Model):
    LEAVE_TYPE_CHOICES = [
        ('sick', 'Sick Leave'),
        ('casual', 'Casual Leave'),
        ('earned', 'Earned Leave'),
        ('unpaid', 'Unpaid Leave'),
        ('maternity', 'Maternity Leave'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='leaves'
    )
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES, default='casual')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    reason = models.TextField(null=True, blank=True)
    approved = models.BooleanField(default=False)
    approved_by = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['employee', 'start_time']),
            models.Index(fields=['approved']),
        ]

    def __str__(self):
        return f"Leave: {self.employee.name} ({self.leave_type}) - {self.start_time.date()}"

    @property
    def duration_days(self):
        delta = self.end_time.date() - self.start_time.date()
        return delta.days + 1

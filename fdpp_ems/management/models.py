from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils import timezone
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from datetime import timedelta, datetime, time
from decimal import Decimal

def get_current_date():
    """Get current date for default field value"""
    return timezone.now().date()

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

class Employee(models.Model):
    # Link to user authentication (optional)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='employee_profile')
    
    # Simple integer emp_id (1, 2, 3, etc.)
    emp_id = models.IntegerField(unique=True, editable=False, db_index=True)
    name = models.CharField(max_length=255)
    profile_img = models.ImageField(upload_to='profiles/', null=True, blank=True)
    
    # Financial fields for payout calculations
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    
    shift_type = models.CharField(max_length=100, default='morning')  # Allows custom shifts like "new" 
    start_time = models.TimeField() 
    end_time = models.TimeField()   
    address = models.TextField()
    phone = models.CharField(max_length=20)
    CNIC = models.CharField(max_length=20, unique=True)
    relative = models.CharField(max_length=255)
    r_phone = models.CharField(max_length=20)
    r_address = models.TextField()
    
    # Additional fields - date_joined is now editable
    status = models.CharField(
        max_length=20,
        choices=[('active', 'Active'), ('inactive', 'Inactive')],
        default='active'
    )
    date_joined = models.DateField(default=get_current_date)
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
        """Get total hours checked out today"""
        from django.utils import timezone
        today = timezone.now().date()
        today_attendance = self.attendances.filter(date=today)
        return sum(att.total_hours for att in today_attendance)


@receiver(pre_save, sender=Employee)
def auto_generate_emp_id(sender, instance, **kwargs):
    """Auto-generate emp_id as simple integers: 1, 2, 3, etc."""
    if not instance.emp_id:
        last_employee = Employee.objects.all().order_by('-emp_id').first()
        if last_employee:
            new_id = last_employee.emp_id + 1
        else:
            new_id = 1
        instance.emp_id = new_id


@receiver(post_save, sender=User)
def create_access_level(sender, instance, created, **kwargs):
    """Create UserAccessLevel for new users"""
    if created:
        UserAccessLevel.objects.get_or_create(user=instance)

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('on_time', 'On Time'),
        ('late', 'Late'),
        ('absent', 'Absent'),
        ('on_leave', 'On Leave'),
    ]

    # This automatically uses emp_id as the Foreign Key
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
        # Removed unique_together to allow multiple scans per day
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Attendance: {self.employee.name} - {self.date}"

    @property
    def total_hours(self):
        """Logic for the 14-hour limit constraint"""
        if self.check_in and self.check_out:
            duration = self.check_out - self.check_in
            hours = duration.total_seconds() / 3600
            # Returns hours worked, but maxes out at 14 per the constraint
            return round(min(hours, 14.0), 2)
        return 0
    
    @property
    def overtime_hours(self):
        """Calculate overtime if any - REMOVED"""
        return 0.0
    
    @property
    def is_late(self):
        """Check if employee was late"""
        if self.check_in:
            shift_start = timezone.make_aware(datetime.combine(self.date, self.employee.start_time))
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
        """Calculate leave duration in days"""
        delta = self.end_time.date() - self.start_time.date()
        return delta.days + 1

class Shift(models.Model):
    """Model to manage shift configurations"""
    name = models.CharField(max_length=100, unique=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"
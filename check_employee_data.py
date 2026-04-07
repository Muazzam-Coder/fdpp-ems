import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fdpp_ems.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from management.models import Employee, User, Attendance
from django.utils import timezone

print("="*70)
print("Employee Data Check")
print("="*70)

try:
    emp = Employee.objects.get(emp_id=1)
    print(f"\nEmployee found: {emp.name} (ID: {emp.emp_id})")
    print(f"  User linked: {emp.user}")
    
    if emp.user:
        print(f"  Username: {emp.user.username}")
        print(f"  First Name: '{emp.user.first_name}'")
        print(f"  Last Name: '{emp.user.last_name}'")
    else:
        print("  ✗ No user linked")
    
    # Check today's attendance
    today = timezone.now().date()
    today_attendance = Attendance.objects.filter(
        employee=emp,
        date=today
    ).order_by('-check_in')
    
    print(f"\nToday's Attendance ({today}):")
    if today_attendance.exists():
        for att in today_attendance:
            print(f"  Check-in: {att.check_in}")
            print(f"  Check-out: {att.check_out}")
            print(f"  Status: {att.status}")
    else:
        print("  ✗ No attendance records for today")
    
except Employee.DoesNotExist:
    print("✗ Employee with ID 1 not found")

print("\n" + "="*70)
print("All Employees Summary")
print("="*70)
for emp in Employee.objects.all():
    user_info = f"User: {emp.user.username} ({emp.user.first_name} {emp.user.last_name})" if emp.user else "No User"
    print(f"  ID: {emp.emp_id}, Name: {emp.name}, {user_info}")

#!/usr/bin/env python
"""
FDPP-EMS Seed/Feed Data Script
Creates dummy data for testing and development
Run: python seed_data.py
"""

import os
import sys
import django
from datetime import datetime, timedelta, time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fdpp_ems.settings')
django.setup()

from management.models import Employee, Attendance, PaidLeave, Shift
from django.utils import timezone

# Color codes for terminal output
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def create_shifts():
    """Create sample shifts"""
    print(f"\n{BLUE}{'='*60}")
    print("Creating Shifts...")
    print(f"{'='*60}{RESET}")
    
    shifts_data = [
        {
            'name': 'Morning Shift',
            'start_time': time(6, 0),
            'end_time': time(14, 0),
            'description': 'Early morning shift (6 AM - 2 PM)'
        },
        {
            'name': 'Afternoon Shift',
            'start_time': time(14, 0),
            'end_time': time(22, 0),
            'description': 'Afternoon shift (2 PM - 10 PM)'
        },
        {
            'name': 'Night Shift',
            'start_time': time(22, 0),
            'end_time': time(6, 0),
            'description': 'Night shift (10 PM - 6 AM)'
        },
    ]
    
    for shift_data in shifts_data:
        shift, created = Shift.objects.get_or_create(
            name=shift_data['name'],
            defaults={
                'start_time': shift_data['start_time'],
                'end_time': shift_data['end_time'],
                'description': shift_data['description']
            }
        )
        if created:
            print_success(f"Created: {shift.name}")
        else:
            print_info(f"Already exists: {shift.name}")

def create_employees():
    """Create sample employees"""
    print(f"\n{BLUE}{'='*60}")
    print("Creating Employees...")
    print(f"{'='*60}{RESET}")
    
    employees_data = [
        {
            'emp_id': '0001',
            'name': 'Muazzam Ali',
            'salary': 75000,
            'hourly_rate': 468.75,
            'shift_type': 'morning',
            'start_time': time(6, 0),
            'end_time': time(14, 0),
            'address': '123 Main Street, Lahore',
            'phone': '03001234567',
            'CNIC': '12345-1234567-1',
            'relative': 'Fatima Ali',
            'r_phone': '03009876543',
            'r_address': 'Relative Address, Lahore',
            'status': 'active'
        },
        {
            'emp_id': '0002',
            'name': 'Ayesha Khan',
            'salary': 65000,
            'hourly_rate': 406.25,
            'shift_type': 'afternoon',
            'start_time': time(14, 0),
            'end_time': time(22, 0),
            'address': '456 Park Road, Islamabad',
            'phone': '03005555555',
            'CNIC': '54321-7654321-2',
            'relative': 'Ahmed Khan',
            'r_phone': '03008888888',
            'r_address': 'Family Address, Islamabad',
            'status': 'active'
        },
        {
            'emp_id': '0003',
            'name': 'Hassan Malik',
            'salary': 55000,
            'hourly_rate': 343.75,
            'shift_type': 'night',
            'start_time': time(22, 0),
            'end_time': time(6, 0),
            'address': '789 City Center, Karachi',
            'phone': '03003333333',
            'CNIC': '11111-1111111-3',
            'relative': 'Zainab Malik',
            'r_phone': '03004444444',
            'r_address': 'Contact Address, Karachi',
            'status': 'active'
        },
        {
            'emp_id': '0004',
            'name': 'Saira Ahmed',
            'salary': 70000,
            'hourly_rate': 437.50,
            'shift_type': 'morning',
            'start_time': time(6, 0),
            'end_time': time(14, 0),
            'address': '321 Trade Center, Faisalabad',
            'phone': '03006666666',
            'CNIC': '99999-9999999-4',
            'relative': 'Mohammad Ahmed',
            'r_phone': '03007777777',
            'r_address': 'Home Address, Faisalabad',
            'status': 'active'
        },
        {
            'emp_id': '0005',
            'name': 'Ali Raza',
            'salary': 60000,
            'hourly_rate': 375.00,
            'shift_type': 'afternoon',
            'start_time': time(14, 0),
            'end_time': time(22, 0),
            'address': '654 Business Park, Rawalpindi',
            'phone': '03002222222',
            'CNIC': '88888-8888888-5',
            'relative': 'Noor Raza',
            'r_phone': '03001111111',
            'r_address': 'Emergency Contact, Rawalpindi',
            'status': 'active'
        },
    ]
    
    for emp_data in employees_data:
        employee, created = Employee.objects.get_or_create(
            emp_id=emp_data['emp_id'],
            defaults={k: v for k, v in emp_data.items() if k != 'emp_id'}
        )
        if created:
            print_success(f"Created: {employee.name} ({employee.emp_id})")
        else:
            print_info(f"Already exists: {employee.name} ({employee.emp_id})")

def create_attendance():
    """Create sample attendance records for the last 7 days"""
    print(f"\n{BLUE}{'='*60}")
    print("Creating Attendance Records...")
    print(f"{'='*60}{RESET}")
    
    employees = Employee.objects.all()
    today = timezone.now().date()
    
    for i in range(7):  # Last 7 days
        check_date = today - timedelta(days=i)
        
        for employee in employees:
            # Random check times
            check_in_hour = 6 + (i % 2)  # 6 or 7 AM
            check_in_minute = (i * 10) % 60
            check_out_hour = 14 + (i % 2)  # 2 or 3 PM
            check_out_minute = (i * 15) % 60
            
            check_in = timezone.make_aware(
                datetime.combine(check_date, time(check_in_hour, check_in_minute))
            )
            check_out = timezone.make_aware(
                datetime.combine(check_date, time(check_out_hour, check_out_minute))
            )
            
            # Determine if late
            is_late = check_in.time() > employee.start_time
            status = 'late' if is_late else 'on_time'
            
            attendance, created = Attendance.objects.get_or_create(
                employee=employee,
                date=check_date,
                defaults={
                    'check_in': check_in,
                    'check_out': check_out,
                    'status': status,
                    'message_late': 'Traffic jam' if is_late else None
                }
            )
            
            if created:
                hours = (check_out - check_in).total_seconds() / 3600
                print_success(f"{employee.name} - {check_date} - {hours:.1f}h ({status})")
            else:
                print_info(f"Already exists: {employee.name} - {check_date}")

def create_leave():
    """Create sample leave records"""
    print(f"\n{BLUE}{'='*60}")
    print("Creating Leave Records...")
    print(f"{'='*60}{RESET}")
    
    employees = Employee.objects.all()[:3]  # First 3 employees
    today = timezone.now()
    
    leave_types = ['sick', 'casual', 'earned']
    
    for idx, employee in enumerate(employees):
        leave_type = leave_types[idx % len(leave_types)]
        start = today + timedelta(days=10)
        end = start + timedelta(days=2)
        
        leave, created = PaidLeave.objects.get_or_create(
            employee=employee,
            start_time=start,
            defaults={
                'leave_type': leave_type,
                'end_time': end,
                'reason': f'Personal {leave_type} leave',
                'approved': idx % 2 == 0  # Alternate approved/pending
            }
        )
        
        if created:
            status = "✓ Approved" if leave.approved else "⏳ Pending"
            print_success(f"{employee.name} - {leave_type} leave ({status})")
        else:
            print_info(f"Already exists: {employee.name} leave request")

def create_bulk_attendance():
    """Create more attendance data for detailed reporting"""
    print(f"\n{BLUE}{'='*60}")
    print("Creating Bulk Attendance Data...")
    print(f"{'='*60}{RESET}")
    
    employees = Employee.objects.all()
    today = timezone.now().date()
    
    # Create data for the last 30 days
    for day_offset in range(30):
        check_date = today - timedelta(days=day_offset)
        
        for employee in employees:
            # Skip weekends (5 = Saturday, 6 = Sunday)
            if check_date.weekday() >= 5:
                continue
            
            # Check if already exists
            if Attendance.objects.filter(employee=employee, date=check_date).exists():
                continue
            
            # Random variation in check times
            variation = (day_offset * hash(employee.emp_id)) % 60
            check_in_hour = 6 + (variation % 3)
            check_in_minute = variation % 60
            check_out_hour = 14 + (variation % 2)
            check_out_minute = (variation * 2) % 60
            
            check_in = timezone.make_aware(
                datetime.combine(check_date, time(check_in_hour, check_in_minute))
            )
            check_out = timezone.make_aware(
                datetime.combine(check_date, time(check_out_hour, check_out_minute))
            )
            
            is_late = check_in.time() > employee.start_time
            
            Attendance.objects.create(
                employee=employee,
                date=check_date,
                check_in=check_in,
                check_out=check_out,
                status='late' if is_late else 'on_time',
                message_late='Traffic' if is_late else None
            )

def delete_all_data():
    """Delete all data (for fresh start)"""
    print(f"\n{YELLOW}{'='*60}")
    print("Deleting All Existing Data...")
    print(f"{'='*60}{RESET}")
    
    Attendance.objects.all().delete()
    print_warning("Deleted all attendance records")
    
    PaidLeave.objects.all().delete()
    print_warning("Deleted all leave records")
    
    Employee.objects.all().delete()
    print_warning("Deleted all employees")
    
    Shift.objects.all().delete()
    print_warning("Deleted all shifts")

def display_summary():
    """Display summary of created data"""
    print(f"\n{BLUE}{'='*60}")
    print("SEED DATA SUMMARY")
    print(f"{'='*60}{RESET}")
    
    total_employees = Employee.objects.count()
    total_attendance = Attendance.objects.count()
    total_leaves = PaidLeave.objects.count()
    total_shifts = Shift.objects.count()
    
    print_success(f"Total Employees: {total_employees}")
    print_success(f"Total Attendance Records: {total_attendance}")
    print_success(f"Total Leave Requests: {total_leaves}")
    print_success(f"Total Shifts: {total_shifts}")
    
    if total_employees > 0:
        avg_attendance = total_attendance // total_employees if total_employees > 0 else 0
        print_info(f"Average Attendance Records per Employee: {avg_attendance}")
    
    print(f"\n{BLUE}API ENDPOINTS TO TEST:{RESET}")
    print_info("GET /api/employees/ - List all employees")
    print_info("GET /api/attendance/ - List attendance records")
    print_info("GET /api/attendance/daily_report/ - Today's report")
    print_info("GET /api/attendance/weekly_report/ - Weekly report")
    print_info("GET /api/attendance/monthly_report/ - Monthly report")
    print_info("GET /api/leave/ - List leave requests")
    print_info("GET /api/shifts/ - List shifts")
    
    print(f"\n{GREEN}{'='*60}")
    print("✅ SEED DATA CREATION COMPLETE!")
    print(f"{'='*60}{RESET}")

def main():
    """Main execution"""
    print(f"\n{BLUE}{'='*60}")
    print("FDPP-EMS DATABASE SEEDER")
    print(f"{'='*60}{RESET}\n")
    
    try:
        # Ask user if they want to delete existing data
        response = input("Delete existing data and start fresh? (y/n): ").lower().strip()
        if response == 'y':
            delete_all_data()
        
        # Create data
        create_shifts()
        create_employees()
        create_attendance()
        create_leave()
        create_bulk_attendance()
        
        # Display summary
        display_summary()
        
    except Exception as e:
        print_error(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

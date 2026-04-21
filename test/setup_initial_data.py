#!/usr/bin/env python
"""
FDPP-EMS Initial Setup Script
Creates sample shifts and demonstrates API usage
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fdpp_ems.settings')
django.setup()

from management.models import Shift, Employee
from datetime import time

def create_sample_shifts():
    """Create sample shifts"""
    print("Creating sample shifts...")
    
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
            print(f"✅ Created: {shift.name}")
        else:
            print(f"ℹ️  Already exists: {shift.name}")
    
    print(f"\n✅ Total shifts: {Shift.objects.count()}")

def create_sample_employee():
    """Create a sample employee for testing"""
    print("\nCreating sample employee...")
    
    employee_data = {
        'emp_id': 'DEMO001',
        'name': 'Muhammad Ali',
        'salary': 50000,
        'hourly_rate': 312.50,
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
    }
    
    employee, created = Employee.objects.get_or_create(
        emp_id=employee_data['emp_id'],
        defaults={k: v for k, v in employee_data.items() if k != 'emp_id'}
    )
    
    if created:
        print(f"✅ Created: {employee.name} ({employee.emp_id})")
    else:
        print(f"ℹ️  Already exists: {employee.name} ({employee.emp_id})")
    
    print(f"\n✅ Total employees: {Employee.objects.count()}")

def display_api_endpoints():
    """Display important API endpoints"""
    print("\n" + "="*60)
    print("FDPP-EMS API Endpoints")
    print("="*60)
    
    endpoints = [
        ("GET", "/api/employees/", "List all employees"),
        ("POST", "/api/employees/", "Create new employee"),
        ("POST", "/api/attendance/check_in/", "Check-in employee"),
        ("POST", "/api/attendance/check_out/", "Check-out employee"),
        ("GET", "/api/attendance/daily_report/", "Daily attendance report"),
        ("GET", "/api/attendance/weekly_report/", "Weekly report"),
        ("GET", "/api/attendance/monthly_report/", "Monthly report"),
        ("POST", "/api/leave/", "Create leave request"),
        ("GET", "/api/leave/pending_approvals/", "Pending leave requests"),
        ("GET", "/api/shifts/", "List all shifts"),
    ]
    
    print(f"\n{'METHOD':<6} {'ENDPOINT':<40} {'DESCRIPTION':<30}")
    print("-" * 76)
    for method, endpoint, description in endpoints:
        print(f"{method:<6} {endpoint:<40} {description:<30}")
    
    print("\n" + "="*60)

def display_quick_commands():
    """Display quick command examples"""
    print("\n" + "="*60)
    print("Quick Command Examples")
    print("="*60)
    
    commands = [
        ("Check-In", "curl -X POST http://localhost:8000/api/attendance/check_in/ -H 'Content-Type: application/json' -d '{\"emp_id\": \"DEMO001\"}'"),
        ("Check-Out", "curl -X POST http://localhost:8000/api/attendance/check_out/ -H 'Content-Type: application/json' -d '{\"emp_id\": \"DEMO001\"}'"),
        ("Daily Report", "curl http://localhost:8000/api/attendance/daily_report/"),
        ("Get Stats", "curl http://localhost:8000/api/employees/employee_stats/"),
    ]
    
    for label, cmd in commands:
        print(f"\n{label}:")
        print(f"  {cmd}")
    
    print("\n" + "="*60)

def main():
    """Main setup function"""
    print("\n" + "="*60)
    print("FDPP-EMS Initial Setup")
    print("="*60)
    
    try:
        # Create shifts
        create_sample_shifts()
        
        # Create sample employee
        create_sample_employee()
        
        # Display endpoints and commands
        display_api_endpoints()
        display_quick_commands()
        
        print("\n✅ Setup Complete!")
        print("\nNext Steps:")
        print("1. Start the server: python manage.py runserver")
        print("2. Visit: http://localhost:8000/api/")
        print("3. Try the endpoints above")
        print("4. Check API_DOCUMENTATION.md for more details")
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()

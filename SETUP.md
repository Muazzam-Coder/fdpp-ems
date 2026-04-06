# FDPP Employee Management System - Setup Guide

## System Overview

This is a complete Django-based Employee Management System (EMS) with the following capabilities:
- **Employee Management**: Track employee information, shifts, and profiles
- **Attendance Tracking**: Check-in/check-out system with automatic late detection
- **Leave Management**: Multiple leave types with approval workflow
- **Payroll System**: Hourly calculations with overtime compensation
- **Reporting**: Daily, weekly, and monthly attendance reports
- **14-Hour Limit**: Enforced work hour limit per day

---

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)

---

## Step-by-Step Installation

### 1. Navigate to Project Directory
```bash
cd "d:\FDPP attendence\fdpp_ems"
```

### 2. Activate Virtual Environment
If you haven't created a virtual environment yet:
```bash
python -m venv venv
```

Activate it:
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Required Packages
```bash
pip install django==6.0.3
pip install djangorestframework==3.14.0
pip install django-filter==23.5
pip install pillow==10.1.0
pip install python-dateutil==2.8.2
```

Or install all at once:
```bash
pip install django==6.0.3 djangorestframework==3.14.0 django-filter==23.5 pillow==10.1.0
```

### 4. Create Database Migrations

First, create the migrations based on model changes:
```bash
python manage.py makemigrations management
```

Then apply all migrations:
```bash
python manage.py migrate
```

### 5. Create Superuser (Admin Account)
```bash
python manage.py createsuperuser
```

Enter credentials:
- Username: admin
- Email: admin@example.com
- Password: (choose a secure password)

### 6. Create Sample Shifts (Optional)
Create a Python script called `create_shifts.py` in the project root:

```python
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fdpp_ems.settings')

import django
django.setup()

from management.models import Shift
from datetime import time

shifts = [
    {'name': 'Morning Shift', 'start_time': time(6, 0), 'end_time': time(14, 0), 'description': 'Early morning shift (6 AM - 2 PM)'},
    {'name': 'Afternoon Shift', 'start_time': time(14, 0), 'end_time': time(22, 0), 'description': 'Afternoon shift (2 PM - 10 PM)'},
    {'name': 'Night Shift', 'start_time': time(22, 0), 'end_time': time(6, 0), 'description': 'Night shift (10 PM - 6 AM)'},
]

for shift_data in shifts:
    shift, created = Shift.objects.get_or_create(**shift_data)
    if created:
        print(f"Created: {shift.name}")
    else:
        print(f"Already exists: {shift.name}")

print("Shift creation complete!")
```

Run it:
```bash
python create_shifts.py
```

### 7. Run Development Server
```bash
python manage.py runserver
```

You should see:
```
Starting development server at http://127.0.0.1:8000/
```

---

## Accessing the System

### Admin Panel
- **URL**: http://localhost:8000/admin/
- **Login**: Use superuser credentials created in Step 5
- **Features**:
  - Manage all employees
  - View and update attendance records
  - Approve/reject leave requests
  - Configure shifts

### API Root
- **URL**: http://localhost:8000/api/
- **Features**:
  - Interactive API documentation
  - All REST endpoints available
  - Browse and test endpoints directly

### Employee Management
- **URL**: http://localhost:8000/api/employees/
- **Features**:
  - Create, read, update, delete employees
  - View employee statistics
  - Calculate payouts

### Attendance Management
- **URL**: http://localhost:8000/api/attendance/
- **Features**:
  - Check-in/check-out
  - Daily, weekly, monthly reports
  - View attendance details

### Leave Management
- **URL**: http://localhost:8000/api/leave/
- **Features**:
  - Create leave requests
  - View pending approvals
  - Approve/reject leaves

---

## Quick Start Examples

### 1. Create an Employee
```bash
curl -X POST http://localhost:8000/api/employees/ \
  -H "Content-Type: application/json" \
  -d '{
    "emp_id": "EMP001",
    "name": "John Doe",
    "salary": 50000,
    "hourly_rate": 312.50,
    "shift_type": "morning",
    "start_time": "06:00:00",
    "end_time": "14:00:00",
    "address": "123 Main St",
    "phone": "03001234567",
    "CNIC": "12345-1234567-1",
    "relative": "Jane Doe",
    "r_phone": "03009876543",
    "r_address": "456 Side St"
  }'
```

### 2. Check-In Employee
```bash
curl -X POST http://localhost:8000/api/attendance/check_in/ \
  -H "Content-Type: application/json" \
  -d '{"emp_id": "EMP001"}'
```

### 3. Check-Out Employee
```bash
curl -X POST http://localhost:8000/api/attendance/check_out/ \
  -H "Content-Type: application/json" \
  -d '{"emp_id": "EMP001"}'
```

### 4. Get Monthly Attendance Report
```bash
curl http://localhost:8000/api/attendance/monthly_report/?month=1&year=2024
```

### 5. Calculate Payout
```bash
curl "http://localhost:8000/api/employees/EMP001/calculate_payout/?start_date=2024-01-01&end_date=2024-01-31"
```

---

## Database Schema

### Employee Table
```
emp_id (PK)
├── name
├── profile_img
├── salary
├── hourly_rate
├── shift_type
├── start_time
├── end_time
├── address
├── phone
├── CNIC
├── relative
├── r_phone
├── r_address
├── status (active/inactive)
├── date_joined
└── last_modified
```

### Attendance Table
```
id (PK)
├── employee (FK -> Employee.emp_id)
├── date
├── check_in
├── check_out
├── message_late
├── status (on_time/late/absent/on_leave)
├── created_at
└── updated_at

Calculated Fields:
├── total_hours (max 14)
├── overtime_hours
└── is_late
```

### PaidLeave Table
```
id (PK)
├── employee (FK -> Employee)
├── leave_type (sick/casual/earned/unpaid/maternity)
├── start_time
├── end_time
├── reason
├── approved
├── approved_by
├── created_at
└── updated_at

Calculated Fields:
└── duration_days
```

### Shift Table
```
id (PK)
├── name
├── start_time
├── end_time
├── description
└── created_at
```

---

## Configuration

### Settings.py Important Settings

#### REST Framework Configuration
```python
REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}
```

#### Database
Currently using SQLite3 (default). For production, use PostgreSQL or MySQL.

#### Time Zone
Currently set to UTC. Change in settings.py:
```python
TIME_ZONE = 'Asia/Karachi'  # For Pakistan time
```

---

## File Structure

```
fdpp_ems/
├── manage.py
├── db.sqlite3
├── venv/
├── fdpp_ems/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── management/
│   ├── migrations/
│   │   ├── __init__.py
│   │   └── 0001_initial.py
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── tests.py
├── API_DOCUMENTATION.md
└── SETUP.md
```

---

## Common Issues & Solutions

### Issue 1: Port Already in Use
**Error**: `Address already in use`
**Solution**: 
```bash
python manage.py runserver 8001  # Use different port
```

### Issue 2: Module Not Found
**Error**: `ModuleNotFoundError: No module named 'rest_framework'`
**Solution**: 
```bash
pip install djangorestframework django-filter
```

### Issue 3: Database Migration Issues
**Error**: `No changes detected in app`
**Solution**:
```bash
python manage.py migrate management --run-syncdb
```

### Issue 4: Image Upload Failures
**Error**: `Image field validation error`
**Solution**: Install Pillow
```bash
pip install pillow
```

### Issue 5: Check-in Already Exists
**Error**: `Already checked in today`
**Solution**: Delete the attendance record or wait until midnight

---

## Features Deep Dive

### 1. Attendance Check-In/Check-Out System

**Check-In Flow:**
1. Employee ID is submitted
2. System checks if employee exists
3. System checks if already checked in today
4. Creates attendance record with current timestamp
5. Automatically detects if late (compares with shift start time)

**Check-Out Flow:**
1. Employee ID is submitted
2. System finds today's check-in record
3. Validates check-out time is after check-in
4. Validates total hours don't exceed 14 hours
5. Updates attendance with check-out time

### 2. 14-Hour Limit Enforcement

- **Applied at**: Check-out validation
- **Logic**: `check_out - check_in > 14 hours` raises error
- **Overtime Calculation**: Hours beyond 8 hours × 1.5
- **Example**:
  - Check-in: 6:00 AM
  - Check-out: 4:00 PM (10 hours)
  - Regular hours: 8
  - Overtime hours: 2 (paid at 1.5x rate)

### 3. Filtering System

**Attendance Filtering:**
- By employee ID
- By date range
- By status (on_time, late, absent, on_leave)
- Combination of above

**Employee Filtering:**
- By status (active, inactive)
- By shift type

### 4. Reporting System

**Daily Report:**
- Presence/absence count
- Late arrivals
- Detailed attendance records

**Weekly Report:**
- Total working days
- Total hours worked
- Late arrivals count
- Average hours per day

**Monthly Report:**
- Total working days
- Total hours by all employees
- Unique employee count
- Late arrivals trend

### 5. Payroll Calculation

**Formula:**
```
Base Pay = Total Hours × Hourly Rate
Overtime Pay = Overtime Hours × Hourly Rate × 1.5
Total Payout = Base Pay + Overtime Pay
```

**Example:**
- Hourly Rate: 312.50
- Regular Hours: 160 (20 days × 8 hours)
- Overtime Hours: 20
- Base Pay: 160 × 312.50 = 50,000
- Overtime Pay: 20 × 312.50 × 1.5 = 9,375
- **Total Payout: 59,375**

---

## Performance Optimization

### Database Indexes
Already configured on:
- Employee: emp_id, status, date_joined
- Attendance: employee + date, date, status
- PaidLeave: employee + start_time, approved

### Pagination
- Default: 20 records per page
- Adjustable via API query parameters

### Filtering
- Use efficient Django ORM queries
- Indexed fields for fast lookup

---

## Security Considerations

### Current Settings (Development)
- `DEBUG = True` (change to False in production)
- `ALLOWED_HOSTS = []` (configure for production)
- `SECRET_KEY` exposed (use environment variables)

### Production Checklist
1. Set `DEBUG = False`
2. Configure `ALLOWED_HOSTS`
3. Use environment variables for secrets
4. Enable HTTPS
5. Use PostgreSQL or MySQL
6. Set up proper authentication
7. Enable CSRF protection
8. Configure CORS if needed

---

## Backup & Restore

### Backup Database
```bash
# SQLite
cp db.sqlite3 db.sqlite3.backup

# Or dump data
python manage.py dumpdata > backup.json
```

### Restore Database
```bash
# From JSON dump
python manage.py loaddata backup.json
```

---

## Testing

Run tests:
```bash
python manage.py test management
```

---

## Support & Documentation

- **API Documentation**: See API_DOCUMENTATION.md
- **Django Docs**: https://docs.djangoproject.com/
- **Django REST Framework**: https://www.django-rest-framework.org/
- **Django Filter**: https://django-filter.readthedocs.io/

---

## Version History

**v1.0** (Initial Release)
- Employee management
- Attendance tracking
- Leave management
- Payroll system
- Reporting features

---

**Last Updated**: 2024  
**Framework**: Django 6.0.3 + Django REST Framework 3.14  
**License**: Open Source

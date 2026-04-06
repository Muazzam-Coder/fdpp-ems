# 🌱 Database Seeding Guide

This guide explains how to populate your database with dummy data for testing and development.

---

## 📋 Available Seed Files

### 1. **seed_data.py** (RECOMMENDED - Most Feature-Rich)
- Creates 5-10 employees
- Creates 3 shifts (Morning, Afternoon, Night)
- Creates 30 days of attendance data
- Creates sample leave requests
- Colored output for easy viewing
- Allows you to delete existing data first
- Displays summary statistics

### 2. **employees_data.csv**
- 10 sample employees in CSV format
- Can be imported into Excel or similar tools
- Manual import into database

### 3. **initial_data.json**
- Django fixture format
- Can be loaded with `python manage.py loaddata`
- Contains basic shifts and employees

### 4. **setup_initial_data.py**
- Creates sample shifts and one demo employee
- Displays API endpoints
- Good for quick setup

---

## 🚀 Method 1: Using seed_data.py (BEST)

### Step 1: Make sure you're in the right directory
```bash
cd d:\FDPP attendence
```

### Step 2: Run the seed script
```bash
python seed_data.py
```

### Step 3: The script will ask:
```
Delete existing data and start fresh? (y/n):
```

- Type **y** to delete and start fresh
- Type **n** to keep existing data and add new records

### Step 4: Watch the colored output
```
✅ Created: Morning Shift
✅ Created: Muazzam Ali (EMP001)
✅ Created: Ayesha Khan - 2024-01-15 - 8.0h (on_time)
... (many more records)

SEED DATA SUMMARY
✅ Total Employees: 10
✅ Total Attendance Records: 150
✅ Total Leave Requests: 3
✅ Total Shifts: 3
```

### Step 5: Start testing!
```bash
python manage.py runserver
```

Visit: http://localhost:8000/api/employees/

---

## 📥 Method 2: Using JSON Fixture (Django Way)

### Step 1: Load the fixture
```bash
python manage.py loaddata initial_data
```

### Step 2: Verify it loaded
```bash
python manage.py shell
from management.models import Employee
print(Employee.objects.count())  # Should show 5
```

---

## 📊 Method 3: Using CSV File

### Step 1: Open employees_data.csv

You can:
- Open in Excel
- Edit/modify as needed
- Save with your changes

### Step 2: Create a custom import script
Create a file called `import_csv.py`:

```python
import os
import sys
import django
import csv
from datetime import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fdpp_ems.settings')
django.setup()

from management.models import Employee

with open('employees_data.csv', 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        Employee.objects.get_or_create(
            emp_id=row['emp_id'],
            defaults={
                'name': row['name'],
                'salary': row['salary'],
                'hourly_rate': row['hourly_rate'],
                'shift_type': row['shift_type'],
                'start_time': row['start_time'],
                'end_time': row['end_time'],
                'address': row['address'],
                'phone': row['phone'],
                'CNIC': row['CNIC'],
                'relative': row['relative'],
                'r_phone': row['r_phone'],
                'r_address': row['r_address'],
                'status': row['status']
            }
        )

print("✅ Employees imported from CSV!")
```

### Step 3: Run the import
```bash
python import_csv.py
```

---

## 🧑‍💼 Data Generated

### Employees
- **EMP001**: Muazzam Ali (Morning Shift)
- **EMP002**: Ayesha Khan (Afternoon Shift)
- **EMP003**: Hassan Malik (Night Shift)
- **EMP004**: Saira Ahmed (Morning Shift)
- **EMP005**: Ali Raza (Afternoon Shift)
- **EMP006-EMP010**: Additional employees across shifts

### Shifts
- **Morning Shift**: 6 AM - 2 PM
- **Afternoon Shift**: 2 PM - 10 PM
- **Night Shift**: 10 PM - 6 AM

### Attendance Data
- 30 days of historical data
- All working days (weekends excluded)
- Mix of on-time and late arrivals
- Includes messages for late arrivals

### Leave Data
- Sample leave requests
- Mix of approved and pending
- Different leave types (sick, casual, earned)

---

## 🔧 Customizing the Seeds

### To add more employees to seed_data.py:

1. Open `seed_data.py`
2. Find the `create_employees()` function
3. Add new employee dict:

```python
{
    'emp_id': 'EMP011',
    'name': 'Your Name',
    'salary': 80000,
    'hourly_rate': 500,
    'shift_type': 'morning',
    'start_time': time(6, 0),
    'end_time': time(14, 0),
    'address': 'Your Address',
    'phone': '03001111111',
    'CNIC': '11111-1111111-11',
    'relative': 'Relative Name',
    'r_phone': '03009999999',
    'r_address': 'Relative Address',
    'status': 'active'
}
```

4. Save and run: `python seed_data.py`

---

## 📊 Test the Data

After seeding, test with these API calls:

### View all employees
```bash
curl http://localhost:8000/api/employees/
```

### View today's attendance
```bash
curl http://localhost:8000/api/attendance/daily_report/
```

### View weekly report
```bash
curl http://localhost:8000/api/attendance/weekly_report/
```

### View monthly report
```bash
curl http://localhost:8000/api/attendance/monthly_report/?month=1&year=2024
```

### Calculate payout for an employee
```bash
curl "http://localhost:8000/api/employees/EMP001/calculate_payout/?start_date=2024-01-01&end_date=2024-01-31"
```

### View leave requests
```bash
curl http://localhost:8000/api/leave/
```

---

## 🗑️ Clearing Data

### Option 1: Using seed_data.py
```bash
python seed_data.py
# When prompted, type: y
```

This will delete all data and create fresh data.

### Option 2: Django shell
```bash
python manage.py shell
from management.models import *
Employee.objects.all().delete()
Attendance.objects.all().delete()
PaidLeave.objects.all().delete()
Shift.objects.all().delete()
exit()
```

### Option 3: Using Django admin
1. Go to http://localhost:8000/admin/
2. Select each model and delete all records

---

## 📈 Testing Scenarios

### Scenario 1: Check-In/Check-Out
1. Seed the database
2. Use Postman to check-in EMP001:
```json
POST /api/attendance/check_in/
{
    "emp_id": "EMP001"
}
```

### Scenario 2: Calculate Payroll
```bash
curl "http://localhost:8000/api/employees/EMP001/calculate_payout/?start_date=2024-01-01&end_date=2024-01-31"
```

### Scenario 3: Create Leave Request
```json
POST /api/leave/
{
    "employee": "EMP001",
    "leave_type": "sick",
    "start_time": "2024-01-20T00:00:00Z",
    "end_time": "2024-01-22T23:59:59Z",
    "reason": "Medical checkup"
}
```

### Scenario 4: Test Late Arrival Detection
```json
POST /api/attendance/
{
    "employee": "EMP001",
    "date": "2024-01-15",
    "check_in": "2024-01-15T07:30:00Z",
    "check_out": "2024-01-15T15:30:00Z",
    "status": "late"
}
```

---

## ✅ Verification Checklist

After seeding:

- [ ] Run `python manage.py runserver`
- [ ] Visit http://localhost:8000/api/employees/ - Should show employees
- [ ] Visit http://localhost:8000/api/attendance/ - Should show attendance records
- [ ] Visit http://localhost:8000/api/attendance/daily_report/ - Should show today's stats
- [ ] Visit http://localhost:8000/api/leave/ - Should show leave requests
- [ ] Create new employee via POST - Should work
- [ ] Check-in an employee - Should work
- [ ] Calculate payout - Should show values

---

## 🐛 Troubleshooting

### Error: "ModuleNotFoundError"
```bash
pip install django djangorestframework django-filter pillow
```

### Error: "RuntimeError: populate() is called"
```bash
python manage.py migrate
```

### No data shown?
```bash
python manage.py shell
from management.models import Employee
print(Employee.objects.count())
```

If count is 0, run: `python seed_data.py`

### Permission denied
Windows: Right-click command prompt and run as Administrator

---

## 📚 Files Overview

| File | Purpose | Usage |
|------|---------|-------|
| seed_data.py | Main seeding script | `python seed_data.py` |
| employees_data.csv | Employee data in CSV | Import into tools |
| initial_data.json | Django fixture | `loaddata initial_data` |
| setup_initial_data.py | Quick setup | `python setup_initial_data.py` |

---

## 🎯 Quick Start

1. **Seed the database**:
   ```bash
   python seed_data.py
   ```

2. **Start the server**:
   ```bash
   python manage.py runserver
   ```

3. **Test the API**:
   ```bash
   curl http://localhost:8000/api/employees/
   ```

4. **Explore**:
   - Visit http://localhost:8000/api/ in browser
   - Try different endpoints
   - Generate reports
   - Test calculations

---

## 📞 Questions?

- Check API_DOCUMENTATION.md for endpoint details
- See EXAMPLES.md for code examples
- Review [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for architecture

---

**Happy testing! 🚀**

Version: 1.0  
Framework: Django 6.0.3 + DRF 3.14

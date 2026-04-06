# FDPP Employee Management System (EMS)

A complete, production-ready Employee Management System built with Django REST Framework that handles employee information, attendance tracking, leave management, and payroll calculations.

## 🎯 Key Features

### Employee Management
- ✅ Complete employee profile management
- ✅ Multiple shift type support
- ✅ Emergency contact information
- ✅ Profile image upload
- ✅ Active/Inactive status tracking

### Attendance Tracking
- ✅ Check-in/Check-out system with automatic timestamps
- ✅ Late arrival detection
- ✅ **14-hour daily limit enforcement**
- ✅ Status tracking (On Time, Late, Absent, On Leave)
- ✅ Daily, weekly, and monthly attendance reports

### Leave Management
- ✅ Multiple leave types (Sick, Casual, Earned, Unpaid, Maternity)
- ✅ Leave request workflow
- ✅ Manager approval system
- ✅ Leave duration calculation
- ✅ Pending leave tracking

### Payroll System
- ✅ Hourly rate calculations
- ✅ Overtime compensation (1.5x pay rate)
- ✅ Flexible salary checkout by date range
- ✅ Detailed payout breakdowns
- ✅ Monthly and custom period calculations

### Reporting & Analytics
- ✅ Real-time daily attendance reports
- ✅ Weekly work hour summaries
- ✅ Monthly employee statistics
- ✅ Late arrival tracking and analysis
- ✅ Employee-wise attendance history

---

## 📦 Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Installation (2 minutes)

```bash
# 1. Navigate to project
cd d:\FDPP\ attendence\fdpp_ems

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install django==6.0.3 djangorestframework==3.14.0 django-filter==23.5 pillow==10.1.0

# 4. Apply migrations
python manage.py makemigrations management
python manage.py migrate

# 5. Create admin user
python manage.py createsuperuser

# 6. Run server
python manage.py runserver
```

### Access the System
- **Admin Panel**: http://localhost:8000/admin/
- **API**: http://localhost:8000/api/
- **Employees**: http://localhost:8000/api/employees/
- **Attendance**: http://localhost:8000/api/attendance/
- **Leave**: http://localhost:8000/api/leave/

---

## 📝 Basic API Examples

### Check-In Employee
```bash
curl -X POST http://localhost:8000/api/attendance/check_in/ \
  -H "Content-Type: application/json" \
  -d '{"emp_id": "EMP001"}'
```

### Check-Out Employee
```bash
curl -X POST http://localhost:8000/api/attendance/check_out/ \
  -H "Content-Type: application/json" \
  -d '{"emp_id": "EMP001"}'
```

### Get Daily Report
```bash
curl http://localhost:8000/api/attendance/daily_report/?date=2024-01-15
```

### Calculate Payout
```bash
curl "http://localhost:8000/api/employees/EMP001/calculate_payout/?start_date=2024-01-01&end_date=2024-01-31"
```

### Get Employee Stats
```bash
curl http://localhost:8000/api/employees/employee_stats/
```

---

## 📊 Database Schema

### Employee Model
```
Fields: emp_id (PK), name, salary, hourly_rate, shift_type, 
        start_time, end_time, address, phone, CNIC, 
        relative info, status, dates
Relationships: One-to-Many with Attendance & Leave
```

### Attendance Model
```
Fields: date, check_in, check_out, status, message_late
Calculated: total_hours (max 14), overtime_hours, is_late
Validation: 14-hour limit enforced
```

### PaidLeave Model
```
Fields: leave_type, start_time, end_time, reason, approved
Calculated: duration_days
Types: sick, casual, earned, unpaid, maternity
```

### Shift Model
```
Fields: name, start_time, end_time, description
Pre-configured: Morning, Afternoon, Night shifts available
```

---

## 🔧 Project Structure

```
fdpp_ems/
├── manage.py
├── db.sqlite3
├── README.md (this file)
├── SETUP.md (detailed setup guide)
├── API_DOCUMENTATION.md (API reference)
├── EXAMPLES.md (usage examples)
├── fdpp_ems/
│   ├── settings.py (Django config)
│   ├── urls.py (project URLs)
│   ├── wsgi.py
│   └── asgi.py
└── management/
    ├── models.py (Employee, Attendance, Leave, Shift)
    ├── views.py (REST API viewsets)
    ├── serializers.py (serializers)
    ├── urls.py (app URLs)
    ├── admin.py (Django admin config)
    ├── apps.py
    ├── tests.py
    └── migrations/
```

---

## 🚀 Core Features In Depth

### 1. Attendance Check-In/Check-Out
- **Automatic timestamps** when employee checks in/out
- **Late detection** compares check-in time with shift start time
- **14-hour validation** prevents excessive work days
- **Status assignment** (on_time, late, absent, on_leave)

### 2. Payroll Calculation
**Formula:**
```
Base Pay = Total Hours × Hourly Rate
Overtime Pay = Overtime Hours × Hourly Rate × 1.5
Total Payout = Base Pay + Overtime Pay
```

**Example:**
- Hourly Rate: $312.50
- Regular Hours: 160 (20 days × 8 hours)
- Overtime Hours: 20
- **Total Payout**: (160 × 312.50) + (20 × 312.50 × 1.5) = $59,375

### 3. Intelligent Filtering
- **Employee filters**: By status, shift type
- **Attendance filters**: By date range, employee, status
- **Leave filters**: By employee, type, approval status
- **Pagination**: Default 20 records per page

### 4. Comprehensive Reporting
- **Daily**: Present/absent/late counts with details
- **Weekly**: Total hours, late arrivals, daily averages
- **Monthly**: Multi-employee stats, attendance trends
- **Custom**: Any date range with detailed breakdowns

---

## 📖 Documentation

1. **[SETUP.md](SETUP.md)** - Complete installation and configuration guide
2. **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Full API reference with all endpoints
3. **[EXAMPLES.md](EXAMPLES.md)** - Usage examples and code samples

---

## 🔐 Configuration

### Current Settings
- **DEBUG**: True (for development)
- **Database**: SQLite3 (change to PostgreSQL for production)
- **Time Zone**: UTC (configure in settings.py)
- **Authentication**: Session-based (configure as needed)

### Important Settings (settings.py)
```python
# REST Framework config
REST_FRAMEWORK = {
    'PAGE_SIZE': 20,  # Default pagination
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
}

# Time zone (change for your region)
TIME_ZONE = 'UTC'  # Change to 'Asia/Karachi' for Pakistan
```

---

## 🛠️ Common Operations

### Add New Employee
```python
POST /api/employees/
{
    "emp_id": "EMP001",
    "name": "John Doe",
    "salary": 50000,
    "hourly_rate": 312.50,
    "shift_type": "morning",
    "start_time": "06:00:00",
    "end_time": "14:00:00",
    ...
}
```

### Daily Operations
```bash
# Morning: Check-in all employees
POST /api/attendance/check_in/

# Evening: Check-out all employees
POST /api/attendance/check_out/

# Get daily summary
GET /api/attendance/daily_report/
```

### Month-End
```bash
# Calculate all payouts
GET /api/employees/{id}/calculate_payout/?start_date=2024-01-01&end_date=2024-01-31

# Get master attendance report
GET /api/attendance/monthly_report/?month=1&year=2024
```

---

## 🐛 Troubleshooting

### Port Already in Use
```bash
python manage.py runserver 8001
```

### Module Not Found
```bash
pip install djangorestframework django-filter
```

### Database Issues
```bash
python manage.py migrate management --run-syncdb
```

See [SETUP.md](SETUP.md) for more troubleshooting tips.

---

## 📋 API Endpoint Summary

### Employees
- `GET /api/employees/` - List all employees
- `POST /api/employees/` - Create employee
- `GET /api/employees/{id}/` - Get single employee
- `PATCH /api/employees/{id}/` - Update employee
- `GET /api/employees/{id}/calculate_payout/` - Calculate payout
- `GET /api/employees/{id}/attendance_report/` - Get attendance report
- `GET /api/employees/employee_stats/` - Get statistics

### Attendance
- `GET /api/attendance/` - List attendance records
- `POST /api/attendance/check_in/` - Check-in employee
- `POST /api/attendance/check_out/` - Check-out employee
- `GET /api/attendance/daily_report/` - Daily report
- `GET /api/attendance/weekly_report/` - Weekly report
- `GET /api/attendance/monthly_report/` - Monthly report

### Leave
- `GET /api/leave/` - List all leaves
- `POST /api/leave/` - Create leave request
- `POST /api/leave/{id}/approve/` - Approve leave
- `POST /api/leave/{id}/reject/` - Reject leave
- `GET /api/leave/pending_approvals/` - Get pending leaves
- `GET /api/leave/employee_leaves/` - Get employee's leaves

### Shifts
- `GET /api/shifts/` - List all shifts
- `POST /api/shifts/` - Create shift
- `PATCH /api/shifts/{id}/` - Update shift

---

## 💡 System Constraints

1. **14-Hour Daily Limit**: Work duration cannot exceed 14 hours in a single day
2. **Unique Daily Attendance**: Only one attendance record per employee per day
3. **Check-Out Validation**: Check-out time must be after check-in time
4. **Shift Requirements**: Each employee must have assigned start and end times

---

## 🎓 Learning Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django Filter](https://django-filter.readthedocs.io/)

---

## 📞 Support

For issues or questions:
1. Check [SETUP.md](SETUP.md) for setup issues
2. Review [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for API questions
3. See [EXAMPLES.md](EXAMPLES.md) for usage examples

---

## 📄 License

Open Source - Feel free to use and modify for your needs

---

## 🔄 Version History

**v1.0** (Current)
- Employee management system
- Complete attendance tracking
- Leave management system
- Payroll calculations
- Comprehensive reporting
- REST API with filtering

---

## ✨ Features Implemented (Based on Requirements)

From your image attachment:

### Employee Fields ✅
- name, profile_img, salary, PK:emp_id
- shift_type, start_time, end_time
- address, phone, CNIC, relative, r_phone, r_address

### Constraints & Features ✅
- ✅ 14 hrs limit for checked out attendance management
- ✅ Every employee attendance with filters (day, week, month, custom, employee)
- ✅ Add & edit user model (full CRUD operations)
- ✅ Hourly payment calculations
- ✅ Salary checkout for the payout
- ✅ Paid leave (start_time to end_time)

### Attendance Fields ✅
- FK:emp_id, check_in, check_out, message (late), date

---

**Created**: 2024  
**Framework**: Django 6.0.3 + Django REST Framework 3.14  
**Database**: SQLite3 (production-ready for PostgreSQL/MySQL)  
**Python**: 3.8+

---

🚀 **Ready to deploy! Follow [SETUP.md](SETUP.md) to get started in minutes.**

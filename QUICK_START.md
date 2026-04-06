# ⚡ FDPP-EMS Quick Start Guide

Get your Employee Management System up and running in **5 minutes**!

---

## 🚀 Installation (5 Minutes)

### Step 1: Activate Virtual Environment
```bash
cd "d:\FDPP attendence\fdpp_ems"
venv\Scripts\activate
```

### Step 2: Install Dependencies
```bash
pip install django==6.0.3 djangorestframework==3.14.0 django-filter==23.5 pillow==10.1.0
```

### Step 3: Run Migrations
```bash
python manage.py makemigrations management
python manage.py migrate
```

### Step 4: Create Admin Account
```bash
python manage.py createsuperuser
# Enter username, email, password
```

### Step 5: Start Server
```bash
python manage.py runserver
```

**✅ Done! Your system is now running.**

---

## 📱 Access Points

| What | URL | Notes |
|------|-----|-------|
| API Root | http://localhost:8000/api/ | Interactive API browser |
| Admin Panel | http://localhost:8000/admin/ | Login with superuser account |
| Employees | http://localhost:8000/api/employees/ | List & create employees |
| Attendance | http://localhost:8000/api/attendance/ | Check-in/out & reports |
| Leave | http://localhost:8000/api/leave/ | Manage leave requests |
| Shifts | http://localhost:8000/api/shifts/ | Manage shifts |

---

## 💼 Basic Workflow

### Morning: Check-In Employees
```bash
curl -X POST http://localhost:8000/api/attendance/check_in/ \
  -H "Content-Type: application/json" \
  -d '{"emp_id": "EMP001"}'
```

### Evening: Check-Out Employees
```bash
curl -X POST http://localhost:8000/api/attendance/check_out/ \
  -H "Content-Type: application/json" \
  -d '{"emp_id": "EMP001"}'
```

### End of Day: Get Report
```bash
curl http://localhost:8000/api/attendance/daily_report/
```

### Month-End: Calculate Payroll
```bash
curl "http://localhost:8000/api/employees/EMP001/calculate_payout/?start_date=2024-01-01&end_date=2024-01-31"
```

---

## 📊 Quick Reference

### Create Employee
```json
POST /api/employees/
{
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
    "r_address": "456 Side St",
    "status": "active"
}
```

### Get All Employees
```
GET /api/employees/
```

### Get Daily Report
```
GET /api/attendance/daily_report/?date=2024-01-15
```

### Get Weekly Stats
```
GET /api/attendance/weekly_report/
```

### Get Monthly Stats
```
GET /api/attendance/monthly_report/?month=1&year=2024
```

### Get Leave Requests
```
GET /api/leave/pending_approvals/
```

### Approve Leave
```
POST /api/leave/1/approve/
{
    "approved_by": "Manager Name"
}
```

---

## 🔑 Key Features (At a Glance)

| Feature | What It Does |
|---------|-------------|
| **Check-In/Out** | Automatic timestamping with late detection |
| **14-Hour Limit** | Prevents excessive work days (enforced) |
| **Overtime Pay** | Calculates 1.5x pay for hours beyond 8 |
| **Daily Reports** | Present/absent/late counts |
| **Weekly Reports** | Total hours, averages, late trends |
| **Monthly Reports** | Multi-employee statistics |
| **Payroll** | Flexible date range calculations |
| **Leave Management** | Multiple types with approval workflow |
| **Shift Management** | Predefined or custom shift configurations |

---

## 🎯 Common Tasks

### Task: Create New Employee
1. Click "Employees" tab in API root
2. Click "POST" button (or use curl)
3. Fill in employee details
4. Click "POST"

**Or use curl:**
```bash
curl -X POST http://localhost:8000/api/employees/ -H "Content-Type: application/json" -d '{ ... }'
```

### Task: Check-In Employees
**Single Employee:**
```bash
curl -X POST http://localhost:8000/api/attendance/check_in/ \
  -H "Content-Type: application/json" \
  -d '{"emp_id": "EMP001"}'
```

**Batch (Python):**
```python
import requests

emp_ids = ["EMP001", "EMP002", "EMP003"]
for emp_id in emp_ids:
    requests.post(
        "http://localhost:8000/api/attendance/check_in/",
        json={"emp_id": emp_id}
    )
```

### Task: View Attendance Report
```bash
# Today
curl http://localhost:8000/api/attendance/daily_report/

# Specific date
curl "http://localhost:8000/api/attendance/daily_report/?date=2024-01-15"

# Weekly
curl http://localhost:8000/api/attendance/weekly_report/

# Monthly
curl "http://localhost:8000/api/attendance/monthly_report/?month=1&year=2024"
```

### Task: Calculate Employee Payout
```bash
curl "http://localhost:8000/api/employees/EMP001/calculate_payout/?start_date=2024-01-01&end_date=2024-01-31"
```

**Response:**
```json
{
    "employee_id": "EMP001",
    "employee_name": "John Doe",
    "total_hours": 160,
    "overtime_hours": 20,
    "hourly_rate": "312.50",
    "base_payout": 50000,
    "overtime_payout": 9375,
    "total_payout": 59375
}
```

### Task: Request & Approve Leave
**Create Request:**
```bash
curl -X POST http://localhost:8000/api/leave/ \
  -H "Content-Type: application/json" \
  -d '{
    "employee": "EMP001",
    "leave_type": "sick",
    "start_time": "2024-01-20T00:00:00Z",
    "end_time": "2024-01-22T23:59:59Z",
    "reason": "Medical checkup"
  }'
```

**View Pending:**
```bash
curl http://localhost:8000/api/leave/pending_approvals/
```

**Approve:**
```bash
curl -X POST http://localhost:8000/api/leave/1/approve/ \
  -H "Content-Type: application/json" \
  -d '{"approved_by": "Manager Name"}'
```

---

## 🔍 Troubleshooting Checklist

| Problem | Solution |
|---------|----------|
| Port 8000 already in use | `python manage.py runserver 8001` |
| `ModuleNotFoundError` | `pip install djangorestframework django-filter` |
| Database errors | `python manage.py migrate` |
| Image upload fails | `pip install pillow` |
| Can't access API | Ensure server is running & check http://localhost:8000/api/ |
| Admin login fails | Recreate superuser: `python manage.py createsuperuser` |

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **README.md** | Project overview & features |
| **SETUP.md** | Detailed installation & configuration |
| **API_DOCUMENTATION.md** | Complete API reference |
| **EXAMPLES.md** | Code examples & use cases |
| **QUICK_START.md** | This file - quick reference |

---

## 🎓 Learning Path

1. **5 min**: Read this file
2. **10 min**: Follow Installation steps above
3. **10 min**: Create test employee using API
4. **5 min**: Test check-in/check-out
5. **5 min**: View daily report
6. **Explore**: Use API_DOCUMENTATION.md for advanced features

---

## 💡 Pro Tips

1. **Use Admin Panel** - Easier for initial data entry (http://localhost:8000/admin/)
2. **Test Endpoints First** - Use API root browser before writing code
3. **Date Format** - Always use `YYYY-MM-DD` for dates
4. **Filter by Employee ID** - Much faster than loading all records
5. **Pagination** - Results are limited to 20 per page by default
6. **Check Timestamps** - Ensure system time is correct for accurate reports
7. **Backup Database** - Keep copies of db.sqlite3 before migrations

---

## 🚨 Important Constraints

1. **14-Hour Limit**: Work duration cannot exceed 14 hours per day
2. **Unique Daily Attendance**: Only one check-in per employee per day
3. **Check-Out Validation**: Check-out time must be after check-in
4. **Required Fields**: emp_id, name, salary, hourly_rate are required for employees

---

## 📞 Getting Help

1. **API Error?** → Check API_DOCUMENTATION.md for endpoint details
2. **Installation Issue?** → See SETUP.md troubleshooting section
3. **Code Example?** → Find it in EXAMPLES.md
4. **System Feature?** → Search README.md

---

## Next Steps

✅ Installation complete  
⬜ Create test employees  
⬜ Test attendance check-in/out  
⬜ Generate reports  
⬜ Calculate payroll  
⬜ Configure shift patterns  
⬜ Set up leave types  

---

**Version**: 1.0  
**Last Updated**: 2024  
**Framework**: Django + Django REST Framework

🎉 **You're all set! Start with `/api/employees/` endpoint.**

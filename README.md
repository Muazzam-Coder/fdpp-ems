# FDPP Employee Management System (EMS)

A complete, production-ready Employee Management System built with Django REST Framework that handles employee information, attendance tracking, leave management, shift history, overtime, holidays, and payroll calculations.

## Key Features

### Employee Management
- Complete employee profile management
- **Shift history tracking** with salary snapshots
- **Weekly off-day configuration** (per employee)
- Emergency contact information
- Profile image upload
- Active/Inactive status tracking

### Attendance Tracking
- Check-in/Check-out system with automatic timestamps
- Late arrival detection (based on active shift)
- **14-hour daily limit enforcement**
- Status tracking (On Time, Late, Absent, On Leave)
- Daily, weekly, and monthly attendance reports

### Shift Management
- **Shift history** — every shift assignment is recorded with date ranges
- **Assign shifts ad-hoc** — no pre-planning required
- **Auto-close previous shifts** when a new one is assigned
- **Salary snapshot** — stores salary at time of assignment

### Leave Management
- Multiple leave types (Sick, Casual, Earned, Unpaid, Maternity)
- Leave request workflow
- Manager approval system
- Leave duration calculation
- Pending leave tracking

### Holiday Management
- Company-wide **declared holidays** (Eid, etc.)
- **Paid holidays** automatically included in salary calculations

### Overtime Management
- Manager-approved overtime with pending/approved/rejected workflow
- Overtime paid at **same hourly rate** as regular hours

### Payroll System
- **Per-shift hourly rate** calculation based on salary and working days
- Prorated salary when shifts change mid-month
- Includes paid holidays, weekly off-days, approved leaves, and overtime
- Detailed payout breakdowns by shift period
- Flexible payout calculation for any date range

### Reporting & Analytics
- Real-time daily attendance reports
- Weekly work hour summaries
- Monthly employee statistics
- Late arrival tracking and analysis
- Employee-wise attendance history
- Excel export with payout data

---

## Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Installation

```bash
# 1. Navigate to project
cd fdpp_ems

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements/requirements.txt

# 4. Apply migrations
python manage.py migrate

# 5. Create admin user
python manage.py createsuperuser

# 6. Run server (development)
python manage.py runserver --insecure
# OR with Daphne (production)
daphne -b 0.0.0.0 -p 8000 fdpp_ems.asgi:application
```

### Access the System
- **Admin Panel**: `http://localhost:8000/admin/`
- **API**: `http://localhost:8000/api/`
- **Employees**: `http://localhost:8000/api/employees/`
- **Attendance**: `http://localhost:8000/api/attendance/`
- **Shifts**: `http://localhost:8000/api/shifts/`
- **Holidays**: `http://localhost:8000/api/holidays/`
- **Overtime**: `http://localhost:8000/api/overtime/`
- **Leave**: `http://localhost:8000/api/leave/`

---

## API Endpoints

### Authentication
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/register/` | Register new user + employee |
| POST | `/api/auth/login/` | Login |
| POST | `/api/auth/create_admin_manager/` | Create admin/manager (admin only) |
| POST | `/api/token/` | Get JWT token |
| POST | `/api/token/refresh/` | Refresh JWT token |

### Employees
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/employees/` | List all employees |
| POST | `/api/employees/` | Create employee |
| GET | `/api/employees/{emp_id}/` | Get employee details |
| PATCH | `/api/employees/{emp_id}/` | Update employee |
| GET | `/api/employees/active_employees/` | List active employees |
| GET | `/api/employees/employee_stats/` | Get statistics |
| GET | `/api/employees/{emp_id}/attendance_report/` | Attendance report |
| GET | `/api/employees/{emp_id}/calculate_payout/` | **Calculate payout (updated)** |
| GET/POST | `/api/employees/{emp_id}/assign_shift/` | **Get/assign a shift (new)** |
| GET | `/api/employees/{emp_id}/shift_history/` | **View shift history (new)** |
| GET/POST | `/api/employees/{emp_id}/relatives/` | Manage relatives |

### Attendance
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/attendance/` | List records (supports filters) |
| POST | `/api/attendance/check_in/` | Check-in/out |
| POST | `/api/attendance/auto_attendance/` | Biometric auto attendance |
| POST | `/api/attendance/mark_absent/` | Mark absent (admin only) |
| GET | `/api/attendance/daily_report/` | Daily report |
| GET | `/api/attendance/weekly_report/` | Weekly report |
| GET | `/api/attendance/monthly_report/` | Monthly report |
| GET | `/api/attendance/export_excel/` | Export attendance to Excel |
| GET | `/api/attendance/export_payout/` | Export payout to Excel |

### Shifts
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/shifts/` | List all shifts |
| POST | `/api/shifts/` | Create shift |
| PATCH | `/api/shifts/{id}/` | Update shift |
| DELETE | `/api/shifts/{id}/` | Delete shift |

### Holidays (New)
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/holidays/` | List all holidays |
| POST | `/api/holidays/` | Create holiday |
| PATCH | `/api/holidays/{id}/` | Update holiday |
| DELETE | `/api/holidays/{id}/` | Delete holiday |

### Overtime (New)
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/overtime/` | List overtime records |
| POST | `/api/overtime/` | Create overtime request |
| POST | `/api/overtime/{id}/approve/` | Approve overtime |
| POST | `/api/overtime/{id}/reject/` | Reject overtime |

### Leave
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/leave/` | List all leaves |
| POST | `/api/leave/` | Create leave request |
| POST | `/api/leave/{id}/approve/` | Approve leave |
| POST | `/api/leave/{id}/reject/` | Reject leave |
| GET | `/api/leave/pending_approvals/` | Pending leaves |
| GET | `/api/leave/employee_leaves/` | Employee leaves |

### Access Levels
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/access-levels/` | List all (admin only) |
| GET | `/api/access-levels/admins/` | List admins |
| GET | `/api/access-levels/managers/` | List managers |

---

## Payout Calculation

The payout system uses **per-shift hourly rates** with salary prorated by calendar days.

### Formula

```
For each shift period in the date range:
  month_days        = total calendar days in the month
  period_days       = calendar days in this shift period
  weekly_off_count  = number of weekly off-days in this period
  working_days      = period_days - weekly_off_count
  shift_hours       = shift_end_time - shift_start_time
  expected_hours    = working_days × shift_hours
  salary_portion    = salary_snapshot × (period_days / month_days)
  hourly_rate       = salary_portion / expected_hours

  For each date:
    attendance → actual_hours × hourly_rate
    off-day    → shift_hours × hourly_rate (paid)
    holiday    → shift_hours × hourly_rate (paid)
    leave      → shift_hours × hourly_rate (paid)
    absent     → $0
    overtime   → ot_hours × hourly_rate (same rate)
```

### Example Payout Request
```
GET /api/employees/1/calculate_payout/?start_date=2026-06-01&end_date=2026-06-30
```

See [FRONTEND_API_GUIDE.md](FRONTEND_API_GUIDE.md) for the full response shape.

---

## Database Schema

### Employee
```
Fields: emp_id (PK), name, salary, current_shift (FK), weekly_off_day, ...
Removed: shift_type, start_time, end_time
```

### EmployeeShiftHistory (New)
```
Fields: employee (FK), shift (FK), from_date, to_date, salary (snapshot),
        shift_start_time, shift_end_time
```

### Holiday (New)
```
Fields: date (unique), name, is_paid
```

### Overtime (New)
```
Fields: employee (FK), date, start_time, end_time, approved_by (FK),
        status, note
```

---

## Project Structure

```
fdpp_ems/
├── manage.py
├── db.sqlite3
├── README.md
├── FRONTEND_API_GUIDE.md          (guide for frontend devs)
├── BACKEND_CHANGES.md             (guide for backend changes)
├── fdpp_ems/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── staticfiles/                   (collected static files)
├── templates/                     (overridden Django templates)
└── management/
    ├── models.py                  (all models)
    ├── views.py                   (all API views)
    ├── serializers.py             (all serializers)
    ├── urls.py                    (app URLs)
    ├── admin.py                   (Django admin config)
    └── migrations/
```

---

## Configuration

### Current Settings
- **DEBUG**: False
- **Database**: SQLite3
- **Time Zone**: Asia/Karachi
- **Authentication**: JWT (SimpleJWT) + Session
- **Static Files**: WhiteNoise

---

## Version History

**v2.0** (Current)
- Shift history tracking with salary snapshots
- Per-employee weekly off-day configuration
- Company-wide holidays management
- Overtime management with approval workflow
- Per-shift hourly rate payout calculation
- Paid off-days, holidays, and leaves in salary
- Updated check-in uses active shift from history

**v1.0**
- Initial employee management system
- Attendance tracking
- Leave management
- Basic payroll calculations

---

## Documentation

- **[FRONTEND_API_GUIDE.md](FRONTEND_API_GUIDE.md)** — Complete API reference for frontend developers
- **[BACKEND_CHANGES.md](BACKEND_CHANGES.md)** — Summary of backend changes

---

## License

Open Source - Feel free to use and modify for your needs

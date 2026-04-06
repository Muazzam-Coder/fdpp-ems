# Project Structure & File Guide

## Directory Overview

```
d:\FDPP attendence\
├── fdpp_ems/                          # Main project folder
│   ├── manage.py                      # Django management script
│   ├── db.sqlite3                     # SQLite database
│   │
│   ├── fdpp_ems/                      # Project settings folder
│   │   ├── __init__.py
│   │   ├── settings.py                # Django configuration
│   │   ├── urls.py                    # Project-level URLs
│   │   ├── asgi.py                    # ASGI config (deployment)
│   │   └── wsgi.py                    # WSGI config (deployment)
│   │
│   └── management/                    # Main application folder
│       ├── migrations/                # Database migration files
│       │   ├── __init__.py
│       │   └── 0001_initial.py
│       │
│       ├── __init__.py
│       ├── admin.py                   # Django admin configuration
│       ├── apps.py                    # App configuration
│       ├── models.py                  # Database models
│       ├── serializers.py             # REST API serializers
│       ├── views.py                   # REST API views/endpoints
│       ├── urls.py                    # App-level URL routing
│       ├── tests.py                   # Unit tests
│       └── __pycache__/               # Python cache
│
├── venv/                              # Virtual environment (NOT in repo)
│
├── README.md                          # Project overview
├── QUICK_START.md                     # 5-minute quick start guide
├── SETUP.md                           # Detailed setup & configuration
├── API_DOCUMENTATION.md               # Complete API reference
├── EXAMPLES.md                        # Usage examples & code samples
├── PROJECT_STRUCTURE.md               # This file
├── requirements.txt                   # Python dependencies
└── setup_initial_data.py             # Data initialization script
```

---

## File Descriptions

### Root Project Files

#### `manage.py`
- Django project management script
- Used for: running server, migrations, creating admin users
- Common commands:
  ```bash
  python manage.py runserver
  python manage.py makemigrations
  python manage.py migrate
  python manage.py createsuperuser
  ```

#### `db.sqlite3`
- SQLite database file
- Contains all application data
- Created automatically on first migration
- Can be backed up: `cp db.sqlite3 db.sqlite3.backup`

#### `requirements.txt`
- Lists all Python dependencies
- Quick install: `pip install -r requirements.txt`
- Current packages:
  - Django 6.0.3
  - Django REST Framework 3.14.0
  - django-filter 23.5
  - Pillow 10.1.0

---

### Configuration Files (fdpp_ems/ folder)

#### `settings.py`
Key configurations:
- **INSTALLED_APPS**: Registered Django apps
  - `django.contrib.admin` - Admin interface
  - `django.contrib.auth` - Authentication
  - `rest_framework` - REST API
  - `django_filters` - Filtering
  - `management` - Our application
- **DATABASES**: Database configuration (SQLite3)
- **REST_FRAMEWORK**: API pagination, filtering, authentication
- **TIME_ZONE**: Currently UTC (change to 'Asia/Karachi' for Pakistan)

#### `urls.py`
- Main URL router for the project
- Routes all requests starting with `/api/` to management app URLs
- Includes Django admin at `/admin/`

#### `wsgi.py` & `asgi.py`
- Deployment configurations
- wsgi.py: For traditional servers (Apache, Gunicorn)
- asgi.py: For async servers (Uvicorn, Hypercorn)

---

### Application Files (management/ folder)

#### `models.py` ⭐
**Database Models** (4 models):

1. **Employee**
   - Fields: emp_id (PK), name, profile_img, salary, hourly_rate, shift_type, start_time, end_time, address, phone, CNIC, relative, r_phone, r_address, status, date_joined, last_modified
   - Relationships: One-to-many with Attendance and PaidLeave
   - Methods: `total_hours_today` property
   - Used for: Employee profile management

2. **Attendance**
   - Fields: employee (FK), date, check_in, check_out, message_late, status, created_at, updated_at
   - Relationships: Foreign key to Employee
   - Properties: `total_hours`, `overtime_hours`, `is_late`
   - Validations: 14-hour limit, unique per employee per day
   - Used for: Track daily work hours

3. **PaidLeave**
   - Fields: employee (FK), leave_type, start_time, end_time, reason, approved, approved_by, created_at, updated_at
   - Relationships: Foreign key to Employee
   - Properties: `duration_days`
   - Leave types: sick, casual, earned, unpaid, maternity
   - Used for: Manage employee leave requests

4. **Shift**
   - Fields: name, start_time, end_time, description, created_at
   - Used for: Define shift patterns (Morning, Afternoon, Night)

#### `serializers.py` 🔄
**REST API Serializers** (converts models to JSON):

1. **ShiftSerializer**: Serializes Shift model
2. **EmployeeSerializer**: Serializes Employee with `total_hours_today`
3. **AttendanceSerializer**: Serializes Attendance with calculated fields (`total_hours`, `overtime_hours`, `is_late`)
4. **PaidLeaveSerializer**: Serializes PaidLeave with `duration_days`

Features:
- Read-only calculated fields
- Validation rules
- Related field display (e.g., employee_name)

#### `views.py` 🚀
**REST API ViewSets** (endpoints/controllers):

1. **EmployeeViewSet** (7 custom actions)
   - CRUD: Create, read, update, delete employees
   - `calculate_payout()` - Payroll calculation
   - `attendance_report()` - Filter by period
   - `active_employees()` - List active only
   - `employee_stats()` - Overall statistics

2. **AttendanceViewSet** (5 custom actions)
   - CRUD: Manage attendance records
   - `check_in()` - Auto check-in
   - `check_out()` - Auto check-out with 14-hour validation
   - `daily_report()` - Daily summary
   - `weekly_report()` - Weekly analytics
   - `monthly_report()` - Monthly statistics

3. **PaidLeaveViewSet** (4 custom actions)
   - CRUD: Manage leave requests
   - `approve()` - Approve leave
   - `reject()` - Reject leave
   - `pending_approvals()` - View pending
   - `employee_leaves()` - Filter by employee

4. **ShiftViewSet**
   - CRUD: Manage shifts

#### `urls.py` 📍
**URL Routing**:
- Uses DefaultRouter for automatic URL generation
- Registers all viewsets
- Provides endpoints like:
  - `/api/employees/`
  - `/api/attendance/`
  - `/api/leave/`
  - `/api/shifts/`

#### `admin.py` 👨‍💼
**Django Admin Configuration**:
- Employee admin: Full fields with filters
- Attendance admin: Status filters, read-only calculated fields
- Leave admin: Approval workflow display
- Shift admin: Simple configuration

Provides web interface for data management at `/admin/`

#### `apps.py`
- App configuration
- Default: ManagementConfig class
- Can add signals and ready methods here

#### `tests.py`
- Unit test file
- Run with: `python manage.py test management`
- Current: Empty (ready for test development)

#### `migrations/` folder
- **0001_initial.py**: Initial schema creation
- New migrations created with: `python manage.py makemigrations`
- Migrations applied with: `python manage.py migrate`

---

### Documentation Files

#### `README.md`
- **Purpose**: Project overview and features
- **Content**: Features list, quick start, key endpoints
- **Audience**: Developers, project managers
- **Length**: ~500 lines

#### `QUICK_START.md`
- **Purpose**: 5-minute installation and basic usage
- **Content**: Step-by-step setup, common tasks, troubleshooting
- **Audience**: First-time users
- **Length**: ~300 lines

#### `SETUP.md`
- **Purpose**: Detailed installation and configuration guide
- **Content**: Full setup, configuration options, troubleshooting, deployment
- **Audience**: Developers, system administrators
- **Length**: ~800 lines

#### `API_DOCUMENTATION.md`
- **Purpose**: Complete API reference
- **Content**: Every endpoint, request/response examples, error codes
- **Audience**: API developers, integration developers
- **Length**: ~1200 lines

#### `EXAMPLES.md`
- **Purpose**: Practical code examples
- **Content**: cURL commands, Python examples, use cases
- **Audience**: Developers implementing the API
- **Length**: ~900 lines

#### `PROJECT_STRUCTURE.md`
- **Purpose**: File organization and explanation
- **Content**: Directory tree, file purposes, class diagrams
- **Audience**: New developers, maintainers
- **Current**: This file

---

### Utility Files

#### `requirements.txt`
```
Django==6.0.3
djangorestframework==3.14.0
django-filter==23.5
pillow==10.1.0
python-dateutil==2.8.2
```
- Install all: `pip install -r requirements.txt`

#### `setup_initial_data.py`
- Script to create sample shifts and employees
- Run: `python setup_initial_data.py`
- Creates:
  - 3 sample shifts (Morning, Afternoon, Night)
  - 1 demo employee
  - Displays API endpoints and quick commands

---

## Key Relationships Diagram

```
Employee (PK: emp_id)
    ├── 1 ──→ Many: Attendance records
    │       └── Tracks: check_in, check_out, hours, status
    │
    ├── 1 ──→ Many: PaidLeave requests
    │       └── Tracks: leave_type, duration, approval
    │
    └── Uses: Shift configuration
            └── Sets: start_time, end_time for shift_type
```

---

## API Endpoint Mapping

### Employee Endpoints
```
GET    /api/employees/                              List employees
POST   /api/employees/                              Create employee
GET    /api/employees/{emp_id}/                     Get employee
PATCH  /api/employees/{emp_id}/                     Update employee
DELETE /api/employees/{emp_id}/                     Delete employee
GET    /api/employees/{emp_id}/calculate_payout/   Calculate payroll
GET    /api/employees/{emp_id}/attendance_report/  Get attendance report
GET    /api/employees/active_employees/            List active employees
GET    /api/employees/employee_stats/              Get statistics
```

### Attendance Endpoints
```
GET    /api/attendance/                             List records
POST   /api/attendance/                             Create record
GET    /api/attendance/{id}/                        Get record
PATCH  /api/attendance/{id}/                        Update record
DELETE /api/attendance/{id}/                        Delete record
POST   /api/attendance/check_in/                    Check-in
POST   /api/attendance/check_out/                   Check-out
GET    /api/attendance/daily_report/               Daily report
GET    /api/attendance/weekly_report/              Weekly report
GET    /api/attendance/monthly_report/             Monthly report
```

### Leave Endpoints
```
GET    /api/leave/                                  List leaves
POST   /api/leave/                                  Create leave
GET    /api/leave/{id}/                             Get leave
PATCH  /api/leave/{id}/                             Update leave
DELETE /api/leave/{id}/                             Delete leave
POST   /api/leave/{id}/approve/                     Approve leave
POST   /api/leave/{id}/reject/                      Reject leave
GET    /api/leave/pending_approvals/               Pending approvals
GET    /api/leave/employee_leaves/                 Employee's leaves
```

### Shift Endpoints
```
GET    /api/shifts/                                 List shifts
POST   /api/shifts/                                 Create shift
GET    /api/shifts/{id}/                            Get shift
PATCH  /api/shifts/{id}/                            Update shift
DELETE /api/shifts/{id}/                            Delete shift
```

---

## Development Workflow

### Creating a New Feature

1. **Update Model** (models.py)
   ```python
   # Add field/method
   new_field = models.CharField(max_length=100)
   ```

2. **Create Serializer** (serializers.py)
   ```python
   # Update serializer to include new field
   fields = [..., 'new_field']
   ```

3. **Add ViewSet Action** (views.py)
   ```python
   @action(detail=True, methods=['get'])
   def new_action(self, request, pk=None):
       # Implementation
   ```

4. **Create Migration**
   ```bash
   python manage.py makemigrations management
   ```

5. **Apply Migration**
   ```bash
   python manage.py migrate
   ```

6. **Update Admin** (admin.py)
   ```python
   # Add to list_display, fieldsets, etc.
   ```

7. **Test**
   ```bash
   python manage.py test management
   ```

---

## Database Schema Quick Reference

### Employee Table
```
Columns: emp_id (PK), name, profile_img, salary, hourly_rate,
         shift_type, start_time, end_time, address, phone, CNIC,
         relative, r_phone, r_address, status, date_joined, last_modified
Indexes: emp_id, status, date_joined
```

### Attendance Table
```
Columns: id (PK), employee_id (FK), date, check_in, check_out,
         message_late, status, created_at, updated_at
Unique: (employee_id, date)
Indexes: (employee_id, date), date, status
```

### PaidLeave Table
```
Columns: id (PK), employee_id (FK), leave_type, start_time, end_time,
         reason, approved, approved_by, created_at, updated_at
Indexes: (employee_id, start_time), approved
```

### Shift Table
```
Columns: id (PK), name, start_time, end_time, description, created_at
Unique: name
```

---

## Performance Optimization Tips

1. **Use Indexes**: Already configured for frequently queried fields
2. **Pagination**: Default 20 records per page
3. **Filtering**: Use query parameters to reduce data transfer
4. **Select Related**: Use when fetching related objects
5. **Caching**: Can be added to expensive calculations

---

## Security Considerations

1. **Current State** (Development):
   - DEBUG = True
   - SECRET_KEY exposed
   - ALLOWED_HOSTS = []

2. **Production Changes Needed**:
   - Set DEBUG = False
   - Use environment variables for secrets
   - Configure ALLOWED_HOSTS
   - Use PostgreSQL instead of SQLite
   - Enable HTTPS
   - Set up authentication/permissions
   - Configure CORS if needed
   - Use secure password validation

---

## Testing Guide

### Run All Tests
```bash
python manage.py test management
```

### Run Specific Test
```bash
python manage.py test management.tests.TestClassName
```

### Test Coverage
```bash
pip install coverage
coverage run --source='.' manage.py test management
coverage report
```

---

## Deployment Checklist

- [ ] Set DEBUG = False
- [ ] Configure ALLOWED_HOSTS
- [ ] Set SECRET_KEY from environment variable
- [ ] Switch to PostgreSQL
- [ ] Enable HTTPS
- [ ] Configure static files
- [ ] Set up media files location
- [ ] Configure logging
- [ ] Set up email backend
- [ ] Configure database backups
- [ ] Review SECURITY settings
- [ ] Run security check: `python manage.py check --deploy`

---

**Last Updated**: 2024  
**Version**: 1.0  
**Framework**: Django 6.0.3 + DRF 3.14

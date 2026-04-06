# Database Migration Guide - Authentication & Auto-Generated emp_id

## Overview
These changes add user authentication and auto-generate employee IDs. Since `emp_id` was the primary key and is now a regular field, this requires careful migration.

## Changes Made

### 1. Employee Model
- **Added**: `user` field (OneToOneField to Django User)
- **Changed**: `emp_id` from primary key to auto-generated unique CharField (format: EMP0001, EMP0002, etc.)
- **Added**: Signal to auto-generate emp_id on save

### 2. Removed Overtime Logic
- Removed `overtime_hours` property from Attendance model
- Updated `calculate_payout()` endpoint to remove overtime calculations
- Updated all serializers to exclude overtime fields

### 3. Authentication Endpoints
- `/api/auth/register/` - Create new user with employee profile
- `/api/auth/login/` - User login

## Migration Steps

### Step 1: Backup Your Database
```bash
# Before making any changes, backup your current database
copy db.sqlite3 db.sqlite3.backup
```

### Step 2: Create and Apply Migrations
```bash
cd d:\FDPP attendence\fdpp_ems

# Create migration files
python manage.py makemigrations

# Apply migrations
python manage.py migrate
```

### Step 3: Fix Data (If Needed)
If you have existing employees without emp_id, the signal will auto-generate them on next save.

### Step 4: Handle Existing Foreign Keys
If the migration fails due to foreign key constraints, follow these steps:

```bash
# Delete all migration files except __init__.py in migrations/
# Keep only: 0001_initial.py

# Reset the database (DEV ONLY - will lose data!)
python manage.py migrate management zero

# Remove all migration files except __init__.py
del migrations\000*.py
del migrations\__pycache__\*

# Recreate migrations
python manage.py makemigrations

# Apply fresh migrations
python manage.py migrate
```

### Step 5: Seed Data (If Needed)
```bash
python seed_data.py
```

## API Changes

### Old Endpoint Format (Still Works)
```
GET /api/employees/EMP001/attendance_report/
```

### New Authentication Endpoints
```
POST /api/auth/register/
{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "secure_pass123",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "03001234567",
    "CNIC": "12345-1234567-1",
    "address": "123 Main St",
    "relative": "Jane Doe",
    "r_phone": "03009876543",
    "r_address": "456 Side St",
    "start_time": "09:00:00",
    "end_time": "17:00:00"
}

POST /api/auth/login/
{
    "username": "john_doe",
    "password": "secure_pass123"
}
```

### Payroll Calculation (No More Overtime)
```
GET /api/employees/EMP001/calculate_payout/?start_date=2026-01-01&end_date=2026-01-31

Response:
{
    "employee_id": "EMP001",
    "employee_name": "John Doe",
    "period": "2026-01-01 to 2026-01-31",
    "total_hours": 160,
    "hourly_rate": "312.50",
    "total_payout": 50000.0
}
```

## Troubleshooting

### If migration fails with "table already exists"
```bash
# Delete all migration files (except __init__.py)
# Start fresh with a new database

# Or manually fix in Django shell:
python manage.py shell

from django.db import connection
cursor = connection.cursor()
cursor.execute("DROP TABLE management_employee")
cursor.execute("DROP TABLE management_attendance")
# etc...

# Then run: python manage.py migrate
```

### If you get "employee" is not defined error
Restart Django server:
```bash
# Kill any running servers
# Then restart
python manage.py runserver
```

### Test Authentication
```bash
# Register new user
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@example.com","password":"pass123","phone":"0300","CNIC":"123","address":"xyz","relative":"rel","r_phone":"0300","r_address":"xyz"}'

# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"pass123"}'
```

## Important Notes

⚠️ **Backward Compatibility**: 
- emp_id format remains the same (EMP0001, EMP0002, etc.)
- API URLs still use emp_id: `/api/employees/EMP001/`
- Old endpoints continue to work

⚠️ **Data Loss Risk**:
- Changing primary keys can cause data loss if not done carefully
- Always backup your database before migrating
- Test in development environment first

⚠️ **Fresh Start Recommended**:
If you're in development, consider:
1. Backing up current db.sqlite3
2. Deleting all migrations except 0001_initial.py
3. Deleting db.sqlite3
4. Running fresh `makemigrations` and `migrate`
5. Re-seeding data with `seed_data.py`

## Verification

After migration, verify:
```bash
# Check if tables exist
python manage.py dbshell
.tables

# Check if auth system works
python manage.py createsuperuser  # Optional

# Start server and test endpoints
python manage.py runserver
# Visit: http://localhost:8000/api/
```

---
**Version**: Updated for Auth + Auto emp_id  
**Last Updated**: April 6, 2026

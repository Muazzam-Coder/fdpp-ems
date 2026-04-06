# FDPP Employee Management System (EMS) - API Documentation

## Overview
This is a comprehensive Employee Management System built with Django REST Framework that tracks employee attendance, shifts, leave management, and salary calculations.

## Features

### 1. **Employee Management**
- Create, update, and manage employee records
- Shift type and timing management
- Emergency contact information
- Profile image upload support
- Employee status tracking (active/inactive)

### 2. **Attendance Management**
- Check-in and check-out functionality
- Daily, weekly, monthly attendance reports
- Automatic late detection
- 14-hour work limit per day (enforced)
- Overtime calculation (1.5x pay)

### 3. **Leave Management**
- Multiple leave types (sick, casual, earned, unpaid, maternity)
- Leave approval workflow
- Leave duration calculation
- Leave history tracking

### 4. **Payroll System**
- Hourly payment calculations
- Overtime compensation (1.5x base rate)
- Salary checkout by date range
- Detailed payout reports

### 5. **Shift Management**
- Pre-defined shift configurations
- Custom shift types support
- Shift assignment to employees

---

## API Endpoints

### **BASE URL**: `http://localhost:8000/api/`

---

## **EMPLOYEE ENDPOINTS**

### 1. Get All Employees
```
GET /employees/
```
**Query Parameters:**
- `status`: Filter by status (active, inactive)
- `shift_type`: Filter by shift type

**Response:**
```json
{
    "count": 10,
    "next": null,
    "previous": null,
    "results": [
        {
            "emp_id": "EMP001",
            "name": "John Doe",
            "salary": "50000.00",
            "hourly_rate": "312.50",
            "shift_type": "morning",
            "start_time": "06:00:00",
            "end_time": "14:00:00",
            "status": "active",
            "total_hours_today": 8.5
        }
    ]
}
```

### 2. Create Employee
```
POST /employees/
```
**Request Body:**
```json
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

### 3. Get Employee Details
```
GET /employees/{emp_id}/
```

### 4. Update Employee
```
PUT /employees/{emp_id}/
PATCH /employees/{emp_id}/
```

### 5. Delete Employee
```
DELETE /employees/{emp_id}/
```

### 6. Calculate Payout
```
GET /employees/{emp_id}/calculate_payout/?start_date=2024-01-01&end_date=2024-01-31
```
**Response:**
```json
{
    "employee_id": "EMP001",
    "employee_name": "John Doe",
    "period": "2024-01-01 to 2024-01-31",
    "total_hours": 160,
    "overtime_hours": 20,
    "hourly_rate": "312.50",
    "base_payout": 50000,
    "overtime_payout": 9375,
    "total_payout": 59375
}
```

### 7. Get Attendance Report
```
GET /employees/{emp_id}/attendance_report/?period=month
```
**Query Parameters:**
- `period`: day, week, month (default: month)
- `start_date`: For custom period (YYYY-MM-DD)
- `end_date`: For custom period (YYYY-MM-DD)

**Response:**
```json
{
    "employee_id": "EMP001",
    "employee_name": "John Doe",
    "period": "2024-01-01 to 2024-01-31",
    "total_days_worked": 20,
    "total_hours": 160,
    "on_time": 18,
    "late": 2,
    "attendance_records": [...]
}
```

### 8. Get Active Employees
```
GET /employees/active_employees/
```

### 9. Get Employee Statistics
```
GET /employees/employee_stats/
```
**Response:**
```json
{
    "total_employees": 50,
    "active_employees": 48,
    "inactive_employees": 2,
    "present_today": 45
}
```

---

## **ATTENDANCE ENDPOINTS**

### 1. Get All Attendance Records
```
GET /attendance/
```
**Query Parameters:**
- `employee`: Filter by emp_id
- `date_from`: Start date (YYYY-MM-DD)
- `date_to`: End date (YYYY-MM-DD)
- `status`: Filter by status

### 2. Create Attendance Record
```
POST /attendance/
```
**Request Body:**
```json
{
    "employee": "EMP001",
    "date": "2024-01-15",
    "check_in": "2024-01-15T06:00:00Z",
    "check_out": "2024-01-15T14:30:00Z",
    "status": "on_time"
}
```

### 3. Check-In Employee
```
POST /attendance/check_in/
```
**Request Body:**
```json
{
    "emp_id": "EMP001"
}
```
**Response:**
```json
{
    "message": "Check-in successful",
    "record": {
        "id": 1,
        "employee": "EMP001",
        "date": "2024-01-15",
        "check_in": "2024-01-15T06:00:00Z",
        "status": "on_time"
    }
}
```

### 4. Check-Out Employee
```
POST /attendance/check_out/
```
**Request Body:**
```json
{
    "emp_id": "EMP001"
}
```

### 5. Daily Report
```
GET /attendance/daily_report/?date=2024-01-15
```
**Response:**
```json
{
    "date": "2024-01-15",
    "total_active_employees": 50,
    "present": 45,
    "absent": 5,
    "on_time": 42,
    "late": 3,
    "attendance_details": [...]
}
```

### 6. Weekly Report
```
GET /attendance/weekly_report/
```
**Response:**
```json
{
    "week": "2024-01-08 to 2024-01-14",
    "total_records": 250,
    "total_hours": 2000,
    "late_arrivals": 15,
    "average_hours_per_day": 285.71
}
```

### 7. Monthly Report
```
GET /attendance/monthly_report/?month=1&year=2024
```
**Response:**
```json
{
    "month": "2024-01",
    "total_working_days": 1000,
    "total_hours_worked": 8000,
    "unique_employees": 50,
    "late_arrivals": 60,
    "average_daily_attendance": 20
}
```

---

## **LEAVE MANAGEMENT ENDPOINTS**

### 1. Get All Leave Requests
```
GET /leave/
```

### 2. Create Leave Request
```
POST /leave/
```
**Request Body:**
```json
{
    "employee": "EMP001",
    "leave_type": "sick",
    "start_time": "2024-01-15T00:00:00Z",
    "end_time": "2024-01-17T23:59:59Z",
    "reason": "Medical checkup"
}
```

### 3. Get Pending Approvals
```
GET /leave/pending_approvals/
```
**Response:**
```json
{
    "pending_count": 5,
    "leaves": [...]
}
```

### 4. Approve Leave
```
POST /leave/{id}/approve/
```
**Request Body:**
```json
{
    "approved_by": "Manager Name"
}
```

### 5. Reject Leave
```
POST /leave/{id}/reject/
```

### 6. Get Employee Leaves
```
GET /leave/employee_leaves/?emp_id=EMP001
```

---

## **SHIFT MANAGEMENT ENDPOINTS**

### 1. Get All Shifts
```
GET /shifts/
```
**Response:**
```json
{
    "count": 3,
    "results": [
        {
            "id": 1,
            "name": "Morning Shift",
            "start_time": "06:00:00",
            "end_time": "14:00:00",
            "description": "Early morning shift"
        }
    ]
}
```

### 2. Create Shift
```
POST /shifts/
```
**Request Body:**
```json
{
    "name": "Afternoon Shift",
    "start_time": "14:00:00",
    "end_time": "22:00:00",
    "description": "Afternoon work hours"
}
```

### 3. Update Shift
```
PUT /shifts/{id}/
PATCH /shifts/{id}/
```

### 4. Delete Shift
```
DELETE /shifts/{id}/
```

---

## **Key Features Explained**

### 1. 14-Hour Limit Constraint
- Automatically enforced when checking out
- If an employee works more than 14 hours, the validation will reject the check-out
- Prevents excessive work hours

### 2. Late Arrival Detection
- Automatically detects if employee checked in after their scheduled start time
- Status automatically set to 'late' or 'on_time'
- Reason for lateness can be recorded

### 3. Overtime Calculation
- Hours worked beyond 8 hours are considered overtime
- Overtime compensated at 1.5x the hourly rate
- Calculated automatically in payout

### 4. Employee Filtering
- Filter by status (active/inactive)
- Filter by shift type
- Filter by date range
- Custom period filtering

### 5. Attendance Reporting
- Daily reports with presence/absence count
- Weekly summary with hours and late arrivals
- Monthly analysis with employee breakdown
- Custom date range reports

### 6. Leave Management
- Multiple leave types supported
- Approval workflow
- Leave duration calculation
- Pending leave tracking

---

## **Installation & Setup**

### 1. Install Dependencies
```bash
pip install django djangorestframework django-filter pillow
```

### 2. Apply Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Create Admin User
```bash
python manage.py createsuperuser
```

### 4. Run Development Server
```bash
python manage.py runserver
```

### 5. Access Admin Panel
Visit: `http://localhost:8000/admin/`

### 6. API Root
Visit: `http://localhost:8000/api/`

---

## **Error Responses**

### 400 Bad Request
```json
{
    "error": "Invalid data",
    "details": "Field validation failed"
}
```

### 404 Not Found
```json
{
    "error": "Employee with id EMP999 not found"
}
```

### 409 Conflict
```json
{
    "error": "Already checked in today"
}
```

---

## **Database Models**

### Employee
- emp_id (PK)
- name, profile_img
- salary, hourly_rate
- shift_type, start_time, end_time
- address, phone, CNIC
- relative, r_phone, r_address
- status, date_joined, last_modified

### Attendance
- employee (FK)
- date
- check_in, check_out
- message_late, status
- Properties: total_hours, overtime_hours, is_late

### PaidLeave
- employee (FK)
- leave_type, start_time, end_time
- reason, approved, approved_by
- Property: duration_days

### Shift
- name, start_time, end_time
- description, created_at

---

## **Best Practices**

1. **Always use emp_id** for employee identification in API calls
2. **Date Format**: Use YYYY-MM-DD for dates and ISO 8601 for datetime
3. **Check-in/Check-out**: Must be done daily for attendance tracking
4. **Pagination**: Results are paginated (default 20 per page)
5. **Filtering**: Use query parameters for efficient data retrieval

---

## **Common Use Cases**

### Calculate Monthly Payroll
```
GET /employees/{emp_id}/calculate_payout/?start_date=2024-01-01&end_date=2024-01-31
```

### Track Daily Attendance
```
GET /attendance/daily_report/?date=2024-01-15
```

### Approve Pending Leaves
```
GET /leave/pending_approvals/
POST /leave/{id}/approve/
```

### Get Employee Attendance History
```
GET /employees/{emp_id}/attendance_report/?period=month
```

### Monitor Late Arrivals
```
GET /attendance/monthly_report/?month=1&year=2024
```

---

**Version**: 1.0  
**Last Updated**: 2024  
**Framework**: Django REST Framework 3.14+  
**Python**: 3.8+

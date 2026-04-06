# FDPP-EMS API Usage Examples

This document provides practical examples for using the FDPP Employee Management System API.

---

## Table of Contents
1. [Employee Management](#employee-management)
2. [Attendance Management](#attendance-management)
3. [Leave Management](#leave-management)
4. [Reports & Analytics](#reports--analytics)
5. [Payroll](#payroll)

---

## Employee Management

### Create a New Employee

**Using cURL:**
```bash
curl -X POST http://localhost:8000/api/employees/ \
  -H "Content-Type: application/json" \
  -d '{
    "emp_id": "HR001",
    "name": "Ahmed Hassan",
    "salary": 75000,
    "hourly_rate": 468.75,
    "shift_type": "morning",
    "start_time": "06:00:00",
    "end_time": "14:00:00",
    "address": "123 Business Complex, Lahore",
    "phone": "03001234567",
    "CNIC": "12345-1234567-1",
    "relative": "Fatima Hassan",
    "r_phone": "03009876543",
    "r_address": "Relative Address, Lahore",
    "status": "active"
  }'
```

**Using Python Requests:**
```python
import requests
import json

url = "http://localhost:8000/api/employees/"
data = {
    "emp_id": "HR001",
    "name": "Ahmed Hassan",
    "salary": 75000,
    "hourly_rate": 468.75,
    "shift_type": "morning",
    "start_time": "06:00:00",
    "end_time": "14:00:00",
    "address": "123 Business Complex",
    "phone": "03001234567",
    "CNIC": "12345-1234567-1",
    "relative": "Fatima Hassan",
    "r_phone": "03009876543",
    "r_address": "Relative Address",
    "status": "active"
}

response = requests.post(url, json=data)
print(response.json())
```

**Response (201 Created):**
```json
{
    "emp_id": "HR001",
    "name": "Ahmed Hassan",
    "profile_img": null,
    "salary": "75000.00",
    "hourly_rate": "468.75",
    "shift_type": "morning",
    "start_time": "06:00:00",
    "end_time": "14:00:00",
    "address": "123 Business Complex, Lahore",
    "phone": "03001234567",
    "CNIC": "12345-1234567-1",
    "relative": "Fatima Hassan",
    "r_phone": "03009876543",
    "r_address": "Relative Address, Lahore",
    "status": "active",
    "date_joined": "2024-01-15",
    "last_modified": "2024-01-15T10:30:00Z",
    "total_hours_today": 0
}
```

### List All Employees

**Basic Request:**
```bash
curl http://localhost:8000/api/employees/
```

**Filter by Status:**
```bash
curl "http://localhost:8000/api/employees/?status=active"
```

**Filter by Shift Type:**
```bash
curl "http://localhost:8000/api/employees/?shift_type=morning"
```

**Combined Filters:**
```bash
curl "http://localhost:8000/api/employees/?status=active&shift_type=morning"
```

### Get Single Employee

```bash
curl http://localhost:8000/api/employees/HR001/
```

### Update Employee

**Partial Update (PATCH):**
```bash
curl -X PATCH http://localhost:8000/api/employees/HR001/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "03005555555",
    "hourly_rate": 500
  }'
```

**Full Update (PUT):**
```bash
curl -X PUT http://localhost:8000/api/employees/HR001/ \
  -H "Content-Type: application/json" \
  -d '{
    "emp_id": "HR001",
    "name": "Ahmed Hassan",
    "salary": 80000,
    "hourly_rate": 500,
    "shift_type": "afternoon",
    "start_time": "14:00:00",
    "end_time": "22:00:00",
    "address": "456 New Address",
    "phone": "03005555555",
    "CNIC": "12345-1234567-1",
    "relative": "Fatima Hassan",
    "r_phone": "03009876543",
    "r_address": "Relative Address",
    "status": "active"
  }'
```

### Delete Employee

```bash
curl -X DELETE http://localhost:8000/api/employees/HR001/
```

### Get Employee Statistics

```bash
curl http://localhost:8000/api/employees/employee_stats/
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

### Get Active Employees Only

```bash
curl http://localhost:8000/api/employees/active_employees/
```

---

## Attendance Management

### Check-In Employee

**Request:**
```bash
curl -X POST http://localhost:8000/api/attendance/check_in/ \
  -H "Content-Type: application/json" \
  -d '{"emp_id": "HR001"}'
```

**Successful Response (201):**
```json
{
    "message": "Check-in successful",
    "record": {
        "id": 1,
        "employee": "HR001",
        "employee_name": "Ahmed Hassan",
        "date": "2024-01-15",
        "check_in": "2024-01-15T06:15:00Z",
        "check_out": null,
        "message_late": null,
        "status": "late",
        "total_hours": 0,
        "overtime_hours": 0,
        "is_late": true
    }
}
```

**Error Response (Employee not found):**
```json
{
    "error": "Employee with id HR999 not found"
}
```

**Error Response (Already checked in):**
```json
{
    "error": "Already checked in today",
    "record": { ... }
}
```

### Check-Out Employee

**Request:**
```bash
curl -X POST http://localhost:8000/api/attendance/check_out/ \
  -H "Content-Type: application/json" \
  -d '{"emp_id": "HR001"}'
```

**Successful Response (200):**
```json
{
    "message": "Check-out successful",
    "total_hours": 8.5,
    "record": {
        "id": 1,
        "employee": "HR001",
        "employee_name": "Ahmed Hassan",
        "date": "2024-01-15",
        "check_in": "2024-01-15T06:00:00Z",
        "check_out": "2024-01-15T14:30:00Z",
        "message_late": null,
        "status": "on_time",
        "total_hours": 8.5,
        "overtime_hours": 0.5,
        "is_late": false
    }
}
```

### Get Attendance for a Date Range

```bash
curl "http://localhost:8000/api/attendance/?employee=HR001&date_from=2024-01-01&date_to=2024-01-31"
```

### Get Daily Report

**Today's Report:**
```bash
curl http://localhost:8000/api/attendance/daily_report/
```

**Specific Date:**
```bash
curl "http://localhost:8000/api/attendance/daily_report/?date=2024-01-15"
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
    "attendance_details": [
        {
            "id": 1,
            "employee": "HR001",
            "employee_name": "Ahmed Hassan",
            "date": "2024-01-15",
            "check_in": "2024-01-15T06:00:00Z",
            "check_out": "2024-01-15T14:30:00Z",
            "status": "on_time",
            "total_hours": 8.5,
            "is_late": false
        }
    ]
}
```

### Get Weekly Report

```bash
curl http://localhost:8000/api/attendance/weekly_report/
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

### Get Monthly Report

**Current Month:**
```bash
curl http://localhost:8000/api/attendance/monthly_report/
```

**Specific Month:**
```bash
curl "http://localhost:8000/api/attendance/monthly_report/?month=1&year=2024"
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

## Leave Management

### Create Leave Request

```bash
curl -X POST http://localhost:8000/api/leave/ \
  -H "Content-Type: application/json" \
  -d '{
    "employee": "HR001",
    "leave_type": "sick",
    "start_time": "2024-01-20T00:00:00Z",
    "end_time": "2024-01-22T23:59:59Z",
    "reason": "Medical checkup and rest"
  }'
```

**Response (201):**
```json
{
    "id": 1,
    "employee": "HR001",
    "employee_name": "Ahmed Hassan",
    "leave_type": "sick",
    "start_time": "2024-01-20T00:00:00Z",
    "end_time": "2024-01-22T23:59:59Z",
    "reason": "Medical checkup and rest",
    "approved": false,
    "approved_by": null,
    "duration_days": 3,
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T10:00:00Z"
}
```

### Get All Leaves

```bash
curl http://localhost:8000/api/leave/
```

### Get Pending Leave Approvals

```bash
curl http://localhost:8000/api/leave/pending_approvals/
```

**Response:**
```json
{
    "pending_count": 3,
    "leaves": [
        {
            "id": 1,
            "employee": "HR001",
            "employee_name": "Ahmed Hassan",
            "leave_type": "sick",
            "start_time": "2024-01-20T00:00:00Z",
            "end_time": "2024-01-22T23:59:59Z",
            "reason": "Medical checkup and rest",
            "approved": false,
            "approved_by": null,
            "duration_days": 3
        }
    ]
}
```

### Get Leaves for Specific Employee

```bash
curl "http://localhost:8000/api/leave/employee_leaves/?emp_id=HR001"
```

### Approve Leave Request

```bash
curl -X POST http://localhost:8000/api/leave/1/approve/ \
  -H "Content-Type: application/json" \
  -d '{"approved_by": "Manager Name"}'
```

**Response:**
```json
{
    "message": "Leave approved",
    "leave": {
        "id": 1,
        "approved": true,
        "approved_by": "Manager Name",
        ...
    }
}
```

### Reject Leave Request

```bash
curl -X POST http://localhost:8000/api/leave/1/reject/
```

---

## Reports & Analytics

### Employee Attendance Report

```bash
curl "http://localhost:8000/api/employees/HR001/attendance_report/?period=month"
```

**Parameters:**
- `period=day` - Today only
- `period=week` - Current week
- `period=month` - Current month (default)
- `period=custom&start_date=2024-01-01&end_date=2024-01-31` - Custom range

**Response:**
```json
{
    "employee_id": "HR001",
    "employee_name": "Ahmed Hassan",
    "period": "2024-01-01 to 2024-01-31",
    "total_days_worked": 20,
    "total_hours": 160,
    "on_time": 18,
    "late": 2,
    "attendance_records": [...]
}
```

### Weekly Attendance Statistics

```bash
curl http://localhost:8000/api/attendance/weekly_report/
```

### Monthly Attendance Statistics

```bash
curl "http://localhost:8000/api/attendance/monthly_report/?month=1&year=2024"
```

---

## Payroll

### Calculate Employee Payout

```bash
curl "http://localhost:8000/api/employees/HR001/calculate_payout/?start_date=2024-01-01&end_date=2024-01-31"
```

**Response:**
```json
{
    "employee_id": "HR001",
    "employee_name": "Ahmed Hassan",
    "period": "2024-01-01 to 2024-01-31",
    "total_hours": 168,
    "overtime_hours": 8,
    "hourly_rate": "468.75",
    "base_payout": "78750.00",
    "overtime_payout": "3750.00",
    "total_payout": "82500.00"
}
```

### Calculation Breakdown

For the above example:
- **Hourly Rate**: 468.75
- **Total Hours**: 168 (21 working days × 8 hours)
- **Overtime Hours**: 8 hours
- **Base Payout**: 168 × 468.75 = 78,750
- **Overtime Pay**: 8 × 468.75 × 1.5 = 5,625
- **Total Payout**: 78,750 + 5,625 = **84,375**

---

## Error Handling

### Common Error Responses

**400 Bad Request:**
```json
{
    "error": "Please provide start_date and end_date (YYYY-MM-DD)"
}
```

**404 Not Found:**
```json
{
    "error": "Employee with id HR999 not found"
}
```

**409 Conflict:**
```json
{
    "error": "Work duration cannot exceed 14 hours per shift."
}
```

**422 Unprocessable Entity:**
```json
{
    "error": "End time must be after start time."
}
```

---

## Tips & Best Practices

1. **Use ISO 8601 Format**: Always use `YYYY-MM-DD` for dates and `HH:MM:SS` for times
2. **Check Employee ID First**: Verify employee exists before check-in
3. **Handle Errors Gracefully**: Always check response status codes
4. **Use Filters**: Filter large datasets for better performance
5. **Pagination**: Results are automatically paginated (20 per page)
6. **Backup**: Regularly backup the database

---

## Python Client Example

```python
import requests
from datetime import datetime, timedelta

class EMSClient:
    def __init__(self, base_url="http://localhost:8000/api"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def create_employee(self, emp_data):
        """Create a new employee"""
        response = self.session.post(f"{self.base_url}/employees/", json=emp_data)
        return response.json()
    
    def check_in(self, emp_id):
        """Check in an employee"""
        data = {"emp_id": emp_id}
        response = self.session.post(f"{self.base_url}/attendance/check_in/", json=data)
        return response.json()
    
    def check_out(self, emp_id):
        """Check out an employee"""
        data = {"emp_id": emp_id}
        response = self.session.post(f"{self.base_url}/attendance/check_out/", json=data)
        return response.json()
    
    def get_daily_report(self, date=None):
        """Get daily attendance report"""
        params = {}
        if date:
            params['date'] = date
        response = self.session.get(f"{self.base_url}/attendance/daily_report/", params=params)
        return response.json()
    
    def calculate_payout(self, emp_id, start_date, end_date):
        """Calculate employee payout"""
        params = {
            'start_date': start_date,
            'end_date': end_date
        }
        response = self.session.get(f"{self.base_url}/employees/{emp_id}/calculate_payout/", params=params)
        return response.json()
    
    def get_employee_stats(self):
        """Get overall employee statistics"""
        response = self.session.get(f"{self.base_url}/employees/employee_stats/")
        return response.json()

# Usage Example
if __name__ == "__main__":
    client = EMSClient()
    
    # Check in
    result = client.check_in("HR001")
    print("Check-in:", result)
    
    # Get daily report
    report = client.get_daily_report("2024-01-15")
    print("Daily Report:", report)
    
    # Calculate payout
    payout = client.calculate_payout("HR001", "2024-01-01", "2024-01-31")
    print("Payout:", payout)
```

---

**Version**: 1.0  
**Last Updated**: 2024

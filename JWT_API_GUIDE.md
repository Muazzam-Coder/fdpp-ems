# FDPP Employee Management System (EMS) - JWT Authentication API Guide

## Overview
This is a comprehensive Employee Management System built with Django REST Framework featuring **JWT (JSON Web Token) authentication** for secure API access.

**Version**: 2.0 (JWT Authentication)  
**Framework**: Django REST Framework 3.14+ with djangorestframework-simplejwt  
**Python**: 3.8+

---

## 🔐 Authentication Flow

### 1. User Registration
Register a new user and create an employee profile.

```http
POST /api/auth/register/
Content-Type: application/json

{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "secure_password123",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "03001234567",
    "CNIC": "12345-1234567-1",
    "address": "123 Main Street",
    "relative": "Jane Doe",
    "r_phone": "03009876543",
    "r_address": "456 Side Street",
    "start_time": "09:00:00",
    "end_time": "17:00:00"
}

Response (201 Created):
{
    "message": "User registered successfully",
    "user": {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com"
    },
    "employee_id": "EMP0001"
}
```

---

### 2. Obtain Access & Refresh Tokens
Login with username and password to get JWT tokens.

```http
POST /api/token/
Content-Type: application/json

{
    "username": "john_doe",
    "password": "secure_password123"
}

Response (200 OK):
{
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Token Details:**
- `access`: Short-lived token (expires in 1 hour)
- `refresh`: Long-lived token (expires in 7 days) for refreshing access token

---

### 3. Refresh Access Token
When access token expires, use refresh token to get a new one.

```http
POST /api/token/refresh/
Content-Type: application/json

{
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

Response (200 OK):
{
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

## 📨 Using Access Token

All API requests (except auth endpoints) require **Bearer token** in the Authorization header:

```http
Authorization: Bearer <access_token>
```

### Example Request with JWT:
```http
GET /api/employees/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

Response (200 OK):
{
    "count": 5,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "emp_id": "EMP0001",
            "name": "John Doe",
            "salary": "50000.00",
            ...
        }
    ]
}
```

---

## 🔑 API Endpoints Summary

### Base URL
```
http://localhost:8000/api/
```

### Authentication Endpoints (❌ No Token Required)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/register/` | POST | Register new user |
| `/token/` | POST | Get access & refresh tokens |
| `/token/refresh/` | POST | Refresh access token |

### Employee Endpoints (✅ Token Required)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/employees/` | GET | List all employees |
| `/employees/` | POST | Create employee |
| `/employees/{emp_id}/` | GET | Get employee details |
| `/employees/{emp_id}/` | PUT | Update employee |
| `/employees/{emp_id}/` | DELETE | Delete employee |
| `/employees/{emp_id}/calculate_payout/` | GET | Calculate payout |
| `/employees/{emp_id}/attendance_report/` | GET | Get attendance report |
| `/employees/active_employees/` | GET | List active employees |
| `/employees/employee_stats/` | GET | Get employee statistics |

### Attendance Endpoints (✅ Token Required, except check-in/check-out)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/attendance/` | GET | Token | List attendance records |
| `/attendance/` | POST | Token | Create attendance record |
| `/attendance/check_in/` | POST | ❌ None | Employee check-in |
| `/attendance/check_out/` | POST | ❌ None | Employee check-out |
| `/attendance/daily_report/` | GET | Token | Daily report |
| `/attendance/weekly_report/` | GET | Token | Weekly report |
| `/attendance/monthly_report/` | GET | Token | Monthly report |

### Leave Endpoints (✅ Token Required)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/leave/` | GET | List leave requests |
| `/leave/` | POST | Create leave request |
| `/leave/{id}/approve/` | POST | Approve leave |
| `/leave/{id}/reject/` | POST | Reject leave |
| `/leave/pending_approvals/` | GET | Get pending leaves |
| `/leave/employee_leaves/` | GET | Get employee leaves |

### Shift Endpoints (✅ Token Required)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/shifts/` | GET | List shifts |
| `/shifts/` | POST | Create shift |
| `/shifts/{id}/` | PUT | Update shift |
| `/shifts/{id}/` | DELETE | Delete shift |

---

## 📌 Detailed Endpoint Documentation

### EMPLOYEE ENDPOINTS

#### 1. Get All Employees
```http
GET /api/employees/
Authorization: Bearer <access_token>

Query Parameters:
- status: active | inactive
- shift_type: morning | afternoon | night | flexible
- page: 1 (default)

Response (200 OK):
{
    "count": 10,
    "next": "http://localhost:8000/api/employees/?page=2",
    "previous": null,
    "results": [
        {
            "id": 1,
            "emp_id": "EMP0001",
            "user": 1,
            "username": "muazzam_ali",
            "email": "muazzam@example.com",
            "name": "Muazzam Ali",
            "salary": "75000.00",
            "hourly_rate": "468.75",
            "shift_type": "morning",
            "start_time": "06:00:00",
            "end_time": "14:00:00",
            "status": "active",
            "total_hours_today": 8.5
        }
    ]
}
```

#### 2. Create Employee
```http
POST /api/employees/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "user": 1,
    "name": "John Doe",
    "salary": 65000,
    "hourly_rate": 406.25,
    "shift_type": "afternoon",
    "start_time": "14:00:00",
    "end_time": "22:00:00",
    "address": "456 Park Road",
    "phone": "03005555555",
    "CNIC": "54321-7654321-2",
    "relative": "Ahmed Khan",
    "r_phone": "03008888888",
    "r_address": "Family Address",
    "status": "active"
}

Response (201 Created):
{
    "id": 2,
    "emp_id": "EMP0002",
    "user": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "name": "John Doe",
    ...
}
```

#### 3. Get Employee Details
```http
GET /api/employees/EMP0001/
Authorization: Bearer <access_token>

Response (200 OK):
{
    "id": 1,
    "emp_id": "EMP0001",
    "user": 1,
    "username": "muazzam_ali",
    "name": "Muazzam Ali",
    "salary": "75000.00",
    "hourly_rate": "468.75",
    "shift_type": "morning",
    "start_time": "06:00:00",
    "end_time": "14:00:00",
    "address": "123 Main Street, Lahore",
    "phone": "03001234567",
    "CNIC": "12345-1234567-1",
    "relative": "Fatima Ali",
    "r_phone": "03009876543",
    "r_address": "Relative Address, Lahore",
    "status": "active",
    "date_joined": "2026-04-06",
    "last_modified": "2026-04-06T13:45:00Z",
    "total_hours_today": 8.5
}
```

#### 4. Calculate Payout
```http
GET /api/employees/EMP0001/calculate_payout/?start_date=2026-03-01&end_date=2026-03-31
Authorization: Bearer <access_token>

Response (200 OK):
{
    "employee_id": "EMP0001",
    "employee_name": "Muazzam Ali",
    "period": "2026-03-01 to 2026-03-31",
    "total_hours": 160,
    "hourly_rate": "468.75",
    "total_payout": 74880.0
}
```

#### 5. Get Attendance Report
```http
GET /api/employees/EMP0001/attendance_report/?period=month
Authorization: Bearer <access_token>

Query Parameters:
- period: day | week | month (default: month)
- start_date: YYYY-MM-DD (for custom period)
- end_date: YYYY-MM-DD (for custom period)

Response (200 OK):
{
    "employee_id": "EMP0001",
    "employee_name": "Muazzam Ali",
    "period": "2026-03-01 to 2026-03-31",
    "total_days_worked": 20,
    "total_hours": 160,
    "on_time": 18,
    "late": 2,
    "attendance_records": [...]
}
```

#### 6. Employee Statistics
```http
GET /api/employees/employee_stats/
Authorization: Bearer <access_token>

Response (200 OK):
{
    "total_employees": 50,
    "active_employees": 48,
    "inactive_employees": 2,
    "present_today": 45
}
```

---

### ATTENDANCE ENDPOINTS

#### 1. List All Attendance
```http
GET /api/attendance/
Authorization: Bearer <access_token>

Query Parameters:
- employee: EMP0001
- date_from: 2026-03-01
- date_to: 2026-03-31
- status: on_time | late | absent | on_leave
- page: 1

Response (200 OK):
{
    "count": 150,
    "results": [...]
}
```

#### 2. Check-In (No Token Required ✅)
```http
POST /api/attendance/check_in/
Content-Type: application/json

{
    "emp_id": "EMP0001"
}

Response (201 Created):
{
    "message": "Check-in successful",
    "record": {
        "id": 25,
        "employee": "EMP0001",
        "employee_name": "Muazzam Ali",
        "date": "2026-04-06",
        "check_in": "2026-04-06T06:30:00Z",
        "check_out": null,
        "message_late": "Traffic jam",
        "status": "late",
        "total_hours": 0,
        "is_late": true,
        "created_at": "2026-04-06T06:30:00Z",
        "updated_at": "2026-04-06T06:30:00Z"
    }
}
```

#### 3. Check-Out (No Token Required ✅)
```http
POST /api/attendance/check_out/
Content-Type: application/json

{
    "emp_id": "EMP0001"
}

Response (200 OK):
{
    "message": "Check-out successful",
    "record": {
        "id": 25,
        "employee": "EMP0001",
        "employee_name": "Muazzam Ali",
        "date": "2026-04-06",
        "check_in": "2026-04-06T06:30:00Z",
        "check_out": "2026-04-06T14:45:00Z",
        "message_late": "Traffic jam",
        "status": "late",
        "total_hours": 8.25,
        "is_late": true,
        "created_at": "2026-04-06T06:30:00Z",
        "updated_at": "2026-04-06T14:45:00Z"
    }
}
```

#### 4. Daily Report
```http
GET /api/attendance/daily_report/?date=2026-04-06
Authorization: Bearer <access_token>

Response (200 OK):
{
    "date": "2026-04-06",
    "total_active_employees": 50,
    "present": 45,
    "absent": 5,
    "on_time": 42,
    "late": 3,
    "attendance_details": [...]
}
```

#### 5. Weekly Report
```http
GET /api/attendance/weekly_report/
Authorization: Bearer <access_token>

Response (200 OK):
{
    "week": "2026-03-30 to 2026-04-05",
    "total_records": 250,
    "total_hours": 2000,
    "late_arrivals": 15,
    "average_hours_per_day": 285.71
}
```

#### 6. Monthly Report
```http
GET /api/attendance/monthly_report/?month=4&year=2026
Authorization: Bearer <access_token>

Response (200 OK):
{
    "month": "2026-04",
    "total_working_days": 1000,
    "total_hours_worked": 8000,
    "unique_employees": 50,
    "late_arrivals": 60,
    "average_daily_attendance": 20.0
}
```

---

### LEAVE ENDPOINTS

#### 1. Create Leave Request
```http
POST /api/leave/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "employee": "EMP0001",
    "leave_type": "sick",
    "start_time": "2026-04-10T00:00:00Z",
    "end_time": "2026-04-12T23:59:59Z",
    "reason": "Medical checkup"
}

Response (201 Created):
{
    "id": 1,
    "employee": "EMP0001",
    "employee_name": "Muazzam Ali",
    "leave_type": "sick",
    "start_time": "2026-04-10T00:00:00Z",
    "end_time": "2026-04-12T23:59:59Z",
    "reason": "Medical checkup",
    "approved": false,
    "approved_by": null,
    "duration_days": 3,
    "created_at": "2026-04-06T13:45:00Z",
    "updated_at": "2026-04-06T13:45:00Z"
}
```

#### 2. Approve Leave
```http
POST /api/leave/1/approve/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "approved_by": "Manager Name"
}

Response (200 OK):
{
    "message": "Leave approved successfully",
    "leave": {...}
}
```

#### 3. Get Pending Approvals
```http
GET /api/leave/pending_approvals/
Authorization: Bearer <access_token>

Response (200 OK):
{
    "pending_count": 3,
    "leaves": [...]
}
```

---

### SHIFT ENDPOINTS

#### 1. List All Shifts
```http
GET /api/shifts/
Authorization: Bearer <access_token>

Response (200 OK):
{
    "count": 3,
    "results": [
        {
            "id": 1,
            "name": "Morning Shift",
            "start_time": "06:00:00",
            "end_time": "14:00:00",
            "description": "Early morning shift (6 AM - 2 PM)",
            "created_at": "2026-04-06T13:45:00Z"
        }
    ]
}
```

#### 2. Create Shift
```http
POST /api/shifts/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "name": "Flexible Shift",
    "start_time": "09:00:00",
    "end_time": "17:00:00",
    "description": "Flexible working hours"
}

Response (201 Created):
{
    "id": 4,
    "name": "Flexible Shift",
    "start_time": "09:00:00",
    "end_time": "17:00:00",
    "description": "Flexible working hours",
    "created_at": "2026-04-06T13:45:00Z"
}
```

---

## ⚠️ Error Responses

### 401 Unauthorized (Missing or Invalid Token)
```json
{
    "detail": "Authentication credentials were not provided."
}
```

### 401 Token Expired
```json
{
    "detail": "Given token not valid for any token type",
    "code": "token_not_valid",
    "messages": [
        {
            "token_class": "AccessToken",
            "token_type": "access",
            "message": "Token is invalid or expired"
        }
    ]
}
```

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

## 🔍 cURL Examples

### Register User
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "pass123",
    "first_name": "John",
    "phone": "0300",
    "CNIC": "123",
    "address": "xyz",
    "relative": "rel",
    "r_phone": "0300",
    "r_address": "xyz"
  }'
```

### Get Access Token
```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "pass123"
  }'
```

### Refresh Token
```bash
curl -X POST http://localhost:8000/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "<refresh_token>"}'
```

### Get All Employees (with Token)
```bash
curl -X GET http://localhost:8000/api/employees/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json"
```

### Check-In (No Token)
```bash
curl -X POST http://localhost:8000/api/attendance/check_in/ \
  -H "Content-Type: application/json" \
  -d '{"emp_id": "EMP0001"}'
```

---

## 📱 JavaScript/Fetch Examples

### Register & Get Tokens
```javascript
// Register
const registerResponse = await fetch('http://localhost:8000/api/auth/register/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        username: 'john_doe',
        email: 'john@example.com',
        password: 'pass123',
        first_name: 'John'
    })
});

// Get Access Token
const tokenResponse = await fetch('http://localhost:8000/api/token/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        username: 'john_doe',
        password: 'pass123'
    })
});

const { access, refresh } = await tokenResponse.json();
```

### API Request with Token
```javascript
const response = await fetch('http://localhost:8000/api/employees/', {
    method: 'GET',
    headers: {
        'Authorization': `Bearer ${access}`,
        'Content-Type': 'application/json'
    }
});

const data = await response.json();
```

### Check-In (No Token)
```javascript
const checkinResponse = await fetch('http://localhost:8000/api/attendance/check_in/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ emp_id: 'EMP0001' })
});

const checkinData = await checkinResponse.json();
```

---

## 🔐 Security Notes

1. **Access Token Lifetime**: 1 hour
2. **Refresh Token Lifetime**: 7 days
3.  **Token Refresh**: Automatically rotates refresh tokens
4. **HTTPS Required**: Use HTTPS in production
5. **Token Storage**: Store tokens securely (not in localStorage for sensitive apps)
6. **CORS Enabled**: All origins allowed for development (change in production)

---

## 📋 Best Practices

1. **Always use HTTPS** in production
2. **Store tokens securely** in your application
3. **Refresh tokens** before they expire
4. **Don't share tokens** between users
5. **Logout by discarding** the token (server stateless)
6. **Use Bearer token** format in Authorization header
7. **Handle 401 responses** by refreshing or re-authenticating

---

## Testing Checklist

- [ ] Register new user
- [ ] Get access token
- [ ] Get employee list with token
- [ ] Refresh token
- [ ] Check-in without token
- [ ] Check-out without token
- [ ] Create leave with token
- [ ] Approve leave with token
- [ ] Test with expired token
- [ ] Test with invalid token

---

**Version**: 2.0 (JWT Authentication)  
**Last Updated**: April 6, 2026  
**Status**: ✅ Production Ready

# FDPP EMS - ULTIMATE FLAT-LIST API REFERENCE

This guide provides a separate entry for every single API request possible in the system.

---

## 🔐 1. Authentication & Tokens

### 1.1 Obtain Access Token (Login)
- **URL**: `/api/token/`
- **Method**: `POST`
- **Payload**:
```json
{
  "username": "your_username",
  "password": "your_password"
}
```
- **Response (200 OK)**:
```json
{
  "access": "eyJhbGci...",
  "refresh": "eyJhbGci..."
}
```

### 1.2 Refresh Access Token
- **URL**: `/api/token/refresh/`
- **Method**: `POST`
- **Payload**:
```json
{
  "refresh": "your_refresh_token"
}
```
- **Response (200 OK)**:
```json
{
  "access": "new_access_token"
}
```

### 1.3 User Info & Role Check
- **URL**: `/api/auth/login/`
- **Method**: `POST`
- **Payload**:
```json
{
  "username": "admin",
  "password": "password123"
}
```
- **Response (200 OK)**:
```json
{
  "message": "Login successful",
  "user_id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "role": "admin"
}
```

### 1.4 Create Admin/Manager (Admin Only)
- **URL**: `/api/auth/create_admin_manager/`
- **Method**: `POST`
- **Format**: `multipart/form-data`
- **Payload**:
  - `username` (string)
  - `email` (email)
  - `password` (string, min 8)
  - `first_name` (optional)
  - `last_name` (optional)
  - `role` ("admin" or "manager")
  - `profile_img` (file, optional)
- **Response (201 Created)**:
```json
{
  "message": "User created successfully as manager",
  "user": { "id": 5, "username": "...", "role": "manager" }
}
```

---

## 👥 2. Employee Management

### 2.1 List All Employees
- **URL**: `/api/employees/`
- **Method**: `GET`
- **Query Params**: `status`, `shift_type`, `employee_id`, `employee_name`
- **Response (200 OK)**:
```json
[
  {
    "id": 1, "emp_id": 1, "name": "John Doe", "status": "active", ...
  }
]
```

### 2.2 Create New Employee
- **URL**: `/api/employees/`
- **Method**: `POST`
- **Format**: `multipart/form-data`
- **Payload**:
  - `name`, `salary`, `hourly_rate`, `shift_type`, `start_time`, `end_time`, `address`, `phone`, `CNIC`, `relative`, `r_phone`, `r_address`, `status`, `date_joined`, `profile_img`
- **Response (201 Created)**: Full employee object.

### 2.3 Retrieve Specific Employee
- **URL**: `/api/employees/{emp_id}/`
- **Method**: `GET`
- **Response (200 OK)**: Full employee object.

### 2.4 Update Employee (Full)
- **URL**: `/api/employees/{emp_id}/`
- **Method**: `PUT`
- **Payload**: All employee fields.

### 2.5 Update Employee (Partial)
- **URL**: `/api/employees/{emp_id}/`
- **Method**: `PATCH`
- **Payload**: Any subset of employee fields.

### 2.6 Delete Employee
- **URL**: `/api/employees/{emp_id}/`
- **Method**: `DELETE`
- **Response (204 No Content)**.

### 2.7 Calculate Payout
- **URL**: `/api/employees/{emp_id}/calculate_payout/`
- **Method**: `GET`
- **Query Params**: `start_date` (YYYY-MM-DD), `end_date` (YYYY-MM-DD)
- **Response (200 OK)**:
```json
{
  "employee_id": 1, "total_hours": 160, "total_payout": 75000.0
}
```

### 2.8 Attendance History Report
- **URL**: `/api/employees/{emp_id}/attendance_report/`
- **Method**: `GET`
- **Query Params**: `period` (day|week|month|custom)
- **Response (200 OK)**: List of attendance records + stats.

### 2.9 List Active Employees
- **URL**: `/api/employees/active_employees/`
- **Method**: `GET`
- **Response (200 OK)**: Array of active employees.

### 2.10 Overall Employee Stats
- **URL**: `/api/employees/employee_stats/`
- **Method**: `GET`
- **Response (200 OK)**: `{ "total_employees": 50, "present_today": 45, ... }`

---

## 📅 3. Attendance Management

### 3.1 List All Records
- **URL**: `/api/attendance/`
- **Method**: `GET`
- **Query Params**: `date_from`, `date_to`, `employee`, `status`

### 3.2 Create Manual Record
- **URL**: `/api/attendance/`
- **Method**: `POST`
- **Payload**:
```json
{
  "employee": 1,
  "date": "2026-04-06",
  "check_in_time": "08:00:00",
  "check_out_time": "17:00:00",
  "status": "on_time"
}
```

### 3.3 Retrieve Attendance Record
- **URL**: `/api/attendance/{id}/`
- **Method**: `GET`
- **Response**: Full attendance object.

### 3.4 Update Attendance Record
- **URL**: `/api/attendance/{id}/`
- **Method**: `PUT` or `PATCH`
- **Payload**: Fields to update (date, check_in_time, etc.)

### 3.5 Delete Attendance Record
- **URL**: `/api/attendance/{id}/`
- **Method**: `DELETE`

### 3.6 Auto Attendance (Card Scan Hook)
- **URL**: `/api/attendance/auto_attendance/`
- **Method**: `POST`
- **Payload**: `{ "emp_id": 1 }`
- **Behavior**: Toggles Check-In/Check-Out + Broadcasts to WebSocket.

### 3.7 Daily Attendance Report
- **URL**: `/api/attendance/daily_report/`
- **Method**: `GET`
- **Query Params**: `date` (YYYY-MM-DD, optional)

### 3.8 Weekly Attendance Report
- **URL**: `/api/attendance/weekly_report/`
- **Method**: `GET`

### 3.9 Monthly Attendance Report
- **URL**: `/api/attendance/monthly_report/`
- **Method**: `GET`
- **Query Params**: `month`, `year`

---

## 🏖️ 4. Leave Management

### 4.1 Request Leave
- **URL**: `/api/leave/`
- **Method**: `POST`
- **Payload**: `{ "employee", "leave_type", "start_time", "end_time", "reason" }`

### 4.2 List All Leaves
- **URL**: `/api/leave/`
- **Method**: `GET`

### 4.3 Retrieve Leave Record
- **URL**: `/api/leave/{id}/`
- **Method**: `GET`

### 4.4 Update Leave Record
- **URL**: `/api/leave/{id}/`
- **Method**: `PUT` or `PATCH`

### 4.5 Delete Leave Record
- **URL**: `/api/leave/{id}/`
- **Method**: `DELETE`

### 4.6 Approve Leave
- **URL**: `/api/leave/{id}/approve/`
- **Method**: `POST`
- **Payload**: `{ "approved_by": "Manager Name" }`

### 4.7 Reject Leave
- **URL**: `/api/leave/{id}/reject/`
- **Method**: `POST`

### 4.8 Get Pending Approvals
- **URL**: `/api/leave/pending_approvals/`
- **Method**: `GET`

### 4.9 Get Employee Leaves
- **URL**: `/api/leave/employee_leaves/`
- **Method**: `GET`
- **Query Param**: `emp_id`

---

## 🕒 5. Shift Configuration

### 5.1 List Shifts
- **URL**: `/api/shifts/`
- **Method**: `GET`

### 5.2 Create Shift
- **URL**: `/api/shifts/`
- **Method**: `POST`
- **Payload**: `{ "name", "start_time", "end_time", "description" }`

### 5.3 Retrieve Shift
- **URL**: `/api/shifts/{id}/`
- **Method**: `GET`

### 5.4 Update Shift
- **URL**: `/api/shifts/{id}/`
- **Method**: `PUT`

### 5.5 Delete Shift
- **URL**: `/api/shifts/{id}/`
- **Method**: `DELETE`

---

## 🎛️ 6. Access Level Management

### 6.1 List Access Levels
- **URL**: `/api/access-levels/`
- **Method**: `GET`

### 6.2 Retrieve Access Level
- **URL**: `/api/access-levels/{id}/`
- **Method**: `GET`

### 6.3 Update Access Level (Role)
- **URL**: `/api/access-levels/{id}/`
- **Method**: `PATCH`
- **Payload**: `{ "role": "admin|manager" }`

### 6.4 Delete Access Level
- **URL**: `/api/access-levels/{id}/`
- **Method**: `DELETE`

### 6.5 List Admins
- **URL**: `/api/access-levels/admins/`
- **Method**: `GET`

### 6.6 List Managers
- **URL**: `/api/access-levels/managers/`
- **Method**: `GET`

---

## 🔌 7. WebSocket Events
- **URL**: `ws://172.172.172.160:8000/ws/biometric/`
- **Event Name**: `biometric_attendance`
- **Data Shape**:
```json
{
  "type": "biometric_attendance",
  "data": {
    "emp_id": 1, "employee_name": "...", "action": "check_in|check_out", ...
  }
}
```
---
**End of Exhaustive Reference**

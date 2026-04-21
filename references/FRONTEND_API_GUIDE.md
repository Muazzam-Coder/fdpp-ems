# FDPP EMS - Frontend API Guide

This guide provides all the technical details needed for the UI developer to integrate with the backend.

## 📍 Base URL
```
http://172.172.172.160:8000/api/
```

## 🔐 Authentication (JWT)

### Get access & refresh tokens
`POST /api/token/`
- **Payload**: `{"username": "admin", "password": "password"}`
- **Response**: `{"access": "...", "refresh": "..."}`

### Refresh access token
`POST /api/token/refresh/`
- **Payload**: `{"refresh": "<refresh_token>"}`
- **Response**: `{"access": "..."}`

### Login (User Info & Role)
`POST /api/auth/login/`
- **Payload**: `{"username": "...", "password": "..."}`
- **Response**: `{"user_id": 1, "username": "...", "role": "admin/manager/employee", "emp_id": 10}`

---

## 👥 Employee Management

### List All Employees
`GET /api/employees/`
- **Header**: `Authorization: Bearer <access_token>`
- **Response**: Paginated list of employee objects.

### Create Employee
`POST /api/employees/`
- **Header**: `Authorization: Bearer <access_token>`
- **Format**: `multipart/form-data`
- **Fields**:
  - `name`: String
  - `salary`: Decimal
  - `hourly_rate`: Decimal
  - `shift_type`: String (e.g., "morning")
  - `start_time`: Time (HH:MM:SS)
  - `end_time`: Time (HH:MM:SS)
  - `address`: Text
  - `phone`: String
  - `CNIC`: String (Unique)
  - `relative`: String
  - `r_phone`: String
  - `r_address`: Text
  - `status`: String ("active" or "inactive")
  - `date_joined`: Date (YYYY-MM-DD)
  - `profile_img`: Image File (Optional)

### Update Employee
`PUT /api/employees/{emp_id}/` or `PATCH /api/employees/{emp_id}/`

### Delete Employee
`DELETE /api/employees/{emp_id}/`

---

## 📅 Attendance & Reports

### Auto Attendance (Main Trigger)
`POST /api/attendance/auto_attendance/`
- **Payload**: `{"emp_id": 1}`
- **Response**: Returns if it was a `check_in` or `check_out` and the timestamp.

### Daily Report
`GET /api/attendance/daily_report/?date=2024-04-08`

### Monthly Report
`GET /api/attendance/monthly_report/?month=4&year=2026`

---

## 🔌 WebSocket (Real-time Updates)

To receive real-time attendance notifications, connect to the biometric WebSocket.

### URL
```
ws://172.172.172.160:8000/ws/biometric/
```

### Event Message Received
Whenever someone scans or an attendance is recorded, all clients get this:
```json
{
    "type": "biometric_attendance",
    "data": {
        "emp_id": 10,
        "employee_name": "John Doe",
        "action": "check_in",
        "message": "✅ John Doe checked in on time",
        "profile_img": "http://172.172.172.160:8000/media/profiles/..."
    }
}
```

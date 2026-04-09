# FDPP EMS - Technical API Reference (Frontend)

This document contains the low-level technical details for all backend endpoints.

## 📍 Environment Details
- **Base API URL**: `http://172.172.172.160:8000/api/`
- **WebSocket URL**: `ws://172.172.172.160:8000/ws/biometric/`
- **Auth Scheme**: JWT Bearer Token

---

## 🔐 1. Authentication Endpoints

### Get Tokens (Login)
`POST /api/token/`
- **Payload**:
```json
{ "username": "...", "password": "..." }
```
- **Response (200 OK)**:
```json
{ "access": "<JWT>", "refresh": "<JWT>" }
```

### Refresh Token
`POST /api/token/refresh/`
- **Payload**: `{ "refresh": "<refresh_token>" }`

### Login & Role Check
`POST /api/auth/login/`
- **Purpose**: Get user roles and basic info.
- **Payload**: `{ "username": "...", "password": "..." }`
- **Response**:
```json
{
    "message": "Login successful",
    "user_id": 1,
    "username": "...",
    "email": "...",
    "role": "admin|manager|employee",
    "emp_id": 10 // only for employees
}
```

### Add Admin/Manager (Admin Only)
`POST /api/auth/create_admin_manager/`
- **Payload**:
```json
{
    "username": "...", "email": "...", "password": "...", 
    "first_name": "...", "last_name": "...", "role": "admin|manager",
    "profile_img": (Optional File)
}
```

---

## 👥 2. Employee Management (`/api/employees/`)

### Create Employee
`POST /api/employees/`
- **Format**: `multipart/form-data`
- **Fields**:
  - `name` (String)
  - `salary` (Decimal)
  - `hourly_rate` (Decimal)
  - `shift_type` (String)
  - `start_time` (HH:MM:SS)
  - `end_time` (HH:MM:SS)
  - `address` (Text)
  - `phone` (String)
  - `CNIC` (String - Unique)
  - `relative` (String)
  - `r_phone` (String)
  - `r_address` (Text)
  - `status` (active|inactive)
  - `date_joined` (YYYY-MM-DD)
  - `profile_img` (File)

### Update/Delete
- `PUT /api/employees/{emp_id}/`: Full update.
- `PATCH /api/employees/{emp_id}/`: Partial update.
- `DELETE /api/employees/{emp_id}/`: Permanent removal.

### Analytics Endpoints
- `GET /api/employees/employee_stats/`: Summary stats.
- `GET /api/employees/{emp_id}/calculate_payout/?start_date=...&end_date=...`: Financial calculation.
- `GET /api/employees/{emp_id}/attendance_report/?period=day|week|month`: Performance history.

---

## 📅 3. Attendance Logic (`/api/attendance/`)

### Real-time Real-Time Scan (Main Trigger)
`POST /api/attendance/auto_attendance/`
- **Payload**: `{ "emp_id": 1 }`
- **Behavior**:
  - Automatically detects Check-In or Check-Out.
  - Calculates late time based on shift start.
  - Broadcasts event to all WebSocket clients.

### Reports
- `GET /api/attendance/daily_report/?date=YYYY-MM-DD`
- `GET /api/attendance/weekly_report/`
- `GET /api/attendance/monthly_report/?month=X&year=XXXX`

---

## 🏖️ 4. Leave Management (`/api/leave/`)

### Request Leave
`POST /api/leave/`
- **Payload**:
```json
{
    "employee": <emp_id>,
    "leave_type": "sick|casual|earned|unpaid|maternity",
    "start_time": "ISO_DATETIME",
    "end_time": "ISO_DATETIME",
    "reason": "..."
}
```

### Approve/Reject
- `POST /api/leave/{id}/approve/` (Payload: `{"approved_by": "..."}`)
- `POST /api/leave/{id}/reject/`

---

## 🕒 5. Shift Management (`/api/shifts/`)

### Create/Update Shift
- `POST /api/shifts/`
- `PUT /api/shifts/{id}/`
- **Payload**:
```json
{
    "name": "Evening Shift",
    "start_time": "18:00:00",
    "end_time": "02:00:00",
    "description": "Optional description"
}
```

### List/Delete
- `GET /api/shifts/`: Returns all shifts.
- `DELETE /api/shifts/{id}/`: Remove a shift configuration.

---

## 🔌 6. WebSockets (Biometric Events)

**Channel**: `biometric_device`

### Inbound Message Structure (Received by UI)
```json
{
    "type": "biometric_attendance",
    "data": {
        "message": "...",
        "action": "check_in|check_out",
        "is_late": true|false,
        "emp_id": 10,
        "employee_name": "...",
        "profile_img": "URL",
        "timestamp": "ISO_STRING"
    }
}
```

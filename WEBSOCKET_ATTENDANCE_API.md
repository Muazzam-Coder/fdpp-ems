# WebSocket & Auto-Attendance Endpoints Documentation

## WebSocket Endpoint

### Connection
```
ws://localhost:8000/ws/attendance/
```

### Features
- Real-time attendance notifications
- Employee status checking
- Late arrival detection

### WebSocket Message Format

#### Request (Check Employee Status)
```json
{
    "emp_id": 5,
    "action": "check_attendance"
}
```

#### Response (Attendance Info)
```json
{
    "type": "attendance_info",
    "emp_id": 5,
    "name": "John Doe",
    "profile_picture": "/media/profiles/john_doe.jpg",
    "shift_type": "morning",
    "shift_start": "09:00:00",
    "shift_end": "17:00:00",
    "is_late": false,
    "message": null,
    "last_status": "on_time",
    "timestamp": "2026-04-07T10:30:00.000000Z"
}
```

If late:
```json
{
    "type": "attendance_info",
    "emp_id": 5,
    "name": "John Doe",
    "profile_picture": "/media/profiles/john_doe.jpg",
    "shift_type": "morning",
    "shift_start": "09:00:00",
    "shift_end": "17:00:00",
    "is_late": true,
    "message": "You are 15 minutes late",
    "last_status": "late",
    "timestamp": "2026-04-07T10:30:00.000000Z"
}
```

### Error Response
```json
{
    "type": "error",
    "error": "Employee with ID 999 not found"
}
```

---

## Auto-Attendance Endpoint

### Endpoint
```
POST /api/attendance/auto_attendance/
```

### Purpose
Intelligently handles check-in/check-out based on employee's last attendance state.

### Logic Flow

1. **No record today OR last record has check_out:**
   - Action: ✅ **CHECK-IN**
   - Status: Determined by shift time (early = "on_time", after = "late")
   - Message: Shows minutes late if applicable

2. **Last record has check_in (no check_out) AND < 14 hours:**
   - Action: ✅ **CHECK-OUT**
   - Calculates total hours worked
   - Returns total_hours in response

3. **Last record has check_in AND >= 14 hours:**
   - Action: ✅ **CHECK-IN** (new shift)
   - 14-hour limit enforced
   - Message: Shows minutes late if applicable

### Request Format
```json
{
    "emp_id": 5
}
```

### Response - Check-In Success
```json
{
    "message": "Check-in successful",
    "action": "check_in",
    "is_late": false,
    "late_message": null,
    "record": {
        "id": 45,
        "employee": 5,
        "employee_name": "John Doe",
        "date": "2026-04-07",
        "check_in": "09:30:00",
        "check_out": null,
        "check_in_time": null,
        "check_out_time": null,
        "message_late": null,
        "status": "on_time",
        "total_hours": 0,
        "is_late": false,
        "created_at": "2026-04-07T08:55:23Z",
        "updated_at": "2026-04-07T08:55:23Z"
    }
}
```

### Response - Check-In Late
```json
{
    "message": "Check-in successful",
    "action": "check_in",
    "is_late": true,
    "late_message": "You are 25 minutes late",
    "record": {
        "id": 46,
        "employee": 5,
        "employee_name": "John Doe",
        "date": "2026-04-07",
        "check_in": "09:25:00",
        "check_out": null,
        "check_in_time": null,
        "check_out_time": null,
        "message_late": "You are 25 minutes late",
        "status": "late",
        "total_hours": 0,
        "is_late": true,
        "created_at": "2026-04-07T08:55:23Z",
        "updated_at": "2026-04-07T08:55:23Z"
    }
}
```

### Response - Check-Out Success
```json
{
    "message": "Check-out successful",
    "action": "check_out",
    "total_hours": 8.5,
    "record": {
        "id": 45,
        "employee": 5,
        "employee_name": "John Doe",
        "date": "2026-04-07",
        "check_in": "09:30:00",
        "check_out": "18:00:00",
        "check_in_time": null,
        "check_out_time": null,
        "message_late": null,
        "status": "on_time",
        "total_hours": 8.5,
        "is_late": false,
        "created_at": "2026-04-07T08:55:23Z",
        "updated_at": "2026-04-07T10:00:23Z"
    }
}
```

### Error Responses

**Employee Not Found:**
```json
{
    "error": "Employee with id 999 not found"
}
```
Status: `404 NOT FOUND`

**Missing emp_id:**
```json
{
    "error": "emp_id is required"
}
```
Status: `400 BAD REQUEST`

**14-Hour Limit Exceeded:**
```json
{
    "error": "Cannot check out. Work duration (14.5 hours) exceeds 14-hour limit",
    "duration_hours": 14.5
}
```
Status: `400 BAD REQUEST`

---

## Testing Examples

### Test 1: WebSocket Connection & Check Status
```bash
# Connect to WebSocket
ws://localhost:8000/ws/attendance/

# Send
{"emp_id": 5, "action": "check_attendance"}

# Receive
{
    "type": "attendance_info",
    "emp_id": 5,
    "name": "John Doe",
    "profile_picture": "/media/profiles/john_doe.jpg",
    "shift_type": "morning",
    ...
}
```

### Test 2: Auto Check-In
```bash
POST /api/attendance/auto_attendance/
{
    "emp_id": 5
}

# Response: Check-in successful
```

### Test 3: Auto Check-Out
```bash
# First, check in
POST /api/attendance/auto_attendance/
{
    "emp_id": 5
}

# Then, check out (same emp_id)
POST /api/attendance/auto_attendance/
{
    "emp_id": 5
}

# Response: Check-out successful
```

### Test 4: Late Arrival
```bash
# Check in after shift start time
POST /api/attendance/auto_attendance/
{
    "emp_id": 5
}

# Response will show:
# "is_late": true
# "late_message": "You are 15 minutes late"
```

---

## Running the Server with WebSocket Support

### Using Daphne (Production-ready)
```bash
daphne -b 0.0.0.0 -p 8000 fdpp_ems.asgi:application
```

### Using Django Development Server (Testing)
```bash
python manage.py runserver 0.0.0.0:8000
```

**Note:** The development server has limited WebSocket support. Use Daphne for proper WebSocket functionality.

---

## Key Features

✅ **Automatic State Management**
- Intelligently determines check-in vs check-out
- Enforces 14-hour work limit

✅ **Real-time Notifications**
- WebSocket for live employee status
- Immediate late arrival detection

✅ **late Message Calculation**
- Automatic minute-level late detection
- Shows exact minutes late in message

✅ **Separation of Concerns**
- Date and time sent separately
- Response shows only time (HH:MM:SS format)
- Full datetime stored in database

✅ **Error Handling**
- Clear error messages
- Proper HTTP status codes
- Validation of constraints

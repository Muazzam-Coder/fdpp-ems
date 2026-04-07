# FDPP Employee Management System - Frontend Integration Guide

## 🎯 Quick Overview for UI Developers

This document explains how to integrate the FDPP EMS backend APIs with your frontend application.

---

## 📋 Core Features Available

### 1. **User Authentication**
- User registration with employee profile
- Image upload during registration
- Login with username/password
- JWT token-based authentication

### 2. **Employee Management**
- Create, read, update, delete employees
- Filter employees by shift type, status
- Upload employee profile images
- Track employee attendance

### 3. **Attendance Tracking**
- Check-in/check-out functionality
- Automatic late detection
- Real-time status via WebSocket
- Daily/weekly/monthly attendance reports

### 4. **Shifts Management**
- Predefined shifts: morning, afternoon, night, flexible
- Custom shift types (e.g., "part-time", "early-bird")
- Filter employees by shift

---

## 🔌 API Base URL

```
http://localhost:8000/api/
```

**In production:**
```
https://your-domain.com/api/
```

---

## 🔐 Authentication

### Register New User + Create Employee

```bash
POST /auth/register/
Content-Type: multipart/form-data

Fields (form-data):
- username (required)
- email (required)
- password (required, min 8 chars)
- first_name (optional)
- last_name (optional)
- phone (optional)
- CNIC (required)
- address (optional)
- relative (optional)
- r_phone (optional)
- r_address (optional)
- start_time (optional, format: "HH:MM:SS")
- end_time (optional, format: "HH:MM:SS")
- shift_type (optional)
- profile_img (optional, image file)
```

**Response (201 Created):**
```json
{
    "message": "User registered successfully",
    "user": {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com"
    },
    "employee": {
        "emp_id": 1,
        "name": "John Doe",
        "profile_img": "http://localhost:8000/media/profiles/photo.jpg"
    }
}
```

### Login

```bash
POST /auth/login/

{
    "username": "john_doe",
    "password": "secure_password"
}
```

**Response (200 OK):**
```json
{
    "message": "Login successful",
    "user_id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "emp_id": 1,
    "name": "John Doe",
    "role": "employee"
}
```

### Get JWT Token (for API access)

```bash
POST /token/

{
    "username": "john_doe",
    "password": "secure_password"
}
```

**Response:**
```json
{
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Use access token for subsequent requests:**
```bash
curl -H "Authorization: Bearer <access_token>" http://localhost:8000/api/employees/
```

---

## 👥 Employees

### Get All Employees

```bash
GET /employees/

Query Parameters:
- shift_type=morning          (filter by shift)
- status=active               (filter by status)
- page=1                      (pagination)
```

**Response (200 OK):**
```json
{
    "count": 15,
    "next": "http://localhost:8000/api/employees/?page=2",
    "previous": null,
    "results": [
        {
            "id": 1,
            "emp_id": 1,
            "name": "John Doe",
            "profile_img": "http://localhost:8000/media/profiles/photo.jpg",
            "phone": "03001234567",
            "CNIC": "12345-1234567-1",
            "shift_type": "morning",
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "status": "active",
            "total_hours_today": 8.5
        }
    ]
}
```

### Get Single Employee

```bash
GET /employees/{emp_id}/

Example: /employees/1/
```

### Create Employee

```bash
POST /employees/
Content-Type: multipart/form-data
Authorization: Bearer <token>

Fields:
- emp_id (auto-assigned if not provided)
- name (required)
- phone (required)
- CNIC (required)
- address (required)
- relative (required)
- r_phone (required)
- r_address (required)
- shift_type (optional)
- start_time (required)
- end_time (required)
- status (optional, default: "active")
- profile_img (optional, image file)
```

### Update Employee

```bash
PUT /employees/{emp_id}/
Content-Type: multipart/form-data (for image) or application/json

Example with image:
-F "name=New Name" 
-F "profile_img=@/path/to/photo.jpg"
```

### Delete Employee

```bash
DELETE /employees/{emp_id}/
Authorization: Bearer <token>
```

---

## ⏰ Attendance

### Check-In/Check-Out (Auto)

```bash
POST /attendance/auto_attendance/

{
    "emp_id": 1
}
```

**First scan of day = Check-in**
**Second scan while checked in = Check-out**

**Response (200 OK):**
```json
{
    "message": "Check-in successful",
    "action": "check_in",
    "is_late": false,
    "late_message": null,
    "record": {
        "id": 123,
        "employee": 1,
        "employee_name": "John Doe",
        "date": "2026-04-07",
        "check_in": "09:30:00",
        "check_out": null,
        "status": "on_time",
        "total_hours": 0
    }
}
```

### Get Attendance Report (Per Employee)

```bash
GET /employees/{emp_id}/attendance_report/

Query Parameters:
- period=month              (day, week, month, custom)
- start_date=2026-04-01    (if period=custom)
- end_date=2026-04-07      (if period=custom)
```

**Response:**
```json
{
    "employee_id": 1,
    "employee_name": "John Doe",
    "period": "2026-04-01 to 2026-04-30",
    "total_days_worked": 20,
    "total_hours": 160.5,
    "on_time": 18,
    "late": 2,
    "attendance_records": [
        {
            "date": "2026-04-07",
            "check_in": "09:30:00",
            "check_out": "17:45:00",
            "status": "late",
            "total_hours": 8.25
        }
    ]
}
```

### Daily Attendance Report (All Employees)

```bash
GET /attendance/daily_report/

Query Parameters:
- date=2026-04-07  (optional, defaults to today)
```

---

## 💰 Payroll

### Calculate Payout

```bash
GET /employees/{emp_id}/calculate_payout/

Query Parameters:
- start_date=2026-04-01    (required)
- end_date=2026-04-30      (required)
```

**Response:**
```json
{
    "employee_id": 1,
    "employee_name": "John Doe",
    "period": "2026-04-01 to 2026-04-30",
    "total_hours": 160.5,
    "hourly_rate": 500.00,
    "total_payout": 80250.00
}
```

---

## 🔄 WebSocket (Real-time)

### Connect to WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/attendance/');

ws.onopen = () => {
    console.log('Connected');
    // Send request
    ws.send(JSON.stringify({
        emp_id: 1,
        action: 'check_attendance'
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Employee status:', data);
    // {
    //     type: "attendance_info",
    //     emp_id: 1,
    //     name: "John Doe",
    //     profile_picture: "http://...",
    //     shift_type: "morning",
    //     shift_start: "09:00:00",
    //     is_late: false,
    //     message: null
    // }
};

ws.onerror = (error) => console.error('Error:', error);
```

---

## 📊 Common Frontend Patterns

### Dashboard Example

```javascript
// Get all employees with attendance today
async function getDashboardData() {
    const token = localStorage.getItem('access_token');
    
    const employees = await fetch('http://localhost:8000/api/employees/?status=active', {
        headers: { 'Authorization': `Bearer ${token}` }
    }).then(r => r.json());
    
    const dailyReport = await fetch('http://localhost:8000/api/attendance/daily_report/', {
        headers: { 'Authorization': `Bearer ${token}` }
    }).then(r => r.json());
    
    return { employees, dailyReport };
}
```

### Handle Image Upload

```html
<input type="file" id="profileImg" accept="image/*">
<script>
document.getElementById('profileImg').addEventListener('change', (e) => {
    const file = e.target.files[0];
    const formData = new FormData();
    formData.append('profile_img', file);
    formData.append('name', 'John Doe');
    
    fetch('http://localhost:8000/api/employees/1/', {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
    });
});
</script>
```

### Display Employee Card

```html
<div class="employee-card">
    <img src="{{ employee.profile_img }}" alt="{{ employee.name }}" class="profile-pic">
    <h3>{{ employee.name }}</h3>
    <p>Shift: {{ employee.shift_type }}</p>
    <p>Hours today: {{ employee.total_hours_today }}</p>
</div>
```

---

## ⚙️ Common Query Parameters & Filters

```bash
# Filter employees by multiple criteria
/employees/?shift_type=morning&status=active&page=1

# Attendance with custom date range
/employees/1/attendance_report/?period=custom&start_date=2026-03-01&end_date=2026-03-31

# Daily report for specific date
/attendance/daily_report/?date=2026-04-05
```

---

## 🚨 Error Handling

### Standard Error Responses

**400 Bad Request:**
```json
{
    "field_name": ["Error message"]
}
```

**401 Unauthorized:**
```json
{
    "detail": "Authentication credentials were not provided."
}
```

**404 Not Found:**
```json
{
    "detail": "Not found."
}
```

**500 Server Error:**
```json
{
    "detail": "Internal server error"
}
```

---

## 💡 Best Practices

1. **Always include Authorization header** for protected endpoints
2. **Use multipart/form-data** for file uploads (images)
3. **Handle JWT token expiration** - refresh when needed
4. **Cache employee data** to reduce API calls
5. **Use WebSocket** for real-time attendance feeds
6. **Implement error boundaries** in your UI
7. **Show loading states** during API calls
8. **Validate forms** before submission

---

## 🔧 Setup Checklist for Frontend

- [ ] API Base URL configured correctly
- [ ] JWT token storage implemented (localStorage/sessionStorage)
- [ ] Logo loading states for API calls
- [ ] Error messages displayed to user
- [ ] Image upload form with preview
- [ ] Employee list with filters
- [ ] Attendance report view
- [ ] Real-time WebSocket connection for status
- [ ] Responsive design for mobile
- [ ] Token refresh on expiration

---

## 📱 Example React Integration

```jsx
import { useState, useEffect } from 'react';

function EmployeeList() {
    const [employees, setEmployees] = useState([]);
    const [loading, setLoading] = useState(true);
    const token = localStorage.getItem('access_token');
    
    useEffect(() => {
        fetch('http://localhost:8000/api/employees/', {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(r => r.json())
        .then(data => {
            setEmployees(data.results);
            setLoading(false);
        });
    }, [token]);
    
    if (loading) return <div>Loading...</div>;
    
    return (
        <div className="employee-grid">
            {employees.map(emp => (
                <div key={emp.id} className="employee-card">
                    <img src={emp.profile_img} alt={emp.name} />
                    <h3>{emp.name}</h3>
                    <p>{emp.shift_type} shift</p>
                    <p>Today: {emp.total_hours_today} hours</p>
                </div>
            ))}
        </div>
    );
}

export default EmployeeList;
```

---

## 📞 Support

For backend API issues, check:
1. Server is running: `http://localhost:8000/api/`
2. Token is valid and not expired
3. Check backend logs for errors
4. Verify network connection
5. Check CORS configuration

---

## 🎉 You're Ready!

All endpoints are ready for frontend integration. Start building! 🚀

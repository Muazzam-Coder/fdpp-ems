# JWT Authentication Implementation Summary

## ✅ Completed Changes

### 1. **Installed Dependencies**
```bash
pip install djangorestframework-simplejwt
```

### 2. **Updated settings.py**
- Added `rest_framework_simplejwt` to INSTALLED_APPS
- Updated REST_FRAMEWORK config:
  - Changed authentication to: `JWTAuthentication`
  - Changed default permission to: `IsAuthenticated`
- Added JWT configuration:
  - Access token lifetime: **1 hour**
  - Refresh token lifetime: **7 days**
  - Token rotation: **Enabled**

### 3. **Updated urls.py** (Main)
Added JWT token endpoints:
```python
POST /api/token/          # Get access & refresh tokens
POST /api/token/refresh/  # Refresh access token
```

### 4. **Updated views.py**
- Added `permission_classes = [IsAuthenticated]` to:
  - EmployeeViewSet
  - AttendanceViewSet
  - PaidLeaveViewSet
  - ShiftViewSet

- Allowed public access to check-in/check-out:
  - `@action(detail=False, methods=['post'], permission_classes=[AllowAny])`
  - Can checkin/checkout **without token**

### 5. **Created API Documentation**
- File: `JWT_API_GUIDE.md` (2000+ lines)
- Complete authentication flow
- All endpoints documented with examples
- cURL and JavaScript examples
- Security best practices

---

## 🔓 Public Endpoints (No Token Required)

```
POST /api/auth/register/         # User registration
POST /api/token/                 # Get access & refresh tokens
POST /api/token/refresh/         # Refresh access token
POST /api/attendance/check_in/   # Employee check-in
POST /api/attendance/check_out/  # Employee check-out
```

---

## 🔒 Protected Endpoints (Token Required)

All other endpoints require: `Authorization: Bearer <access_token>`

```
GET/POST /api/employees/
GET /api/employees/EMP001/
GET/POST /api/attendance/
GET /api/attendance/daily_report/
GET /api/attendance/weekly_report/
GET /api/attendance/monthly_report/
GET/POST /api/leave/
POST /api/leave/{id}/approve/
GET/POST /api/shifts/
... and all other endpoints
```

---

## 🔑 Authentication Flow

### Step 1: Register User
```bash
POST /api/auth/register/
{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "pass123",
    "first_name": "John",
    ...
}
→ Returns: emp_id (e.g., EMP0001)
```

### Step 2: Get Access Token
```bash
POST /api/token/
{
    "username": "john_doe",
    "password": "pass123"
}
→ Returns: { "access": "...", "refresh": "..." }
```

### Step 3: Use Access Token
```bash
GET /api/employees/
Authorization: Bearer <access_token>
→ Returns: List of employees
```

### Step 4: Refresh Token (when expired)
```bash
POST /api/token/refresh/
{ "refresh": "<refresh_token>" }
→ Returns: { "access": "<new_access_token>" }
```

---

## 📊 Token Specifications

| Property | Value |
|----------|-------|
| Access Token Lifetime | 1 hour |
| Refresh Token Lifetime | 7 days |
| Algorithm | HS256 |
| Format | JWT (Bearer) |
| Header Type | `Authorization: Bearer <token>` |
| Rotation | Enabled (new refresh token each use) |

---

## 🧪 Quick Test Commands

### 1. Register
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_user",
    "email": "test@example.com",
    "password": "test123",
    "first_name": "Test",
    "phone": "0300",
    "CNIC": "123",
    "address": "xyz",
    "relative": "rel",
    "r_phone": "0300",
    "r_address": "xyz"
  }'
```

### 2. Get Token
```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_user",
    "password": "test123"
  }'
```

### 3. Use Token (Get Employees)
```bash
curl -X GET http://localhost:8000/api/employees/ \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json"
```

### 4. Check-In (No Token)
```bash
curl -X POST http://localhost:8000/api/attendance/check_in/ \
  -H "Content-Type: application/json" \
  -d '{"emp_id": "EMP0001"}'
```

### 5. Refresh Token
```bash
curl -X POST http://localhost:8000/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "<your_refresh_token>"
  }'
```

---

## 🎯 UI Implementation Guide

### Step 1: Setup Frontend Environment
```javascript
const API_BASE = 'http://localhost:8000/api';
let accessToken = null;
let refreshToken = null;
```

### Step 2: Registration
```javascript
async function register(userData) {
    const res = await fetch(`${API_BASE}/auth/register/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData)
    });
    return res.json();
}
```

### Step 3: Login
```javascript
async function login(username, password) {
    const res = await fetch(`${API_BASE}/token/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    accessToken = data.access;
    refreshToken = data.refresh;
    return data;
}
```

### Step 4: API Request Helper
```javascript
async function apiRequest(endpoint, options = {}) {
    const headers = options.headers || {};
    if (accessToken) {
        headers['Authorization'] = `Bearer ${accessToken}`;
    }
    
    const res = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers: { 'Content-Type': 'application/json', ...headers }
    });
    
    if (res.status === 401) {
        // Token expired, refresh it
        await refreshAccessToken();
        return apiRequest(endpoint, options); // Retry
    }
    
    return res.json();
}
```

### Step 5: Refresh Token
```javascript
async function refreshAccessToken() {
    const res = await fetch(`${API_BASE}/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: refreshToken })
    });
    const data = await res.json();
    accessToken = data.access;
}
```

### Step 6: Check-In (No Auth)
```javascript
async function checkIn(empId) {
    const res = await fetch(`${API_BASE}/attendance/check_in/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ emp_id: empId })
    });
    return res.json();
}
```

### Step 7: Get Employees (With Auth)
```javascript
async function getEmployees() {
    return apiRequest('/employees/');
}
```

---

## 🔐 Security Checklist

- [x] JWT authentication implemented
- [x] Access & refresh token structure
- [x] Token expiration configured
- [x] Permission classes added
- [x] Check-in/out as public endpoints
- [x] CORS enabled for dev
- [x] API documentation complete
- [ ] Use HTTPS in production
- [ ] Update CORS to specific origins in production
- [ ] Rotate SECRET_KEY in production
- [ ] Use environment variables for secrets

---

## 📚 Files Modified

1. **settings.py**
   - Added `rest_framework_simplejwt`
   - Updated REST_FRAMEWORK config
   - Added SIMPLE_JWT settings

2. **urls.py** (Main)
   - Added token endpoints
   - Imported TokenObtainPairView, TokenRefreshView

3. **views.py**
   - Added permission_classes to viewsets
   - Added permission override to check-in/out

4. **JWT_API_GUIDE.md** (New)
   - Complete API documentation
   - Authentication flow
   - All endpoints with examples

---

## ✅ Deployment Checklist

- [ ] Update INSTALLED_APPS with `rest_framework_simplejwt`
- [ ] Update REST_FRAMEWORK settings
- [ ] Add JWT configuration to settings.py
- [ ] Update main urls.py with token endpoints
- [ ] Run `python manage.py migrate` (if needed)
- [ ] Test all authentication flows
- [ ] Test public endpoints (check-in/out)
- [ ] Test protected endpoints with token
- [ ] Test token refresh
- [ ] Test token expiration handling
- [ ] Update frontend to use new auth system
- [ ] Test error responses
- [ ] Document for UI team

---

## 🆘 Troubleshooting

### Issue: "Authentication credentials were not provided"
**Solution**: Include `Authorization: Bearer <token>` header

### Issue: "Token is invalid or expired"
**Solution**: Refresh token using `/api/token/refresh/`

### Issue: Check-in returns 401 Unauthorized
**Solution**: Check-in is public! Don't send auth header. Use: `POST /api/attendance/check_in/` without Bearer token

### Issue: "CORS origin not allowed"
**Solution**: Dev environment has CORS enabled. For production, update CORS settings.

---

## 📞 Support

For UI implementation help, refer to:
- **JWT_API_GUIDE.md** - Complete endpoint documentation
- **JavaScript Examples** - Fetch API examples
- **cURL Examples** - Command-line testing

---

**Status**: ✅ JWT Authentication Ready  
**Date**: April 6, 2026  
**Version**: 2.0

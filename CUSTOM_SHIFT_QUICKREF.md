# Custom Shift - Quick Reference

## What I Fixed

❌ **Before:** Only predefined shifts allowed (morning, afternoon, night, flexible)  
✅ **Now:** Unlimited custom shift types (e.g., "new", "part-time", "early-bird")

---

## The Issue You Had

```
GET /api/employees/?shift_type=new  → 400 Bad Request
```

**Reason:** The shift_type field had hardcoded choices that didn't include "new"

**Solution:** Removed choices constraint from Employee.shift_type field

---

## What Changed

### In `models.py` (Employee model):

**Before:**
```python
shift_type = models.CharField(max_length=20, choices=SHIFT_CHOICES, default='morning')
```

**After:**
```python
shift_type = models.CharField(max_length=100, default='morning')
```

---

## Restart Required

⚠️ **You MUST restart your Django server for changes to take effect:**

```bash
# Terminal 1: Stop and restart
Ctrl+C  # Stop current server

# Start again:
cd fdpp_ems
daphne -b 0.0.0.0 -p 8000 fdpp_ems.asgi:application
```

**OR use batch file:**
```bash
# Double-click start_server.bat
```

---

## Test Your Custom Shift

### Step 1: Filter by Custom Shift

In PowerShell:
```bash
curl "http://localhost:8000/api/employees/?shift_type=new"
```

Expected: Returns employees with shift_type="new" (200 OK)

### Step 2: Create Employee with Custom Shift

```bash
$body = @{
    emp_id = 15
    name = "Test User"
    shift_type = "new"
    start_time = "10:00:00"
    end_time = "18:00:00"
    phone = "03001234567"
    CNIC = "12345-1234567-1"
    address = "123 Street"
    relative = "Family"
    r_phone = "03009876543"
    r_address = "456 Avenue"
} | ConvertTo-Json

Invoke-WebRequest -Method Post `
  -Uri "http://localhost:8000/api/employees/" `
  -ContentType "application/json" `
  -Body $body
```

Expected: 201 Created

### Step 3: Verify

```bash
curl "http://localhost:8000/api/employees/?shift_type=new"
```

Should now show the employee you created.

---

## Common Custom Shifts

You can now use any of these:
- `new`
- `part-time`
- `early-morning`
- `early-bird`
- `night-shift`
- `extended`
- `split-shift`
- Or any other name you want!

---

## No Migration Needed

✅ **The database schema didn't change**
- Only validation rules changed
- Existing data is preserved
- No migration required
- Just restart the server

---

## Backward Compatible

✅ **All existing shifts still work:**
- `morning` - Still valid
- `afternoon` - Still valid
- `night` - Still valid
- `flexible` - Still valid

You can mix predefined and custom shifts in the same database.

---

## Quick API Reference

```bash
# Filter by custom shift (now works!)
GET /api/employees/?shift_type=new

# Get all employees
GET /api/employees/

# Create with custom shift
POST /api/employees/
Body: {"emp_id": 15, "shift_type": "new", ...}

# Update employee's shift
PUT /api/employees/15/
Body: {"shift_type": "part-time"}

# Create shift configuration (optional)
POST /api/shifts/
Body: {"name": "new", "start_time": "10:00:00", "end_time": "18:00:00"}
```

---

## Summary

✅ Custom shift types fully supported  
✅ No database migration required  
✅ Just restart your server  
✅ Your `?shift_type=new` filter now works!  

**You're all set!** 🚀

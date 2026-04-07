# Custom Shift Types Guide

## Overview

Your FDPP EMS now supports unlimited custom shift types. You can:
- Use simple shift names like "new", "custom_morning", "part-time", etc.
- Filter employees by custom shift types
- Set different start/end times per employee

---

## Method 1: Quick Custom Shift (Simple)

### Create Employee with Custom Shift

```bash
POST /api/employees/
{
    "emp_id": 10,
    "name": "John Doe",
    "shift_type": "new",        # ← Custom shift name
    "start_time": "10:00:00",
    "end_time": "18:00:00",
    "phone": "03001234567",
    "CNIC": "12345-1234567-1",
    "address": "123 Main St",
    "relative": "Jane Doe",
    "r_phone": "03009876543",
    "r_address": "456 Side St"
}
```

### Filter by Custom Shift Type

```bash
GET /api/employees/?shift_type=new
```

**Response:**
```json
[
    {
        "emp_id": 10,
        "name": "John Doe",
        "shift_type": "new",
        "start_time": "10:00:00",
        "end_time": "18:00:00",
        ...
    }
]
```

---

## Method 2: Using Shift Model (Recommended)

For better organization and reusability, use the Shift model:

### Create Shift Configuration

```bash
POST /api/shifts/
{
    "name": "new",
    "start_time": "10:00:00",
    "end_time": "18:00:00",
    "description": "New shift schedule"
}
```

### Get All Shifts

```bash
GET /api/shifts/
```

**Response:**
```json
[
    {
        "id": 1,
        "name": "morning",
        "start_time": "09:00:00",
        "end_time": "17:00:00",
        "description": "Morning shift"
    },
    {
        "id": 2,
        "name": "new",
        "start_time": "10:00:00",
        "end_time": "18:00:00",
        "description": "New shift schedule"
    }
]
```

### Assign Employee to Shift

```bash
POST /api/employees/
{
    "emp_id": 10,
    "name": "John Doe",
    "shift_type": "new",  # ← References the "new" shift created above
    "start_time": "10:00:00",
    "end_time": "18:00:00",
    ...
}
```

---

## Custom Shift Examples

### Example 1: Part-Time Shift

```bash
POST /api/shifts/
{
    "name": "part-time",
    "start_time": "14:00:00",
    "end_time": "18:00:00",
    "description": "Part-time afternoon shift"
}
```

Then assign employees:
```bash
POST /api/employees/
{
    "shift_type": "part-time",
    ...
}
```

### Example 2: Extended Shift

```bash
POST /api/shifts/
{
    "name": "extended",
    "start_time": "08:00:00",
    "end_time": "20:00:00",
    "description": "Extended working hours"
}
```

### Example 3: Split Shift

```bash
POST /api/shifts/
{
    "name": "split-shift",
    "start_time": "09:00:00",
    "end_time": "14:00:00",
    "description": "Morning portion of split shift"
}
```

---

## Predefined Shifts (Still Available)

These standard shifts still work:
- `morning` - (6 AM - 2 PM)
- `afternoon` - (2 PM - 10 PM)
- `night` - (10 PM - 6 AM)
- `flexible` - (Custom times per employee)

---

## Filter Employees by Shift Type

### Get All "new" Shift Employees

```bash
GET /api/employees/?shift_type=new
```

### Get All "part-time" Shift Employees

```bash
GET /api/employees/?shift_type=part-time
```

### Get All Active Employees with Custom Shift

```bash
GET /api/employees/?shift_type=new&status=active
```

---

## Database Operations

### Check Custom Shifts in Database

```bash
python manage.py shell
```

```python
from management.models import Employee, Shift

# Get all employees with custom shift "new"
new_shift_employees = Employee.objects.filter(shift_type='new')
for emp in new_shift_employees:
    print(f"{emp.name} - {emp.shift_type} ({emp.start_time} - {emp.end_time})")

# Get all available shifts
shifts = Shift.objects.all()
for shift in shifts:
    print(f"{shift.name}: {shift.start_time} - {shift.end_time}")
    
# Count employees by shift type
from django.db.models import Count
shift_counts = Employee.objects.values('shift_type').annotate(count=Count('id'))
for item in shift_counts:
    print(f"{item['shift_type']}: {item['count']} employees")
```

---

## API Endpoints Summary

| Method | Endpoint | Use Case |
|--------|----------|----------|
| `GET` | `/api/employees/` | Get all employees |
| `GET` | `/api/employees/?shift_type=new` | Filter by custom shift |
| `POST` | `/api/employees/` | Create employee with custom shift |
| `GET` | `/api/shifts/` | Get all shift configurations |
| `POST` | `/api/shifts/` | Create new shift configuration |
| `GET` | `/api/shifts/{id}/` | Get specific shift details |
| `PUT` | `/api/employees/{emp_id}/` | Update employee shift |

---

## Important Notes

⚠️ **Key Points:**

1. **Custom shifts don't have validation** - You can use any shift_type name (ensure start_time < end_time is checked elsewhere)

2. **Late detection uses start_time** - The late arrival calculation compares current time with Employee.start_time

3. **Shift Model is optional** - You can create custom shifts without creating Shift records, but using Shift model is recommended for consistency

4. **Migration not needed** - The change to allow custom shifts doesn't require a Django migration since:
   - The field already exists
   - It just removes the hardcoded choices
   - Existing data is preserved

---

## Example Workflow

### Step 1: Create Shift Configuration (Optional but Recommended)

```bash
POST /api/shifts/
{
    "name": "new",
    "start_time": "10:00:00",
    "end_time": "18:00:00",
    "description": "New shift - 10 AM to 6 PM"
}
```

### Step 2: Create Employee with Custom Shift

```bash
POST /api/employees/
{
    "emp_id": 10,
    "name": "Alice Johnson",
    "shift_type": "new",
    "start_time": "10:00:00",
    "end_time": "18:00:00",
    "status": "active",
    "phone": "03001234567",
    "CNIC": "99999-9999999-9",
    "address": "123 New Street",
    "relative": "Bob Johnson",
    "r_phone": "03009876543",
    "r_address": "456 Family Ave"
}
```

### Step 3: Query by Custom Shift

```bash
GET /api/employees/?shift_type=new
```

Result:
```json
[
    {
        "emp_id": 10,
        "name": "Alice Johnson",
        "shift_type": "new",
        "start_time": "10:00:00",
        "end_time": "18:00:00",
        ...
    }
]
```

### Step 4: Check Attendance with Custom Shift

When Alice scans at 10:15 AM (15 mins late):
```bash
POST /api/attendance/auto_attendance/
{"emp_id": 10}
```

Response:
```json
{
    "message": "Check-in successful",
    "action": "check_in",
    "is_late": true,
    "late_message": "You are 15 minutes late",
    ...
}
```

---

## Troubleshooting

### Error: "Bad Request" when filtering

**Problem:** `GET /api/employees/?shift_type=new` returns 400

**Solution:** 
- Ensure shift_type value exists in database
- Verify the shift_type is spelled correctly
- Check that at least one employee has that shift type

### Custom Shift Not Appearing

**Problem:** Created shift but can't filter by it

**Solution:**
- The Shift model is separate from Employee.shift_type
- You must explicitly create Employee records with that shift_type
- Or create a Shift record for documentation purposes

### Need to Change Custom Shift

**Problem:** Want to rename "new" to "modified"

**Solution:**
```bash
python manage.py shell
```

```python
from management.models import Employee

# Update all employees with old shift to new shift
Employee.objects.filter(shift_type='new').update(shift_type='modified')

# Verify
print(Employee.objects.filter(shift_type='modified').count())
```

---

## Best Practices

✅ **DO:**
- Create Shift records for documentation
- Use descriptive shift names (e.g., "early-morning", "late-evening")
- Keep shift names short and lowercase
- Document what each shift represents

❌ **DON'T:**
- Use very long shift names (>100 chars)
- Use special characters in shift names
- Change shift_type on existing employees without tracking
- Create shift names that conflict with system operations

---

## Support

For issues with custom shifts:
1. Verify shift_type in employee exists
2. Check database: `Employee.objects.filter(shift_type='your_shift').exists()`
3. Ensure API request format is correct
4. Check server logs for detailed errors

---

## Summary

✅ Unlimited custom shift types supported  
✅ Filter employees by any shift name  
✅ Optional Shift model for better organization  
✅ Automatic late detection with custom shifts  
✅ No migration required  

Your custom "new" shift type is now working! 🎉

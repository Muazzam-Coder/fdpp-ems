# Testing Guide - Biometric Integration

## Pre-Testing Checklist

Before testing, ensure:
- [ ] Virtual environment activated
- [ ] All dependencies installed: `pip install pyzk requests`
- [ ] Django server running (Terminal 1)
- [ ] ZK device powered on and connected to network
- [ ] Device IP correct in `biometric_integration.py`
- [ ] Database has test employees (emp_id: 1, 2, 3, etc.)

---

## Test 1: Device Connectivity

### Objective
Verify Python can communicate with ZK K40 device

### Steps

1. Open Python shell:
```bash
cd d:\FDPP attendence
. .\venv\Scripts\Activate.ps1
python
```

2. Run connection test:
```python
from zk import ZK

DEVICE_IP = '172.172.173.234'  # ← Change to your device IP
DEVICE_PORT = 4370

try:
    zk = ZK(DEVICE_IP, port=DEVICE_PORT, timeout=10)
    conn = zk.connect()
    print("✅ Device connection successful!")
    
    # Get device info
    firmware = conn.get_firmware_version()
    print(f"Device firmware: {firmware}")
    
    # Get attendance count
    attendances = conn.get_attendance()
    print(f"Total attendance records: {len(attendances)}")
    
    conn.disconnect()
except Exception as e:
    print(f"❌ Connection failed: {str(e)}")
```

### Expected Result
```
✅ Device connection successful!
Device firmware: 2024.01.15
Total attendance records: 125
```

---

## Test 2: Server API Connectivity

### Objective
Verify Django server API is responding correctly

### Steps

1. Test endpoint is accessible:
```bash
# In PowerShell
curl -X POST http://localhost:8000/api/attendance/auto_attendance/ `
  -H "Content-Type: application/json" `
  -d "{`"emp_id`": 5}"
```

### Expected Result
```json
{
    "message": "Check-in successful",
    "action": "check_in",
    "is_late": false,
    "late_message": null,
    "record": {...}
}
```

---

## Test 3: Manual Check-In via API

### Objective
Test the auto_attendance endpoint with manual API call

### Steps

1. Ensure server is running
2. Open PowerShell and run:

```bash
$body = @{emp_id = 5} | ConvertTo-Json

$response = Invoke-WebRequest -Method Post `
  -Uri "http://localhost:8000/api/attendance/auto_attendance/" `
  -ContentType "application/json" `
  -Body $body

$response.Content | ConvertFrom-Json | ConvertTo-Json
```

### Expected Response
- Status: 200 OK
- Action: "check_in"
- Employee found with name

### Verify in Database
```bash
python manage.py shell
```

```python
from management.models import Attendance
from datetime import date

today = date.today()
att = Attendance.objects.filter(date=today, employee__emp_id=5).first()
print(f"Check-in time: {att.check_in}")
print(f"Status: {att.status}")
print(f"Late message: {att.message_late}")
```

---

## Test 4: Check-Out via API

### Objective
Test check-out functionality

### Steps

1. Employee must already be checked in:
```bash
# Check-in first (if not already done)
$response = Invoke-WebRequest -Method Post `
  -Uri "http://localhost:8000/api/attendance/auto_attendance/" `
  -ContentType "application/json" `
  -Body "{`"emp_id`": 5}" -ErrorAction SilentlyContinue
```

2. Call auto_attendance again (same emp_id):
```bash
$response = Invoke-WebRequest -Method Post `
  -Uri "http://localhost:8000/api/attendance/auto_attendance/" `
  -ContentType "application/json" `
  -Body "{`"emp_id`": 5}"

$response.Content | ConvertFrom-Json | ConvertTo-Json
```

### Expected Response
- Status: 200 OK
- Action: "check_out"
- Total_hours: > 0

---

## Test 5: Biometric Integration Script

### Objective
Test the complete biometric integration script

### Steps

1. Ensure configuration is correct in `biometric_integration.py`:
```python
DEVICE_IP = '172.172.173.234'   # ← Verify this is correct
SERVER_IP = '172.172.173.102'   # ← Verify this is correct
SERVER_PORT = '8000'
```

2. Start the script:
```bash
cd d:\FDPP attendence
. .\venv\Scripts\Activate.ps1
python biometric_integration.py
```

3. Wait for initialization:
```
✅ Successfully connected to ZK K40 device at 172.172.173.234:4370
📊 Initialized with 125 existing records
🔄 Starting Biometric Monitor Loop...
```

4. Have an employee (with emp_id 5) scan fingerprint on device

5. Check output in script terminal - should show:
```
📱 New Biometric Scan - Employee ID: 5, Time: 2026-04-07 09:30:45
✅ John Doe (ID: 5) - CHECK_IN - On time
```

### Verify in Database
```bash
python manage.py shell
```

```python
from management.models import Attendance
from datetime import date

today = date.today()
att = Attendance.objects.filter(
    date=today, 
    employee__emp_id=5
).order_by('-check_in').first()

if att:
    print(f"✅ Attendance record created!")
    print(f"Employee: {att.employee.name}")
    print(f"Check-in: {att.check_in}")
    print(f"Status: {att.status}")
else:
    print("❌ No record found")
```

---

## Test 6: Late Arrival Detection

### Objective
Test that late arrivals are correctly detected

### Precondition
Employee shift starts at 09:00 AM

### Steps

1. Manually create a late check-in (after 09:00):
```bash
$body = @{emp_id = 6} | ConvertTo-Json

$response = Invoke-WebRequest -Method Post `
  -Uri "http://localhost:8000/api/attendance/auto_attendance/" `
  -ContentType "application/json" `
  -Body $body

$json = $response.Content | ConvertFrom-Json
$json.late_message
```

### Expected Output
```
You are X minutes late
```

### Verify Status
```python
from management.models import Attendance
att = Attendance.objects.filter(
    employee__emp_id=6,
    date=date.today()
).first()

print(f"Status: {att.status}")  # Should be "late"
print(f"Message: {att.message_late}")  # Should show minutes
```

---

## Test 7: 14-Hour Limit

### Objective
Verify 14-hour work limit is enforced

### Steps

1. Create a check-in record manually:
```bash
python manage.py shell
```

```python
from management.models import Attendance, Employee
from datetime import datetime, timedelta, date
from django.utils import timezone

emp = Employee.objects.get(emp_id=5)

# Create check-in 14+ hours ago
check_in_time = timezone.now() - timedelta(hours=14, minutes=30)

att = Attendance.objects.create(
    employee=emp,
    date=date.today(),
    check_in=check_in_time,
    status='on_time'
)
print(f"✅ Created check-in: {att.check_in}")
```

2. Try to check out (should fail):
```bash
$response = Invoke-WebRequest -Method Post `
  -Uri "http://localhost:8000/api/attendance/auto_attendance/" `
  -ContentType "application/json" `
  -Body "{`"emp_id`": 5}" -ErrorAction SilentlyContinue

$json = $response.Content | ConvertFrom-Json
$json.error  # Should show limit exceeded message
```

### Expected Error
```
Cannot check out. Work duration (14.5 hours) exceeds 14-hour limit
```

---

## Test 8: Multiple Employees

### Objective
Test handling of multiple employees

### Steps

1. Call API with different emp_ids:
```bash
# Employee 5
Invoke-WebRequest -Method Post `
  -Uri "http://localhost:8000/api/attendance/auto_attendance/" `
  -ContentType "application/json" `
  -Body "{`"emp_id`": 5}"

# Employee 6
Invoke-WebRequest -Method Post `
  -Uri "http://localhost:8000/api/attendance/auto_attendance/" `
  -ContentType "application/json" `
  -Body "{`"emp_id`": 6}"

# Employee 7
Invoke-WebRequest -Method Post `
  -Uri "http://localhost:8000/api/attendance/auto_attendance/" `
  -ContentType "application/json" `
  -Body "{`"emp_id`": 7}"
```

2. Check all records created:
```python
from management.models import Attendance
from datetime import date

today = date.today()
attendances = Attendance.objects.filter(date=today)

for att in attendances:
    print(f"{att.employee.name} - {att.check_in.time()}")
```

### Expected Result
All 3 employees have check-in records

---

## Test 9: Error Handling - Employee Not Found

### Objective
Verify graceful error when employee doesn't exist

### Steps

1. Call API with non-existent emp_id:
```bash
$response = Invoke-WebRequest -Method Post `
  -Uri "http://localhost:8000/api/attendance/auto_attendance/" `
  -ContentType "application/json" `
  -Body "{`"emp_id`": 99999}" -ErrorAction SilentlyContinue

$json = $response.Content | ConvertFrom-Json
$json.error
```

### Expected Result
```
Employee with id 99999 not found
```

---

## Test 10: Logging

### Objective
Verify logs are being written correctly

### Steps

1. Ensure script is running
2. Have multiple employees scan
3. Check log file:

```bash
Get-Content biometric_integration.log -Tail 50
```

### Expected Log Entries
```
2026-04-07 09:00:15 - INFO - ✅ Successfully connected to ZK K40 device
2026-04-07 09:00:16 - INFO - 📊 Initialized with 125 existing records
2026-04-07 09:30:45 - INFO - 📱 New Biometric Scan - Employee ID: 5
2026-04-07 09:30:46 - INFO - ✅ John Doe (ID: 5) - CHECK_IN - On time
2026-04-07 17:45:23 - INFO - 📱 New Biometric Scan - Employee ID: 5
2026-04-07 17:45:24 - INFO - ✅ John Doe (ID: 5) - CHECK_OUT
```

---

## Test 11: Stress Test - Rapid Scans

### Objective
Test system handles multiple rapid scans

### Steps

1. Simulate rapid API calls:
```bash
For ($i=1; $i -le 10; $i++) {
    $body = @{emp_id = (5 + ($i % 3))} | ConvertTo-Json
    $response = Invoke-WebRequest -Method Post `
      -Uri "http://localhost:8000/api/attendance/auto_attendance/" `
      -ContentType "application/json" `
      -Body $body -ErrorAction SilentlyContinue
    Write-Host "Request $i: Success"
    Start-Sleep -Milliseconds 100
}
```

### Expected Result
All requests succeed with proper responses

---

## Test 12: WebSocket Connection

### Objective
Test WebSocket endpoint for real-time status

### Steps

1. Use a WebSocket client or Python script:
```bash
pip install websocket-client
python
```

```python
import websocket
import json

ws = websocket.create_connection("ws://localhost:8000/ws/attendance/")

# Send check attendance request
message = {"emp_id": 5, "action": "check_attendance"}
ws.send(json.dumps(message))

# Receive response
response = ws.recv()
print(json.loads(response))

ws.close()
```

### Expected Response
```json
{
    "type": "attendance_info",
    "emp_id": 5,
    "name": "John Doe",
    "shift_type": "morning",
    "is_late": false,
    "message": null,
    ...
}
```

---

## Complete Testing Sequence

Run tests in this order:

1. ✅ Device Connectivity
2. ✅ Server API Connectivity
3. ✅ Manual Check-In API
4. ✅ Manual Check-Out API
5. ✅ Biometric Script Start
6. ✅ Late Arrival Detection
7. ✅ 14-Hour Limit
8. ✅ Multiple Employees
9. ✅ Error Handling
10. ✅ Logging Verification
11. ✅ Stress Test
12. ✅ WebSocket Test

---

## Troubleshooting During Tests

### Test Fails: Device Connection
**Problem:** Cannot connect to ZK device  
**Solution:**
- Verify device IP with: `ping 172.172.173.234`
- Check device is powered on
- Verify correct port 4370
- Check firewall settings

### Test Fails: Server Connection
**Problem:** Cannot reach Django server  
**Solution:**
- Verify server is running in Terminal 1
- Check with: `curl http://localhost:8000/`
- Verify correct IP and port in script

### Test Fails: Employee Not Found
**Problem:** emp_id doesn't exist in database  
**Solution:**
- Create test employee first:
```bash
python manage.py shell
from management.models import Employee
emp = Employee.objects.create(emp_id=5, name="Test User", ...)
```

### Test Fails: Biometric Script Stops
**Problem:** Script crashes or disconnects  
**Solution:**
- Check logs: `Get-Content biometric_integration.log`
- Restart with: `python biometric_integration.py`
- Verify network stability

---

## Test Results Template

Use this template to document your testing:

```
Test Date: _______________
Tester: ___________________

Test 1 - Device Connectivity: ☐ PASS ☐ FAIL
Test 2 - Server Connection: ☐ PASS ☐ FAIL
Test 3 - Manual Check-In: ☐ PASS ☐ FAIL
Test 4 - Manual Check-Out: ☐ PASS ☐ FAIL
Test 5 - Biometric Script: ☐ PASS ☐ FAIL
Test 6 - Late Detection: ☐ PASS ☐ FAIL
Test 7 - 14-Hour Limit: ☐ PASS ☐ FAIL
Test 8 - Multiple Employees: ☐ PASS ☐ FAIL
Test 9 - Error Handling: ☐ PASS ☐ FAIL
Test 10 - Logging: ☐ PASS ☐ FAIL
Test 11 - Stress Test: ☐ PASS ☐ FAIL
Test 12 - WebSocket: ☐ PASS ☐ FAIL

Overall Result: ☐ PASS ☐ FAIL

Issues Found:
_________________________________
_________________________________

Notes:
_________________________________
_________________________________
```

---

## Success Criteria

System is ready for production when:
- ✅ All 12 tests pass
- ✅ No errors in logs
- ✅ Database records are accurate
- ✅ Late detection works correctly
- ✅ Script runs continuously without crashing
- ✅ Multiple employees processed simultaneously
- ✅ Response times < 500ms

**Congratulations!** Your biometric integration is production-ready! 🎉

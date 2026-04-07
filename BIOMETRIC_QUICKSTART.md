# FDPP EMS - Biometric Integration Quick Start

## What This Does

This system automatically tracks employee attendance using a ZK K40 biometric device (fingerprint scanner).

**Flow:**
```
Employee scans fingerprint → Device → Python script → Server → Attendance created ✅
```

---

## Files You Need

### 1. **biometric_integration.py**
   - Python script that connects to ZK K40 device
   - Reads employee IDs from fingerprint scans
   - Calls server API to create/update attendance
   - Generates logs automatically

### 2. **start_server.bat** (Windows only)
   - One-click script to start Django server
   - Double-click to run

### 3. **start_biometric.bat** (Windows only)
   - One-click script to start biometric reader
   - Double-click to run

### 4. **BIOMETRIC_SETUP_GUIDE.md**
   - Complete setup instructions
   - Troubleshooting guide
   - Configuration reference

---

## Quick Start (3 Steps)

### Step 1: Open First Command Prompt
```bash
# Option A: Double-click start_server.bat (easiest)
# OR
# Option B: Manually run:
cd d:\FDPP attendence
. .\venv\Scripts\Activate.ps1
cd fdpp_ems
daphne -b 0.0.0.0 -p 8000 fdpp_ems.asgi:application
```

**Expected Output:**
```
Listening on TCP address 0.0.0.0:8000
```

### Step 2: Open Second Command Prompt
```bash
# Option A: Double-click start_biometric.bat (easiest)
# OR
# Option B: Manually run:
cd d:\FDPP attendence
. .\venv\Scripts\Activate.ps1
python biometric_integration.py
```

**Expected Output:**
```
✅ Successfully connected to ZK K40 device at 172.172.173.234:4370
📊 Initialized with 125 existing records
🔄 Starting Biometric Monitor Loop...
```

### Step 3: Done!
- Employee scans fingerprint on device
- Server automatically logs attendance
- Check database for records

---

## What Happens Behind the Scenes

1. **Employee scans fingerprint**
   - Device beeps or shows "✅ OK"

2. **Python script detects the scan**
   - Reads employee ID from device
   - Example: "Employee 5 scanned at 09:30"

3. **Script sends to server**
   ```json
   POST /api/attendance/auto_attendance/
   {"emp_id": 5}
   ```

4. **Server processes automatically**
   - **If first time today:** Creates CHECK-IN record
   - **If already checked in:** Creates CHECK-OUT record
   - **Detects if late:** Calculates minutes late
   - **Enforces 14-hour limit:** Prevents overtime abuse

5. **Result saved to database**
   - Attendance record created/updated
   - Employee can view their log

---

## Configuration

### Edit Device IP (IMPORTANT)

1. Check what IP your ZK K40 device has
2. Edit `biometric_integration.py`
3. Find "DEVICE_IP" on line 11
4. Change to your device's IP

```python
# Line 11 - Change this to your device IP
DEVICE_IP = '172.172.173.234'  # ← Your device IP here
```

### Edit Server IP (if different)

If your server is on a different computer:

```python
# Line 16 - Change to your server IP
SERVER_IP = '172.172.173.102'  # ← Your server IP here
```

---

## Checking Logs

Logs are automatically saved to: `biometric_integration.log`

### View logs in PowerShell:
```powershell
Get-Content biometric_integration.log -Tail 20  # Last 20 lines
Get-Content biometric_integration.log  # All logs
```

### View logs in Command Prompt:
```bash
type biometric_integration.log | more
```

### Watch logs in real-time:
```powershell
Get-Content biometric_integration.log -Wait
```

---

## Troubleshooting

### Problem: "Failed to connect to device"
- ✅ Is the ZK device powered on?
- ✅ Is it connected to the network?
- ✅ Is the device IP correct in the script?
- ✅ Can you ping it? `ping 172.172.173.234`

### Problem: "Cannot reach server"
- ✅ Is the Django server running in Terminal 1?
- ✅ Is the server IP correct?
- ✅ Try accessing http://172.172.173.102:8000/ in browser

### Problem: "Employee not found"
- ✅ Does the employee exist in the database?
- ✅ Is the emp_id correct?
- ✅ You can only create attendance for existing employees

### Problem: Connection keeps dropping
- ✅ Check network stability
- ✅ Script will auto-retry (max 5 times)
- ✅ Restart both server and script if needed

---

## Running at Startup (Windows)

To run automatically when computer starts:

1. Create a batch file startup script
2. Place it in Startup folder:
   ```
   C:\Users\YourUsername\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup
   ```

Or use Task Scheduler:
1. Press Win+R, type `taskschd.msc` and press Enter
2. Click "Create Task"
3. Set trigger to "At startup"
4. Set action to run `python biometric_integration.py`

---

## Database Records

After successful scanning, you can check records:

### Check in Database:
```bash
python manage.py shell
```

```python
from management.models import Attendance
from datetime import datetime

today = datetime.now().date()
today_records = Attendance.objects.filter(date=today)

for att in today_records:
    print(f"{att.employee.name}: {att.check_in} - {att.check_out}")
```

### Check via API:
```bash
# Get daily report
curl "http://172.172.173.102:8000/api/attendance/daily_report/"
```

---

## Important Notes

⚠️ **READ THIS:**

1. **Script is NOT automatic** - You must run `start_server.bat` and `start_biometric.bat` manually (or set them to run at startup)

2. **Two terminals required** - Server must run in one terminal, biometric script in another

3. **Configuration is key** - Make sure device IP and server IP are correct

4. **Network connectivity** - Device, script, and server must be on same network

5. **Employees must exist** - Can't create attendance for employees not in database

6. **Employee ID format** - Device must have correct employee ID (emp_id) configured

---

## File Structure

```
d:\FDPP attendence\
├── biometric_integration.py      ← Main script (run this)
├── start_server.bat              ← One-click server start
├── start_biometric.bat           ← One-click biometric start
├── BIOMETRIC_SETUP_GUIDE.md      ← Detailed setup guide
├── biometric_integration.log     ← Auto-generated logs
├── fdpp_ems\
│   ├── manage.py
│   ├── fdpp_ems\
│   │   ├── asgi.py
│   │   ├── settings.py
│   │   └── urls.py
│   └── management\
│       ├── views.py
│       ├── models.py
│       └── serializers.py
└── venv\                         ← Virtual environment
```

---

## Summary

✅ **Dependencies:** pyzk, requests  
✅ **Server:** Terminal 1 with `start_server.bat`  
✅ **Biometric:** Terminal 2 with `start_biometric.bat`  
✅ **Result:** Automatic attendance on fingerprint scan  

**That's it!**

For detailed troubleshooting and advanced configuration, see `BIOMETRIC_SETUP_GUIDE.md`

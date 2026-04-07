# ZK K40 Biometric Integration - Complete Setup Guide

## Overview
This guide explains how to integrate a ZK K40 biometric device with the FDPP Employee Management System for automatic attendance tracking.

### Architecture
```
┌─────────────────────────┐
│   ZK K40 Device         │
│  (Biometric Scanner)    │
└────────────┬────────────┘
             │ (Employee ID)
             │
┌────────────▼────────────┐
│ biometric_integration.py│  ◄── Python Script
│      (This file)        │
└────────────┬────────────┘
             │ (HTTP POST)
             │
┌────────────▼────────────┐
│   Django Server         │
│  /api/attendance/       │
│  auto_attendance/       │
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│   Database              │
│  (Attendance Records)   │
└─────────────────────────┘
```

---

## Prerequisites

### 1. Hardware Requirements
- ✅ ZK K40 Biometric Device
- ✅ Network connection between device and server (same network)
- ✅ Windows/Linux/Mac machine to run the Python script

### 2. Software Requirements
- ✅ Python 3.8+
- ✅ Running Django FDPP EMS server
- ✅ Network connectivity to both device and server

### 3. IP Addresses (Configure These)
```
Device IP:      172.172.173.234    (Your ZK K40 IP - check device display)
Device Port:    4370               (Default ZK port)
Server IP:      172.172.173.102    (Your Django server IP)
Server Port:    8000               (Your Django server port)
```

---

## Installation Steps

### Step 1: Install Python Dependencies

```bash
# Activate virtual environment
cd d:\FDPP attendence
. .\venv\Scripts\Activate.ps1

# Install ZK library and requests
pip install pyzk requests
```

**Install Commands:**
```bash
# For ZK device communication
pip install pyzk

# For HTTP requests
pip install requests

# Both together
pip install pyzk requests
```

### Step 2: Verify Installation
```bash
python -c "from zk import ZK; print('✅ ZK library installed')"
python -c "import requests; print('✅ Requests library installed')"
```

### Step 3: Configure the Script

Edit `biometric_integration.py` and update:

```python
# Line 11-12: Device Configuration
DEVICE_IP = '172.172.173.234'      # ← Change to your device IP
DEVICE_PORT = 4370                 # ← Usually 4370 (don't change)

# Line 16-17: Server Configuration  
SERVER_IP = '172.172.173.102'      # ← Change to your server IP
SERVER_PORT = '8000'               # ← Change if using different port
```

---

## Finding Your Device IP

### Method 1: ZK Device Menu
1. Press Menu on the device
2. Navigate to Settings → Network
3. Look for IP Address display
4. Note down the IP (e.g., 172.172.173.234)

### Method 2: Network Scan
```bash
# Windows
arp -a | findstr /i "zk\|biometric"

# Linux/Mac
arp -a | grep -i zk
```

### Method 3: Check Device Documentation
- Check the device manual or sticker on the device
- Default IP is often printed on the device

---

## Running the System

### Two-Terminal Method (Recommended)

#### Terminal 1: Start Django Server

```bash
cd d:\FDPP attendence
. .\venv\Scripts\Activate.ps1
cd fdpp_ems
daphne -b 0.0.0.0 -p 8000 fdpp_ems.asgi:application
```

**Expected Output:**
```
Listening on TCP address 0.0.0.0:8000
WebSocket support enabled
```

#### Terminal 2: Start Biometric Script

```bash
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

---

## What Happens When Employee Scans

### Sequence of Events

1. **Employee scans fingerprint** on ZK K40 device
   ```
   Device show: "✅ Registered"
   ```

2. **Python script detects scan**
   ```
   📱 New Biometric Scan - Employee ID: 5, Time: 2026-04-07 09:30:00
   ```

3. **Script sends to server**
   ```
   POST http://172.172.173.102:8000/api/attendance/auto_attendance/
   Body: {"emp_id": 5}
   ```

4. **Server processes attendance**
   - If new day or last was "out" → **CHECK-IN**
   - If checked in already → **CHECK-OUT**
   - Detects if late and shows message

5. **Response to script**
   ```json
   {
       "message": "Check-in successful",
       "action": "check_in",
       "is_late": true,
       "late_message": "You are 15 minutes late",
       "record": {...}
   }
   ```

6. **Script logs the result**
   ```
   ⚠️ John Doe (ID: 5) - CHECK_IN - You are 15 minutes late
   ✅ Success logged to biometric_integration.log
   ```

---

## Log File

The script creates a log file: `biometric_integration.log`

### View Logs
```bash
# Windows
type biometric_integration.log

# Linux/Mac
cat biometric_integration.log

# Real-time monitoring
tail -f biometric_integration.log
```

### Example Log Output
```
2026-04-07 09:00:15 - INFO - ✅ Successfully connected to ZK K40 device at 172.172.173.234:4370
2026-04-07 09:00:16 - INFO - 📊 Initialized with 125 existing records
2026-04-07 09:00:17 - INFO - 🔄 Starting Biometric Monitor Loop...
2026-04-07 09:30:45 - INFO - 📱 New Biometric Scan - Employee ID: 5, Time: 2026-04-07 09:30:45
2026-04-07 09:30:46 - INFO - ✅ John Doe (ID: 5) - CHECK_IN - On time
2026-04-07 17:45:23 - INFO - 📱 New Biometric Scan - Employee ID: 5, Time: 2026-04-07 17:45:23
2026-04-07 17:45:24 - INFO - ✅ John Doe (ID: 5) - CHECK_OUT - 8.25 hours worked
```

---

## Automatic Operation

### Does It Run Automatically?

**NO** - The script does NOT run automatically. You need to start it manually.

### To Run Automatically on Startup

#### Option 1: Windows Task Scheduler

1. Click Start → Search "Task Scheduler"
2. Click "Create Task"
3. Name: "FDPP Biometric Integration"
4. Trigger: "At startup"
5. Action: "Start a program"
   - Program: `C:\path\to\venv\Scripts\python.exe`
   - Arguments: `C:\path\to\biometric_integration.py`
6. Check "Run with highest privileges"
7. Click OK

#### Option 2: Windows Batch File

Create `start_biometric.bat`:
```batch
@echo off
cd /d "d:\FDPP attendence"
call venv\Scripts\activate.bat
python biometric_integration.py
pause
```

Place in `Startup` folder:
```
C:\Users\YourUsername\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup
```

#### Option 3: Linux/Mac (Cron Job)

```bash
# Edit crontab
crontab -e

# Add this line (runs at system startup)
@reboot cd /path/to/FDPP\ attendence && . venv/bin/activate && python biometric_integration.py >> biometric_integration.log 2>&1
```

---

## Troubleshooting

### Issue 1: "Failed to connect to device"

**Solution:**
1. Verify device is powered on and connected to network
2. Check if device IP is correct
3. Test connection:
   ```bash
   ping 172.172.173.234
   ```
4. You should see replies (ping working)

### Issue 2: "Cannot reach server"

**Solution:**
1. Verify Django server is running in Terminal 1
2. Check server IP and port are correct
3. Test server connection:
   ```bash
   curl http://172.172.173.102:8000/api/employees/
   ```
4. Should return employee data

### Issue 3: Employee ID not found in database

**Solution:**
1. Make sure employee exists in system
2. Check employee's emp_id is correct
3. You can't create attendance for non-existent employees

### Issue 4: Biometric device IP changes

**Solution:**
1. Set static IP on the ZK device
2. Through device menu: Settings → Network → DHCP: OFF
3. Set fixed IP address

### Issue 5: Script stops/crashes

**Solution:**
1. Check `biometric_integration.log` for errors
2. Script auto-retries on failure
3. If max retries exceeded:
   - Restart both server and script
   - Check network connectivity

---

## Quick Startup Commands

### Terminal 1 - Start Server
```powershell
cd "d:\FDPP attendence"
. .\venv\Scripts\Activate.ps1
cd fdpp_ems
daphne -b 0.0.0.0 -p 8000 fdpp_ems.asgi:application
```

### Terminal 2 - Start Biometric Script
```powershell
cd "d:\FDPP attendence"
. .\venv\Scripts\Activate.ps1
python biometric_integration.py
```

---

## Configuration Summary

| Setting | Value | Location |
|---------|-------|----------|
| Device IP | 172.172.173.234 | Line 11 |
| Device Port | 4370 | Line 12 |
| Server IP | 172.172.173.102 | Line 16 |
| Server Port | 8000 | Line 17 |
| Check Interval | 2 seconds | Line 179 |
| Connection Timeout | 10 seconds | Line 13 |
| Max Retries | 5 attempts | Line 107 |

---

## Advanced Configuration

### Change Check Interval (How often to poll device)

Edit line 179 in `biometric_integration.py`:
```python
time.sleep(2)  # ← Change 2 to any value (in seconds)
```

- Smaller = More responsive but more CPU usage
- Larger = Less responsive but less CPU usage
- **Recommended: 2-5 seconds**

### Change Connection Timeout

Edit line 13:
```python
DEVICE_TIMEOUT = 10  # ← Change to timeout in seconds
```

### Change Log File Location

Edit line 25:
```python
LOG_FILE = 'biometric_integration.log'  # ← Change path
```

---

## Performance Metrics

- **Memory Usage:** ~50-100 MB
- **CPU Usage:** <5% (idle)
- **Network Traffic:** ~100-500 bytes per scan
- **Response Time:** 200-500ms per scan
- **Concurrent Scans:** Handles multiple users at once

---

## Support & Troubleshooting

If encountering issues:

1. **Check logs:** `biometric_integration.log`
2. **Verify connectivity:**
   - Device: `ping 172.172.173.234`
   - Server: `curl http://172.172.173.102:8000/`
3. **Test endpoint manually:**
   ```bash
   curl -X POST http://172.172.173.102:8000/api/attendance/auto_attendance/ \
     -H "Content-Type: application/json" \
     -d "{\"emp_id\": 5}"
   ```

---

## Security Notes

⚠️ **Important:**
- Use HTTPS in production
- Restrict device to network only
- Use firewall to limit access
- Change device default password
- Monitor logs regularly

---

## Summary

✅ **Installation:** Install pyzk and requests  
✅ **Configuration:** Update IP addresses in script  
✅ **Terminal 1:** Start Django server  
✅ **Terminal 2:** Start Python script  
✅ **Result:** Automatic attendance on every fingerprint scan  

Employee scans → Device detects → Script calls API → Attendance created ✨

# Biometric Integration Checklist

## Pre-Setup Checklist

- [ ] ZK K40 device is powered on
- [ ] Device is connected to network (Ethernet or WiFi)
- [ ] You know your device's IP address (check device display)
- [ ] Python 3.8+ is installed
- [ ] Virtual environment is created: `venv`
- [ ] Django server dependencies installed
- [ ] You have admin access to the server

## Installation Checklist

- [ ] Created virtual environment
- [ ] Activated virtual environment
- [ ] Installed Django dependencies
- [ ] Installed pyzk: `pip install pyzk`
- [ ] Installed requests: `pip install requests`
- [ ] Updated DEVICE_IP in biometric_integration.py
- [ ] Updated SERVER_IP in biometric_integration.py (if needed)
- [ ] Verified device IP is reachable: `ping <device_ip>`

## Configuration Checklist

In `biometric_integration.py`:
- [ ] Line 11: DEVICE_IP = correct device IP
- [ ] Line 12: DEVICE_PORT = 4370 (usually correct)
- [ ] Line 16: SERVER_IP = correct server IP
- [ ] Line 17: SERVER_PORT = 8000 (or your port)

## Startup Checklist (Each Time)

### Terminal 1 - Server
- [ ] Open Command Prompt/PowerShell
- [ ] Navigate to project directory
- [ ] Activate virtual environment
- [ ] Run: `cd fdpp_ems && daphne -b 0.0.0.0 -p 8000 fdpp_ems.asgi:application`
- [ ] Verify: "Listening on TCP address 0.0.0.0:8000"
- [ ] **Keep this terminal running**

### Terminal 2 - Biometric Script
- [ ] Open new Command Prompt/PowerShell
- [ ] Navigate to project directory
- [ ] Activate virtual environment
- [ ] Run: `python biometric_integration.py`
- [ ] Verify: "✅ Successfully connected to ZK K40 device"
- [ ] Verify: "🔄 Starting Biometric Monitor Loop..."
- [ ] **Keep this terminal running**

## Testing Checklist

- [ ] Server is running (Terminal 1)
- [ ] Biometric script is running (Terminal 2)
- [ ] ZK device is powered and connected
- [ ] Test: Have an employee scan their fingerprint on device
- [ ] Check logs: Look for success message in Terminal 2
- [ ] Verify: Check database for attendance record
- [ ] Verify: Check if "on_time" or "late" status is correct

## Troubleshooting Checklist

If anything fails:
- [ ] Check `biometric_integration.log` for error messages
- [ ] Verify device is powered on
- [ ] Ping device: `ping <device_ip>`
- [ ] Verify server is running
- [ ] Check server logs for errors
- [ ] Verify correct employee exists in database
- [ ] Verify ZK device is configured with correct employee IDs

## First Run Success Indicators

Server Terminal should show:
```
Listening on TCP address 0.0.0.0:8000
WebSocket support enabled
```

Biometric Terminal should show:
```
✅ Successfully connected to ZK K40 device at 172.172.173.234:4370
📊 Initialized with 125 existing records
🔄 Starting Biometric Monitor Loop...
```

When employee scans:
```
📱 New Biometric Scan - Employee ID: 5, Time: 2026-04-07 09:30:45
✅ John Doe (ID: 5) - CHECK_IN - On time
```

## Daily Use

1. Click `start_server.bat` (or double-click)
2. Click `start_biometric.bat` (or double-click)
3. Leave both running during work hours
4. Employees scan fingerprints normally
5. Attendance is created automatically
6. Stop by pressing Ctrl+C in each terminal

## Common Issues & Solutions

### Device connection fails
- [ ] Check device power
- [ ] Check network cable
- [ ] Verify correct IP in script
- [ ] Restart device
- [ ] Check firewall rules

### Server connection fails
- [ ] Check server is running in Terminal 1
- [ ] Check server IP in script
- [ ] Check firewall on server machine
- [ ] Verify network connectivity

### Employee "not found" error
- [ ] Verify employee exists in database
- [ ] Check employee emp_id is correct
- [ ] Verify ZK device has correct employee ID stored

### No response from device
- [ ] Device might be offline
- [ ] Network connection issue
- [ ] Device IP changed dynamically (set static IP)
- [ ] Device port blocked (usually 4370)

## Need Help?

1. Check `biometric_integration.log`
2. Read `BIOMETRIC_SETUP_GUIDE.md`
3. Read `BIOMETRIC_QUICKSTART.md`
4. Verify all configuration is correct
5. Test connectivity: `ping <device_ip>` and `curl <server_ip>:8000`

---

## You're All Set! ✅

Once you've completed all checklists and confirmed "First Run Success Indicators", your biometric integration is ready to use.

Employees can now scan fingerprints and attendance will be automatically recorded!

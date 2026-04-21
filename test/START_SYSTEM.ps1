# FDPP EMS - Complete System Startup Script
# This script starts all three components:
# 1. Django Server (Daphne ASGI with WebSocket support)
# 2. Biometric Connector (ZK K40 device integration)
# 3. Attendance Interface (WebSocket client - do this in browser)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "FDPP EMS - System Startup Guide" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$VENV_PATH = "d:\FDPP attendence\venv"
$PROJECT_PATH = "d:\FDPP attendence\fdpp_ems"
$SCRIPT_PATH = "d:\FDPP attendence"

Write-Host "System Configuration:" -ForegroundColor Yellow
Write-Host "  Server IP: 172.172.172.160" -ForegroundColor White
Write-Host "  Server Port: 8000" -ForegroundColor White
Write-Host ""

Write-Host "============================================================" -ForegroundColor Green
Write-Host "STEP 1: Start Django Server (Daphne)" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Open a NEW PowerShell terminal and run:" -ForegroundColor Yellow
Write-Host ""
Write-Host "& `"$VENV_PATH\Scripts\Activate.ps1`"" -ForegroundColor Cyan
Write-Host "cd `"$PROJECT_PATH`"" -ForegroundColor Cyan
Write-Host "python -m daphne -b 172.172.172.160 -p 8000 fdpp_ems.asgi:application" -ForegroundColor Cyan
Write-Host ""
Write-Host "✓ Server should show: 'Listening on TCP address 172.172.172.160:8000'" -ForegroundColor Green
Write-Host ""

Write-Host "============================================================" -ForegroundColor Green
Write-Host "STEP 2: Start Biometric Connector (ZK K40 Device)" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Open ANOTHER NEW PowerShell terminal and run:" -ForegroundColor Yellow
Write-Host ""
Write-Host "& `"$VENV_PATH\Scripts\Activate.ps1`"" -ForegroundColor Cyan
Write-Host "cd `"$SCRIPT_PATH`"" -ForegroundColor Cyan
Write-Host "python biometric_websocket.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "✓ Biometric connector should show:" -ForegroundColor Green
Write-Host "  - 'WebSocket connected to ws://172.172.172.160:8000/ws/biometric/'" -ForegroundColor Green
Write-Host "  - '🔄 Starting Biometric Monitor Loop...'" -ForegroundColor Green
Write-Host ""

Write-Host "============================================================" -ForegroundColor Green
Write-Host "STEP 3: Open Attendance Interface (Browser/Dashboard)" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Open your web browser and navigate to:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Dashboard: http://172.172.172.160:8000/admin/" -ForegroundColor Cyan
Write-Host ""
Write-Host "Or use this JavaScript in browser console to connect to WebSocket:" -ForegroundColor Yellow
Write-Host ""
Write-Host "// Connect to Attendance WebSocket (for UI updates)" -ForegroundColor DarkGray
Write-Host "const ws = new WebSocket('ws://172.172.172.160:8000/ws/attendance/');" -ForegroundColor Cyan
Write-Host "ws.onopen = () => console.log('Connected to attendance service');" -ForegroundColor Cyan
Write-Host "ws.onmessage = (e) => {" -ForegroundColor Cyan
Write-Host "  const data = JSON.parse(e.data);" -ForegroundColor Cyan
Write-Host "  console.log('Employee Status:', data);" -ForegroundColor Cyan
Write-Host "};" -ForegroundColor Cyan
Write-Host "// Send query for employee status" -ForegroundColor DarkGray
Write-Host "ws.send(JSON.stringify({emp_id: 1, action: 'check_attendance'}));" -ForegroundColor Cyan
Write-Host ""

Write-Host "============================================================" -ForegroundColor Green
Write-Host "WEBSOCKET ENDPOINTS" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "1. BIOMETRIC CONNECTION (Device -> Server):" -ForegroundColor Yellow
Write-Host "   URL: ws://172.172.172.160:8000/ws/biometric/" -ForegroundColor Cyan
Write-Host "   Purpose: Device sends employee scans in real-time" -ForegroundColor DarkGray
Write-Host "   Message: {emp_id: 1}" -ForegroundColor DarkGray
Write-Host ""
Write-Host "2. ATTENDANCE INTERFACE (UI -> Server):" -ForegroundColor Yellow
Write-Host "   URL: ws://172.172.172.160:8000/ws/attendance/" -ForegroundColor Cyan
Write-Host "   Purpose: Dashboard queries employee status" -ForegroundColor DarkGray
Write-Host "   Message: {emp_id: 1, action: 'check_attendance'}" -ForegroundColor DarkGray
Write-Host ""

Write-Host "============================================================" -ForegroundColor Green
Write-Host "REST API ENDPOINTS" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Login: POST http://172.172.172.160:8000/api/auth/login/" -ForegroundColor Cyan
Write-Host "  Returns: {username, email, first_name, last_name, role}" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Access Levels: GET http://172.172.172.160:8000/api/access-levels/" -ForegroundColor Cyan
Write-Host "  Returns: {username, email, first_name, last_name, role, profile_img}" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Employees: GET http://172.172.172.160:8000/api/employees/" -ForegroundColor Cyan
Write-Host "Auto Attendance: POST http://172.172.172.160:8000/api/attendance/auto_attendance/" -ForegroundColor Cyan
Write-Host "  Payload: {emp_id: 1}" -ForegroundColor DarkGray
Write-Host ""

Write-Host "============================================================" -ForegroundColor Magenta
Write-Host "All Three Components Running Together:" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "✓ Django Server" -ForegroundColor Green
Write-Host "  - Provides REST API for employee management" -ForegroundColor DarkGray
Write-Host "  - WebSocket for biometric device integration" -ForegroundColor DarkGray
Write-Host "  - WebSocket for attendance dashboard updates" -ForegroundColor DarkGray
Write-Host ""
Write-Host "✓ Biometric Connector" -ForegroundColor Green
Write-Host "  - Connects to ZK K40 device at 172.172.173.235:4370" -ForegroundColor DarkGray
Write-Host "  - Polls for new scans every 1 second" -ForegroundColor DarkGray
Write-Host "  - Sends scans to server via WebSocket" -ForegroundColor DarkGray
Write-Host "  - Creates attendance records in real-time" -ForegroundColor DarkGray
Write-Host ""
Write-Host "✓ Attendance Interface" -ForegroundColor Green
Write-Host "  - Connects to WebSocket at ws://172.172.172.160:8000/ws/attendance/" -ForegroundColor DarkGray
Write-Host "  - Queries employee status and shift information" -ForegroundColor DarkGray
Write-Host "  - Receives real-time updates for all employees" -ForegroundColor DarkGray
Write-Host "  - Displays profile pictures, names, check-in/out times" -ForegroundColor DarkGray
Write-Host ""

Write-Host "============================================================" -ForegroundColor Yellow
Write-Host "TROUBLESHOOTING" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "If Django server fails to start:" -ForegroundColor White
Write-Host "  - Run: Get-NetTCPConnection -LocalPort 8000" -ForegroundColor Cyan
Write-Host "  - Kill the process if already running" -ForegroundColor Cyan
Write-Host ""
Write-Host "If Biometric fails to connect:" -ForegroundColor White
Write-Host "  - Check if Django server is running on 172.172.172.160:8000" -ForegroundColor Cyan
Write-Host "  - Check device IP (172.172.173.235) is reachable" -ForegroundColor Cyan
Write-Host "  - View logs in: biometric_websocket.log" -ForegroundColor Cyan
Write-Host ""
Write-Host "If WebSocket connection fails from browser:" -ForegroundColor White
Write-Host "  - Check firewall allows port 8000" -ForegroundColor Cyan
Write-Host "  - Ensure Django server is running" -ForegroundColor Cyan
Write-Host "  - Check browser console for error messages" -ForegroundColor Cyan
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Ready to start? Open 3 PowerShell terminals and follow steps 1-3" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

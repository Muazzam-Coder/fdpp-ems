# FDPP EMS - System Master Documentation

This is the central guide for the FDPP Employee Management System, summarizing all features and system logic.

## 🌟 System Overview
The FDPP EMS is a real-time attendance and employee management platform that handles:
1.  **Employee Administration**: Full lifecycle management of employee data and profiles.
2.  **Smart Attendance**: Automatic check-in/out logic via API or Biometric device.
3.  **Real-Time Dashboard**: Instant updates to all connected UIs via WebSockets.
4.  **Financials**: Automated payout calculations based on hourly rates.
5.  **Leave Workflow**: Submission and approval process for employee leaves.

---

## 🔑 Roles & Permissions
- **Admin**: Full access to all data, reporting, and user creation (including other admins).
- **Manager**: Manage employees, attendance, and leaves. Cannot create other admins.
- **Employee**: Can view their own profile and attendance reports.

---

## 📈 Key System Workflows

### 1. Attendance Logic (Auto-Attendance)
The system uses "Toggle Logic" for the scanner:
- **First Scan**: Creates a `Check-In` record. If late, it marks the status as `Late` and notes the delay.
- **Subsequent Scans**: Updates the `Check-Out` time.
- **Multiple Scans**: Employees can scan multiple times throughout the day (e.g., for breaks). The system intelligently calculates total hours based on the first check-in and last check-out.
- **14-Hour Rule**: An employee cannot work more than 14 hours in a single session.

### 2. Biometric Integration
If the `biometric_websocket.py` script is running, any card scan at the device:
1.  Triggers the backend `auto_attendance` endpoint.
2.  Updates the database.
3.  Broadcasts the event (Name, Photo, Status) to all open dashboards instantly.

### 3. Reporting
Reports are available for:
- **Daily**: Who is present, who is absent, and who was late today.
- **Weekly**: Total aggregate hours and attendance trends.
- [ ] **Monthly**: Detailed breakdown for payroll preparation.

### 4. Shift Management
- **Centralized Config**: Define shift names (e.g., "Morning", "Night", "Overtime") with fixed start and end times.
- **Auto-Late Detection**: The system uses these shift times to determine if an employee is late when they check in.
- **Flexibility**: Managers can create, edit, or delete shifts at any time via the management dashboard.

---

## 🛠 Support & Maintenance
- **Django Admin**: `http://172.172.172.160:8000/admin/` (Full DB access)
- **API Documentation**: Detailed technical specs are in `FRONTEND_API_DOCS.md`.
- **Server Monitoring**: Run via `daphne` to ensure WebSocket support.

---
**Version**: 2.5 (Comprehensive)  
**Main Author**: Antigravity Assistant

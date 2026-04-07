# WebSocket Integration Guide for FDPP EMS

## 🔌 WebSocket Endpoints

Your system now has **2 WebSocket endpoints** for real-time communication:

### 1. **Attendance WebSocket** (For UI/Mobile Apps)
```
ws://localhost:8000/ws/attendance/
```
- Purpose: Real-time employee attendance status
- Used by: Dashboard, Mobile App, Management Portal
- Data: Check current status, late status, shift times

### 2. **Biometric WebSocket** (For Device Integration)
```
ws://localhost:8000/ws/biometric/
```
- Purpose: Real-time biometric device events
- Used by: Biometric Script, Admin Dashboard
- Data: Employee scans, attendance updates

---

## 🚀 Setup Steps

### Step 1: Install WebSocket Library
```bash
pip install websockets
```

### Step 2: Verify Channels Configuration
Channels is already configured in your Django settings. Verify `fdpp_ems/settings.py` has:
```python
INSTALLED_APPS = [
    ...
    'daphne',  # ASGI server
    'channels',  # WebSocket support
    ...
]

ASGI_APPLICATION = 'fdpp_ems.asgi.application'

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}
```

### Step 3: Start Server with Daphne
Instead of `python manage.py runserver`, use:
```bash
cd d:\FDPP attendence\fdpp_ems
daphne -b 0.0.0.0 -p 8000 fdpp_ems.asgi:application
```

### Step 4: Start Biometric Integration
**Option A: Using HTTP (Original Script)**
```bash
python d:\FDPP attendence\biometric_integration.py
```

**Option B: Using WebSocket (Real-time)**
```bash
python d:\FDPP attendence\biometric_websocket.py
```

---

## 📱 Client-Side WebSocket Examples

### JavaScript (Browser)

#### Attendance Status Listener
```javascript
// Connect to attendance WebSocket
const attendanceWS = new WebSocket('ws://localhost:8000/ws/attendance/');

attendanceWS.onopen = () => {
    console.log('Connected to attendance service');
    
    // Request employee attendance info
    attendanceWS.send(JSON.stringify({
        emp_id: 1,
        action: 'check_attendance'
    }));
};

attendanceWS.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Attendance Info:', data);
    
    if (data.type === 'attendance_info') {
        updateEmployeeCard({
            name: data.name,
            shift: data.shift_type,
            isLate: data.is_late,
            message: data.message,
            profileImg: data.profile_picture
        });
    }
};

attendanceWS.onerror = (error) => {
    console.error('WebSocket error:', error);
};

attendanceWS.onclose = () => {
    console.log('Disconnected from attendance service');
};
```

#### Real-time Biometric Event Listener
```javascript
// Connect to biometric WebSocket for real-time updates
const biometricWS = new WebSocket('ws://localhost:8000/ws/biometric/');

biometricWS.onopen = () => {
    console.log('Connected to biometric service');
};

biometricWS.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'biometric_attendance') {
        const attendance = data.data;
        
        // Show notification
        showNotification({
            title: attendance.employee_name,
            message: attendance.message,
            image: attendance.profile_img,
            action: attendance.action
        });
        
        // Update employee list
        updateEmployeeAttendance(attendance.emp_id, {
            lastAction: attendance.action,
            checkIn: attendance.check_in,
            checkOut: attendance.check_out
        });
    }
};

biometricWS.onerror = (error) => {
    console.error('Biometric WebSocket error:', error);
};
```

### React Component Example

```jsx
import { useEffect, useState } from 'react';

function BiometricDashboard() {
    const [employees, setEmployees] = useState([]);
    const [ws, setWs] = useState(null);

    useEffect(() => {
        // Connect to biometric WebSocket
        const biometricWS = new WebSocket('ws://localhost:8000/ws/biometric/');

        biometricWS.onopen = () => {
            console.log('Biometric WebSocket connected');
            setWs(biometricWS);
        };

        biometricWS.onmessage = (event) => {
            const message = JSON.parse(event.data);
            
            if (message.type === 'biometric_attendance') {
                const { emp_id, employee_name, action, message: msg, profile_img } = message.data;

                // Update employee list
                setEmployees(prev => {
                    const existing = prev.find(e => e.emp_id === emp_id);
                    if (existing) {
                        return prev.map(e => 
                            e.emp_id === emp_id 
                                ? { ...e, lastAction: action, statusMessage: msg }
                                : e
                        );
                    }
                    return [...prev, { emp_id, employee_name, lastAction: action, statusMessage: msg, profile_img }];
                });

                // Show toast notification
                showToast(msg, action === 'check_in' ? 'info' : 'success');
            }
        };

        return () => {
            if (biometricWS) biometricWS.close();
        };
    }, []);

    return (
        <div className="dashboard">
            <h1>Real-time Attendance</h1>
            {employees.map(emp => (
                <EmployeeCard key={emp.emp_id} employee={emp} />
            ))}
        </div>
    );
}

export default BiometricDashboard;
```

### Python Client Example

```python
import asyncio
import json
import websockets

async def biometric_listener():
    """Listen to biometric events from server"""
    uri = "ws://localhost:8000/ws/biometric/"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to biometric WebSocket")
            
            while True:
                # Receive messages from server
                message = await websocket.recv()
                data = json.loads(message)
                
                if data.get('type') == 'biometric_attendance':
                    attendance = data.get('data', {})
                    print(f"📱 Scan: {attendance.get('employee_name')} - {attendance.get('message')}")
                    
    except Exception as e:
        print(f"❌ WebSocket error: {e}")

# Run the listener
asyncio.run(biometric_listener())
```

---

## 📊 WebSocket Message Formats

### Connection Confirmation
```json
{
    "type": "connection",
    "message": "Connected to attendance service",
    "timestamp": "2026-04-07T14:30:45.123456Z"
}
```

### Attendance Query
```json
{
    "emp_id": 1,
    "action": "check_attendance"
}
```

### Attendance Response
```json
{
    "type": "attendance_info",
    "emp_id": 1,
    "name": "John Doe",
    "profile_picture": "http://localhost:8000/media/profiles/photo.jpg",
    "shift_type": "morning",
    "shift_start": "09:00:00",
    "shift_end": "17:00:00",
    "is_late": false,
    "message": null,
    "last_status": "on_time",
    "timestamp": "2026-04-07T14:30:45.123456Z"
}
```

### Biometric Scan (from Device)
```json
{
    "emp_id": 1
}
```

### Biometric Success Response
```json
{
    "type": "biometric_success",
    "emp_id": 1,
    "employee_name": "John Doe",
    "action": "check_in",
    "message": "✅ John Doe checked in on time",
    "is_late": false,
    "check_in": "2026-04-07 09:30:45",
    "check_out": null,
    "profile_img": "http://localhost:8000/media/profiles/photo.jpg"
}
```

### Broadcast Event (All Connected Clients)
```json
{
    "type": "biometric_attendance",
    "data": {
        "emp_id": 1,
        "employee_name": "John Doe",
        "action": "check_in",
        "message": "✅ John Doe checked in on time",
        "profile_img": "http://localhost:8000/media/profiles/photo.jpg"
    },
    "timestamp": "2026-04-07T14:30:45.123456Z"
}
```

---

## 🔄 Complete Flow Diagram

```
┌──────────────────────────────────┐
│   ZK K40 Device                  │
│   (Card Scanner)                 │
└────────────┬──────────────────────┘
             │ (scans card)
             ↓
┌──────────────────────────────────────┐
│   Biometric Script                   │
│   (biometric_websocket.py)           │
│   - Reads from device every 1 sec    │
│   - Sends new scans via WebSocket    │
└────────────┬──────────────────────────┘
             │ (sends emp_id)
             ↓
┌──────────────────────────────────────────┐
│   Django Server (Daphne ASGI)            │
│   BiometricConsumer WebSocket Handler    │
│   - Processes attendance                 │
│   - Broadcasts to all connected clients  │
└────────────┬──────────────────────────────┘
             │ (broadcasts event)
    ┌────────┴──────────┐
    ↓                   ↓
┌─────────────────┐  ┌──────────────────┐
│  Admin Dashboard│  │ Mobile App       │
│  (Real-time)    │  │ (Real-time)      │
│  Shows all      │  │ Shows personal   │
│  scans          │  │ attendance       │
└─────────────────┘  └──────────────────┘
```

---

## ⚙️ Configuration for Different Environments

### Development (localhost)
```python
DEVICE_IP = '172.172.173.199'
SERVER_IP = 'localhost'  # or 127.0.0.1
WS_URL = "ws://localhost:8000/ws/biometric/"
```

### Production (Network)
```python
DEVICE_IP = '172.172.173.199'  # Device IP on network
SERVER_IP = '172.172.173.197'  # Server IP on network
WS_URL = "ws://172.172.173.197:8000/ws/biometric/"
```

### With SSL/TLS (wss://)
```python
WS_URL = "wss://your-domain.com/ws/biometric/"
```

---

## 📡 Two Approaches

### ✅ Approach 1: HTTP POST (Original)
```bash
python biometric_integration.py
```
- **Pros**: Simple, stateless, easy to debug
- **Cons**: Polling-based, higher latency, more bandwidth
- **Use Case**: Testing, simple setups

### ⚡ Approach 2: WebSocket (Real-time)
```bash
python biometric_websocket.py
```
- **Pros**: Real-time, persistent connection, lower latency
- **Cons**: Requires Channels, more complex
- **Use Case**: Production, dashboard updates, multiple clients

---

## 🔍 Troubleshooting

### WebSocket Connection Refused
```
Error: Failed to connect to ws://localhost:8000/ws/biometric/
Solution: Ensure server is running with Daphne, not runserver
```

### "ModuleNotFoundError: No module named 'websockets'"
```bash
pip install websockets
```

### WebSocket Closed Unexpectedly
- Check server logs: `daphne -b 0.0.0.0 -p 8000 fdpp_ems.asgi:application`
- Verify firewall allows port 8000
- Check network connectivity

### Messages Not Being Received
- Verify WebSocket is in "OPEN" state
- Check message format is valid JSON
- Look for errors in browser console or server logs

---

## 🚀 Production Checklist

- [ ] Install `pyzk` and `websockets`
- [ ] Start Daphne server (not runserver)
- [ ] Configure correct IP addresses for device and server
- [ ] Test WebSocket connection with browser console
- [ ] Monitor server logs during initial scans
- [ ] Verify employee data is being created in database
- [ ] Test with 5+ scans to confirm stability
- [ ] Set up log rotation for biometric_websocket.log
- [ ] Configure firewall to allow WebSocket port
- [ ] Test automatic reconnection on server restart

---

## 📝 Logging

### Biometric Script Logs
```bash
# View live logs
tail -f d:\FDPP_attendence\biometric_websocket.log

# View HTTP logs (if using old script)
tail -f d:\FDPP_attendence\biometric_integration.log
```

### Server Logs
- Django: `python manage.py runserver` or `daphne` output
- Check for WebSocket errors and connection issues

---

## ✨ You're Ready!

Your system now has:
- ✅ Real-time biometric integration
- ✅ WebSocket for instant updates
- ✅ Dashboard with live attendance
- ✅ Multiple client support
- ✅ Scalable architecture

Start using it! 🎉

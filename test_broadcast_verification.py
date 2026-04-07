import asyncio
import websockets
import json
import requests
import time

# Configuration
SERVER_IP = "172.172.172.160"
WS_URL = f"ws://{SERVER_IP}:8000/ws/attendance/"
API_URL = f"http://{SERVER_IP}:8000/api/attendance/auto_attendance/"
EMP_ID = 2

async def verify_broadcast():
    print(f"Connecting to WebSocket: {WS_URL}...")
    try:
        async with websockets.connect(WS_URL) as websocket:
            # Step 1: Wait for connection confirmation
            resp = await websocket.recv()
            print(f"Connected: {resp}")
            
            # Step 2: Trigger the API in a separate thread (or just use requests here as it's async context but synchronous call)
            # We'll do it after a small delay to ensure we're listening
            print(f"Triggering API: {API_URL} for emp_id: {EMP_ID}...")
            
            # Use synchronous requests for simplicity, it will block for a moment but that's fine here
            response = requests.post(API_URL, json={"emp_id": EMP_ID})
            print(f"API Response: {response.status_code}")
            
            # Step 3: Listen for the broadcast
            print("Waiting for broadcast message...")
            try:
                # We expect two messages if we just connected:
                # 1. Connection message (already received)
                # 2. The broadcast message we just triggered
                
                start_time = time.time()
                while time.time() - start_time < 5: # 5 second timeout
                    msg = await websocket.recv()
                    data = json.loads(msg)
                    print(f"Received message: {json.dumps(data, indent=2)}")
                    
                    if data.get("type") == "attendance_broadcast":
                        print("\nSUCCESS: Received attendance broadcast!")
                        return True
            except asyncio.TimeoutError:
                print("\nTIMEOUT: No broadcast message received.")
                return False
                
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(verify_broadcast())
    if result:
        print("Verification PASSED")
    else:
        print("Verification FAILED")

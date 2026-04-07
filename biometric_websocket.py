"""
ZK K40 Biometric Device Integration with WebSocket Support
Connects to ZK K40 device and sends real-time updates via WebSocket
"""

import os
import sys
import django
import json
import logging
import asyncio
import websockets
from datetime import datetime
from zk import ZK, const

# Setup Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fdpp_ems.settings')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'fdpp_ems'))
django.setup()

from django.conf import settings

# ============ CONFIGURATION ============
DEVICE_IP = '172.172.173.197'
DEVICE_PORT = 4370
DEVICE_TIMEOUT = 10

# SERVER CONFIGURATION
SERVER_IP = settings.SERVER_IP
SERVER_PORT = settings.SERVER_PORT
WS_URL = f"ws://{SERVER_IP}:{SERVER_PORT}/ws/biometric/"

# LOGGING - Set encoding to avoid emoji errors on Windows
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('biometric_websocket.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class BiometricMonitorWebSocket:
    def __init__(self, device_ip, device_port, ws_url, timeout=DEVICE_TIMEOUT):
        self.device_ip = device_ip
        self.device_port = device_port
        self.ws_url = ws_url
        self.timeout = timeout
        self.conn = None
        self.ws_conn = None
        self.last_count = 0
        self.retry_count = 0
        self.max_retries = 5
        
    def connect_device(self):
        """Establish connection to ZK K40 device (Synchronous library)"""
        try:
            zk = ZK(self.device_ip, port=self.device_port, timeout=self.timeout)
            self.conn = zk.connect()
            logger.info(f"Connected to ZK K40 device at {self.device_ip}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to device: {str(e)}")
            return False

    async def connect_websocket(self):
        """Establish WebSocket connection to server"""
        try:
            self.ws_conn = await websockets.connect(self.ws_url)
            logger.info(f"WebSocket connected to {self.ws_url}")
            
            # Receive connection confirmation
            response = await self.ws_conn.recv()
            logger.info(f"Server says: {response}")
            return True
        except Exception as e:
            logger.error(f"WebSocket connection failed: {str(e)}")
            return False

    async def send_biometric_data(self, emp_id):
        """Send employee ID to server via WebSocket and await response"""
        try:
            if not self.ws_conn:
                logger.error("WebSocket not connected")
                return False

            payload = {"emp_id": str(emp_id)}
            await self.ws_conn.send(json.dumps(payload))
            
            # Wait for the server to process attendance and return info
            response = await self.ws_conn.recv()
            data = json.loads(response)
            
            # If the response is a broadcast from group_send
            if data.get('type') == 'biometric_attendance':
                inner_data = data.get('data', {})
                msg = inner_data.get('message', 'Attendance Processed')
                logger.info(f"SUCCESS: {msg}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error sending data: {str(e)}")
            return False

    async def process_attendance(self):
        """Fetch logs from device and trigger WebSocket send"""
        try:
            # get_attendance is a sync call, we run it in a thread to keep loop alive
            loop = asyncio.get_event_loop()
            attendance = await loop.run_in_executor(None, self.conn.get_attendance)
            
            current_count = len(attendance)
            if current_count > self.last_count:
                new_records = attendance[self.last_count:]
                logger.info(f"Detected {len(new_records)} new scan(s)")
                
                for log in new_records:
                    emp_id = log.user_id
                    # KEY FIX: We await the send_biometric_data here
                    await self.send_biometric_data(emp_id)
                
                self.last_count = current_count
        except Exception as e:
            logger.error(f"Error processing logs: {str(e)}")

    async def monitor_loop(self):
        """Main async loop"""
        logger.info("Starting Biometric Monitor Loop...")
        
        if not self.connect_device():
            return

        # Initialize count
        try:
            init_logs = self.conn.get_attendance()
            self.last_count = len(init_logs)
            logger.info(f"Initialized. Ignoring {self.last_count} old records.")
        except:
            self.last_count = 0

        while True:
            try:
                await self.process_attendance()
                await asyncio.sleep(2) # Check every 2 seconds
            except Exception as e:
                logger.error(f"Loop error: {e}")
                await asyncio.sleep(5)

async def main():
    monitor = BiometricMonitorWebSocket(
        device_ip=DEVICE_IP,
        device_port=DEVICE_PORT,
        ws_url=WS_URL
    )
    
    # WebSocket Connection with auto-reconnect
    while True:
        try:
            if await monitor.connect_websocket():
                # Start the monitoring loop
                await monitor.monitor_loop()
        except (websockets.ConnectionClosed, Exception) as e:
            logger.error(f"Connection lost: {e}. Retrying in 5s...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    # Fix for Windows loop policy
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped by user.")
"""
ZK K40 Biometric Device Integration with WebSocket Support
Connects to ZK K40 device and sends real-time updates via WebSocket
"""

import os
import sys
import django
import time
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
DEVICE_IP = '172.172.173.235'  # Your ZK K40 device IP
DEVICE_PORT = 4370             # ZK default port
DEVICE_TIMEOUT = 10            # Connection timeout in seconds

# SERVER CONFIGURATION (WebSocket) - Imported from Django settings
SERVER_IP = settings.SERVER_IP
SERVER_PORT = settings.SERVER_PORT
WS_URL = f"ws://{SERVER_IP}:{SERVER_PORT}/ws/biometric/"

# LOGGING CONFIGURATION
LOG_FILE = 'biometric_websocket.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============ BIOMETRIC MONITOR WITH WEBSOCKET ============
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
        """Establish connection to ZK K40 device"""
        try:
            zk = ZK(self.device_ip, port=self.device_port, timeout=self.timeout)
            self.conn = zk.connect()
            logger.info(f"✅ Successfully connected to ZK K40 device at {self.device_ip}:{self.device_port}")
            self.retry_count = 0
            return True
        except Exception as e:
            self.retry_count += 1
            logger.error(f"❌ Failed to connect to device: {str(e)} (Attempt {self.retry_count}/{self.max_retries})")
            return False

    def disconnect_device(self):
        """Safely disconnect from device"""
        try:
            if self.conn:
                self.conn.disconnect()
                logger.info("Device disconnected safely")
        except Exception as e:
            logger.error(f"Error during disconnect: {str(e)}")

    async def connect_websocket(self):
        """Establish WebSocket connection to server"""
        try:
            self.ws_conn = await websockets.connect(self.ws_url)
            logger.info(f"✅ WebSocket connected to {self.ws_url}")
            
            # Receive connection confirmation
            response = await self.ws_conn.recv()
            logger.info(f"Server: {response}")
            return True
        except Exception as e:
            logger.error(f"❌ WebSocket connection failed: {str(e)}")
            return False

    async def disconnect_websocket(self):
        """Safely disconnect WebSocket"""
        try:
            if self.ws_conn:
                await self.ws_conn.close()
                logger.info("WebSocket disconnected safely")
        except Exception as e:
            logger.error(f"Error during WebSocket disconnect: {str(e)}")

    async def send_biometric_data(self, emp_id):
        """Send employee ID to server via WebSocket"""
        try:
            payload = {
                "emp_id": int(emp_id)
            }
            
            if self.ws_conn:
                # Send to server
                await self.ws_conn.send(json.dumps(payload))
                
                # Receive response
                response = await self.ws_conn.recv()
                data = json.loads(response)
                
                if data.get('type') == 'biometric_success':
                    action = data.get('action', 'unknown')
                    emp_name = data.get('employee_name', 'Unknown')
                    message = data.get('message', '')
                    logger.info(f"{message}")
                    return True, data
                else:
                    logger.error(f"❌ Error: {data.get('error', 'Unknown error')}")
                    return False, data
            else:
                logger.error("❌ WebSocket not connected")
                return False, "WebSocket not connected"
                
        except Exception as e:
            logger.error(f"❌ Error sending biometric data: {str(e)}")
            return False, str(e)

    def process_attendance(self):
        """Get attendance logs from device and process new records"""
        try:
            attendance = self.conn.get_attendance()
            current_count = len(attendance)
            
            if current_count > self.last_count:
                new_records = attendance[self.last_count:]
                
                logger.info(f"📊 New scan detected: {len(new_records)} new record(s)")
                
                for log in new_records:
                    emp_id = log.user_id
                    timestamp = log.timestamp
                    
                    logger.info(f"📱 New Biometric Scan - Employee ID: {emp_id}, Time: {timestamp}")
                    
                    # Send via WebSocket (non-blocking)
                    try:
                        asyncio.run(self.send_biometric_data(emp_id))
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to send WebSocket data for ID {emp_id}: {str(e)}")
                
                self.last_count = current_count
                
        except Exception as e:
            logger.error(f"❌ Error processing attendance: {str(e)}")

    def initialize_count(self):
        """Get initial attendance count to ignore old records"""
        try:
            attendance = self.conn.get_attendance()
            self.last_count = len(attendance)
            logger.info(f"📊 Initialized with {self.last_count} existing records")
            return True
        except Exception as e:
            logger.error(f"❌ Error initializing count: {str(e)}")
            return False

    def monitor(self):
        """Main monitoring loop (runs synchronously, WebSocket calls are async)"""
        logger.info("🔄 Starting Biometric Monitor Loop...")
        
        # Connect to device
        if not self.connect_device():
            return False
        
        # Initialize count
        if not self.initialize_count():
            self.disconnect_device()
            return False
        
        try:
            while True:
                self.process_attendance()
                time.sleep(1)  # Check every 1 second
                
        except KeyboardInterrupt:
            logger.info("\n⏹️  Monitor stopped by user")
            self.disconnect_device()
            return True
        except Exception as e:
            logger.error(f"❌ Unexpected error in monitor loop: {str(e)}")
            self.disconnect_device()
            return False


async def main():
    """Main async function"""
    logger.info("="*60)
    logger.info("FDPP EMS - ZK K40 Biometric WebSocket Integration Started")
    logger.info(f"Device IP: {DEVICE_IP}:{DEVICE_PORT}")
    logger.info(f"WebSocket URL: {WS_URL}")
    logger.info("="*60)
    
    monitor = BiometricMonitorWebSocket(
        device_ip=DEVICE_IP,
        device_port=DEVICE_PORT,
        ws_url=WS_URL,
        timeout=DEVICE_TIMEOUT
    )
    
    # Connect WebSocket
    while True:
        if await monitor.connect_websocket():
            # Start monitoring
            monitor.monitor()
            await monitor.disconnect_websocket()
        
        if monitor.retry_count < monitor.max_retries:
            wait_time = 5 * (monitor.retry_count + 1)
            logger.info(f"⏳ Retrying WebSocket connection in {wait_time} seconds...")
            await asyncio.sleep(wait_time)
        else:
            logger.critical("❌ Max retries exceeded. Please check device and server.")
            break


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"Critical error: {str(e)}")
        raise

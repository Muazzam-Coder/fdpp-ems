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
from pathlib import Path
from datetime import datetime
from zk import ZK, const

# Load .env values directly for standalone execution
def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    with env_path.open('r', encoding='utf-8') as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue

            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_env_file(Path(__file__).resolve().parent / '.env')

# Setup Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fdpp_ems.settings')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'fdpp_ems'))
django.setup()

# ============ CONFIGURATION ============
DEVICE_IP = os.environ.get('DEVICE_IP', '192.168.1.202')
DEVICE_PORT = int(os.environ.get('DEVICE_PORT', '4370'))
DEVICE_TIMEOUT = 10

# SERVER CONFIGURATION
SERVER_IP = os.environ['SERVER_IP']
SERVER_PORT = int(os.environ['SERVER_PORT'])
WS_URL = f"ws://{SERVER_IP}:{SERVER_PORT}/ws/biometric/"
# WS_URL = f"ws://172.172.172.160:8000/ws/biometric/"

if SERVER_IP == DEVICE_IP:
    raise RuntimeError(
        'SERVER_IP must be the Django server address, not the biometric device IP.'
    )

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

    def disconnect_device(self):
        """Close the current device session."""
        try:
            if self.conn:
                self.conn.disconnect()
        except Exception:
            pass
        finally:
            self.conn = None

    def is_device_connection_error(self, error: Exception) -> bool:
        error_text = str(error).lower()
        return any(
            keyword in error_text
            for keyword in (
                '10054',
                'timed out',
                'connection reset',
                'forcibly closed',
                'refused',
            )
        )
        
    def connect_device(self):
        """Establish connection to ZK K40 device (Synchronous library)"""
        try:
            zk = ZK(self.device_ip, port=self.device_port, timeout=self.timeout)
            self.conn = zk.connect()
            logger.info(f"Connected to ZK K40 device at {self.device_ip}:{self.device_port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to device at {self.device_ip}:{self.device_port}: {str(e)}")
            self.disconnect_device()
            return False

    async def connect_websocket(self):
        """Establish WebSocket connection to server with keepalive/ping settings"""
        try:
            # use ping/pong keepalive to prevent silent NAT/firewall drops
            self.ws_conn = await websockets.connect(
                self.ws_url,
                ping_interval=20,
                ping_timeout=10,
            )
            logger.info(f"WebSocket connected to {self.ws_url}")

            # Receive connection confirmation (short timeout)
            try:
                response = await asyncio.wait_for(self.ws_conn.recv(), timeout=5)
                logger.info(f"Server says: {response}")
            except asyncio.TimeoutError:
                logger.info("No immediate welcome message received (ok)")

            return True
        except Exception as e:
            logger.error(f"WebSocket connection failed: {str(e)}")
            self.ws_conn = None
            return False

    async def send_biometric_data(self, emp_id):
        """Send employee ID to server via WebSocket and await response"""
        try:
            # If socket isn't open, try reconnecting once
            if not self.ws_conn or not getattr(self.ws_conn, 'open', False):
                logger.warning("WebSocket not open — attempting reconnect...")
                if not await self.connect_websocket():
                    logger.error("WebSocket reconnect failed")
                    return False

            payload = {"emp_id": emp_id}
            await self.ws_conn.send(json.dumps(payload))

            # Wait for the server to process attendance and return info
            response = await asyncio.wait_for(self.ws_conn.recv(), timeout=10)
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
            # If the connection is broken, try to close and clear reference so main loop reconnects
            try:
                if self.ws_conn:
                    await self.ws_conn.close()
            except Exception:
                pass
            self.ws_conn = None
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
            return True
        except Exception as e:
            logger.error(f"Error processing logs: {str(e)}")
            if self.is_device_connection_error(e):
                self.disconnect_device()
            return False

    async def wait_for_device_reconnect(self):
        """Retry connecting to the device until it comes back."""
        delay = 2
        while True:
            logger.info(
                f"Device offline. Retrying connection to {self.device_ip}:{self.device_port} in {delay}s..."
            )
            await asyncio.sleep(delay)
            if self.connect_device():
                try:
                    init_logs = self.conn.get_attendance()
                    self.last_count = len(init_logs)
                    logger.info(f"Reconnected. Ignoring {self.last_count} old records.")
                except Exception:
                    self.last_count = 0
                return
            delay = min(delay + 2, 10)

    async def monitor_loop(self):
        """Main async loop"""
        logger.info("Starting Biometric Monitor Loop...")
        
        if not self.connect_device():
            await self.wait_for_device_reconnect()

        # Initialize count
        try:
            init_logs = self.conn.get_attendance()
            self.last_count = len(init_logs)
            logger.info(f"Initialized. Ignoring {self.last_count} old records.")
        except:
            self.last_count = 0

        while True:
            try:
                connected = await self.process_attendance()
                if not connected:
                    await self.wait_for_device_reconnect()
                await asyncio.sleep(2) # Check every 2 seconds
            except Exception as e:
                logger.error(f"Loop error: {e}")
                self.disconnect_device()
                await self.wait_for_device_reconnect()
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
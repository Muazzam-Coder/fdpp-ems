"""
ZK K40 Biometric Device Integration with FDPP EMS
Connects to ZK K40 device, reads employee IDs, and calls auto_attendance endpoint
"""

import time
import requests
import logging
from datetime import datetime
from zk import ZK, const

# ============ CONFIGURATION ============
DEVICE_IP = '172.172.173.197'  # Your ZK K40 device IP
DEVICE_PORT = 4370             # ZK default port
DEVICE_TIMEOUT = 10            # Connection timeout in seconds

# SERVER CONFIGURATION
SERVER_IP = '172.172.173.102'  # Your Django server IP
SERVER_PORT = '8000'           # Your Django server port
SERVER_URL = f"http://{SERVER_IP}:{SERVER_PORT}/api/attendance/auto_attendance/"

# LOGGING CONFIGURATION
LOG_FILE = 'biometric_integration.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============ BIOMETRIC MONITOR CLASS ============
class BiometricMonitor:
    def __init__(self, device_ip, device_port, server_url, timeout=DEVICE_TIMEOUT):
        self.device_ip = device_ip
        self.device_port = device_port
        self.server_url = server_url
        self.timeout = timeout
        self.conn = None
        self.last_count = 0
        self.retry_count = 0
        self.max_retries = 5
        
    def connect_device(self):
        """Establish connection to ZK K40 device"""
        try:
            zk = ZK(self.device_ip, port=self.device_port, timeout=self.timeout)
            self.conn = zk.connect()
            logger.info(f"✅ Successfully connected to ZK K40 device at {self.device_ip}:{self.device_port}")
            self.retry_count = 0  # Reset retry count on successful connection
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

    def call_server(self, emp_id):
        """Send employee ID to server's auto_attendance endpoint"""
        try:
            payload = {
                "emp_id": int(emp_id)
            }
            
            response = requests.post(
                self.server_url,
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                action = data.get('action', 'unknown')
                emp_name = data.get('record', {}).get('employee_name', 'Unknown')
                is_late = data.get('is_late', False)
                late_msg = data.get('late_message', '')
                
                if is_late:
                    logger.info(f"⚠️ {emp_name} (ID: {emp_id}) - {action.upper()} - {late_msg}")
                else:
                    logger.info(f"✅ {emp_name} (ID: {emp_id}) - {action.upper()} - On time")
                    
                return True, data
                
            else:
                logger.error(f"❌ Server Error ({response.status_code}): {response.text}")
                return False, response.text
                
        except requests.exceptions.Timeout:
            logger.error(f"❌ Server Connection Timeout for Employee {emp_id}")
            return False, "Timeout"
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Cannot reach server at {self.server_url}")
            return False, "Connection Error"
        except Exception as e:
            logger.error(f"❌ Network Error for Employee {emp_id}: {str(e)}")
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
                    
                    # Call server endpoint
                    success, response = self.call_server(emp_id)
                    
                    if not success:
                        logger.warning(f"⚠️ Failed to process attendance for ID {emp_id}")
                
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
        """Main monitoring loop"""
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
                time.sleep(2)  # Check every 2 seconds
                
        except KeyboardInterrupt:
            logger.info("\n⏹️  Monitor stopped by user")
            self.disconnect_device()
            return True
        except Exception as e:
            logger.error(f"❌ Unexpected error in monitor loop: {str(e)}")
            self.disconnect_device()
            return False


# ============ MAIN EXECUTION ============
def main():
    """Main function with retry logic"""
    logger.info("="*60)
    logger.info("FDPP EMS - ZK K40 Biometric Integration Started")
    logger.info(f"Device IP: {DEVICE_IP}:{DEVICE_PORT}")
    logger.info(f"Server URL: {SERVER_URL}")
    logger.info("="*60)
    
    monitor = BiometricMonitor(
        device_ip=DEVICE_IP,
        device_port=DEVICE_PORT,
        server_url=SERVER_URL,
        timeout=DEVICE_TIMEOUT
    )
    
    while True:
        success = monitor.monitor()
        
        if not success and monitor.retry_count < monitor.max_retries:
            wait_time = 5 * (monitor.retry_count + 1)  # Exponential backoff
            logger.info(f"⏳ Retrying connection in {wait_time} seconds...")
            time.sleep(wait_time)
        else:
            if monitor.retry_count >= monitor.max_retries:
                logger.critical("❌ Max retries exceeded. Please check device and server.")
            break


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Critical error in main: {str(e)}")
        raise

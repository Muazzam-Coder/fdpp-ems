"""
WebSocket Test Script - Verify Server Connection
"""

import asyncio
import websockets
import json
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
SERVER_IP = '127.0.0.1'  # Use localhost for testing
SERVER_PORT = '8000'
BIOMETRIC_WS_URL = f'ws://{SERVER_IP}:{SERVER_PORT}/ws/biometric/'
ATTENDANCE_WS_URL = f'ws://{SERVER_IP}:{SERVER_PORT}/ws/attendance/'

async def test_biometric_connection():
    """Test connection to biometric WebSocket endpoint"""
    logger.info(f"Testing Biometric WebSocket: {BIOMETRIC_WS_URL}")
    
    try:
        async with websockets.connect(BIOMETRIC_WS_URL) as websocket:
            logger.info("✅ Connected to biometric WebSocket!")
            
            # Send a test message
            test_data = {"emp_id": 1}
            logger.info(f"📤 Sending test message: {test_data}")
            await websocket.send(json.dumps(test_data))
            
            # Receive response
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            logger.info(f"📥 Received response: {response}")
            
    except ConnectionRefusedError:
        logger.error("❌ Connection refused. Is Daphne running on port 8000?")
    except asyncio.TimeoutError:
        logger.warning("⚠️ No response received within 5 seconds (this may be normal)")
    except Exception as e:
        logger.error(f"❌ Connection error: {type(e).__name__}: {e}")


async def test_attendance_connection():
    """Test connection to attendance WebSocket endpoint"""
    logger.info(f"\nTesting Attendance WebSocket: {ATTENDANCE_WS_URL}")
    
    try:
        async with websockets.connect(ATTENDANCE_WS_URL) as websocket:
            logger.info("✅ Connected to attendance WebSocket!")
            
            # Receive initial connection message
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            logger.info(f"📥 Connection message: {response}")
            
            # Send a test query
            test_data = {"emp_id": 1, "action": "check_attendance"}
            logger.info(f"📤 Sending test message: {test_data}")
            await websocket.send(json.dumps(test_data))
            
            # Receive response
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            logger.info(f"📥 Received response: {response}")
            
    except ConnectionRefusedError:
        logger.error("❌ Connection refused. Is Daphne running on port 8000?")
    except asyncio.TimeoutError:
        logger.warning("⚠️ No response within 5 seconds")
    except Exception as e:
        logger.error(f"❌ Connection error: {type(e).__name__}: {e}")


async def main():
    """Run all tests"""
    logger.info("="*60)
    logger.info("WebSocket Connection Tests")
    logger.info(f"Server: {SERVER_IP}:{SERVER_PORT}")
    logger.info("="*60)
    
    await test_attendance_connection()
    await test_biometric_connection()
    
    logger.info("\n" + "="*60)
    logger.info("Tests completed!")
    logger.info("="*60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")

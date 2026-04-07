"""
Biometric WebSocket Connection Test - No Device Required
Tests if the biometric script can connect to the server's WebSocket endpoint
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

# Use the network IP instead of localhost
SERVER_IP = '172.172.173.197'  # Your Django server IP
SERVER_PORT = '8000'
WS_URL = f"ws://{SERVER_IP}:{SERVER_PORT}/ws/biometric/"

async def test_biometric_connection():
    """Test biometric WebSocket connection"""
    logger.info(f"Testing Biometric WebSocket Connection")
    logger.info(f"URL: {WS_URL}")
    logger.info("=" * 60)
    
    try:
        # Try to connect
        logger.info("⏳ Attempting connection...")
        async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=20) as websocket:
            logger.info("✅ **CONNECTION SUCCESSFUL!**")
            
            # Receive connection confirmation
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            logger.info(f"📥 Server response: {response}")
            
            # Send a test scan
            logger.info("\n📤 Sending test scan (emp_id: 1)...")
            test_scan = {"emp_id": 1}
            await websocket.send(json.dumps(test_scan))
            
            # Receive confirmation
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            logger.info(f"📥 Server accepted scan: {response}")
            
            logger.info("\n✅ WebSocket connection is working correctly!")
            logger.info("✅ The biometric_websocket.py script should work fine")
            
    except ConnectionRefusedError as e:
        logger.error(f"\n❌ Connection Refused: {e}")
        logger.error(f"   - Check if Daphne is running on {SERVER_IP}:8000")
        logger.error(f"   - Check firewall settings for port 8000")
        logger.error(f"   - Verify the server IP address is correct")
        
    except asyncio.TimeoutError as e:
        logger.error(f"\n❌ Connection Timeout: {e}")
        logger.error(f"   - Server not responding")
        logger.error(f"   - Network connectivity issue")
        logger.error(f"   - Try using 127.0.0.1 instead of {SERVER_IP}")
        
    except OSError as e:
        logger.error(f"\n❌ Network Error: {e}")
        logger.error(f"   - Cannot resolve {SERVER_IP}")
        logger.error(f"   - Network unreachable")
        logger.error(f"   - Check your network connection")
        
    except Exception as e:
        logger.error(f"\n❌ Unexpected Error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    logger.info("Biometric WebSocket Connection Test")
    logger.info("=" * 60)
    
    try:
        asyncio.run(test_biometric_connection())
    except KeyboardInterrupt:
        logger.info("\nTest interrupted")

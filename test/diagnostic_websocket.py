"""
WebSocket Connectivity Diagnostic Tool
Identifies and fixes common connection issues
"""

import subprocess
import socket
import asyncio
import websockets
import json
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DiagnosticTool:
    def __init__(self, host, port, ws_path="/ws/biometric/"):
        self.host = host
        self.port = port
        self.ws_path = ws_path
        self.ws_url = f"ws://{host}:{port}{ws_path}"
        
    def check_port_listening(self):
        """Check if port is open and listening"""
        logger.info(f"\n1️⃣  Checking if port {self.port} is listening...")
        
        try:
            result = subprocess.run(
                f'Get-NetTCPConnection -LocalPort {self.port} -ErrorAction SilentlyContinue',
                shell=True, capture_output=True, text=True
            )
            if result.returncode == 0 and "Listen" in result.stdout:
                logger.info(f"   ✅ Port {self.port} is LISTENING")
                return True
            else:
                logger.error(f"   ❌ Port {self.port} is NOT listening")
                return False
        except Exception as e:
            logger.error(f"   ❌ Error checking port: {e}")
            return False
    
    def test_tcp_socket(self):
        """Test TCP connection to the host:port"""
        logger.info(f"\n2️⃣  Testing TCP connection to {self.host}:{self.port}...")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            
            if result == 0:
                logger.info(f"   ✅ TCP connection successful to {self.host}:{self.port}")
                return True
            else:
                logger.error(f"   ❌ TCP connection failed: {result}")
                return False
        except Exception as e:
            logger.error(f"   ❌ TCP socket error: {type(e).__name__}: {e}")
            return False
    
    async def test_websocket(self):
        """Test WebSocket connection"""
        logger.info(f"\n3️⃣  Testing WebSocket connection to {self.ws_url}...")
        
        try:
            async with websockets.connect(self.ws_url, ping_interval=None) as ws:
                logger.info(f"   ✅ WebSocket connected!")
                
                # Receive welcome message
                response = await asyncio.wait_for(ws.recv(), timeout=3)
                logger.info(f"   📨 Received: {response}")
                
                # Send test data
                test_data = {"emp_id": 1}
                logger.info(f"   📤 Sending test data: {test_data}")
                await ws.send(json.dumps(test_data))
                
                # Receive response
                response = await asyncio.wait_for(ws.recv(), timeout=3)
                logger.info(f"   📨 Received: {response}")
                
                return True
                
        except asyncio.TimeoutError:
            logger.error(f"   ❌ WebSocket timeout - server not responding")
            return False
        except ConnectionRefusedError as e:
            logger.error(f"   ❌ WebSocket connection refused: {e}")
            return False
        except Exception as e:
            logger.error(f"   ❌ WebSocket error: {type(e).__name__}: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all diagnostic tests"""
        logger.info("="*70)
        logger.info("WebSocket Connectivity Diagnostic Tool")
        logger.info(f"Host: {self.host}:{self.port}")
        logger.info(f"URL:  {self.ws_url}")
        logger.info("="*70)
        
        # Test 1: Port listening
        port_ok = self.check_port_listening()
        
        # Test 2: TCP connection
        tcp_ok = self.test_tcp_socket()
        
        # Test 3: WebSocket
        ws_ok = await self.test_websocket()
        
        # Diagnosis
        logger.info("\n" + "="*70)
        logger.info("DIAGNOSIS:")
        logger.info("="*70)
        
        if port_ok and tcp_ok and ws_ok:
            logger.info("✅ Everything working! WebSocket is connected and operational.")
            logger.info("\n✅ SOLUTION: No issues found. The server is working correctly.")
            return True
        
        elif not port_ok:
            logger.error("\n❌ PROBLEM: Port 8000 is not listening")
            logger.info("\nSOLUTION:")
            logger.info("1. Check if Daphne is running:")
            logger.info("   & \"d:\\FDPP attendence\\venv\\Scripts\\Activate.ps1\"")
            logger.info("   cd \"d:\\FDPP attendence\\fdpp_ems\"")
            logger.info("   python -m daphne -b 0.0.0.0 -p 8000 fdpp_ems.asgi:application")
            return False
            
        elif not tcp_ok:
            logger.error("\n❌ PROBLEM: Cannot establish TCP connection to host")
            logger.info("\nSOLUTION - Try one of these:")
            logger.info("1. Use localhost (127.0.0.1) instead of 172.172.173.197")
            logger.info("   - Change SERVER_IP = '127.0.0.1' in biometric_websocket.py")
            logger.info("2. Check firewall settings:")
            logger.info("   - Allow port 8000 through Windows Firewall")
            logger.info("3. Verify network connectivity:")
            logger.info("   - ping 172.172.173.197")
            logger.info("4. Check your IP address:")
            logger.info("   - ipconfig /all  (to see your actual IP)")
            return False
            
        elif not ws_ok:
            logger.error("\n❌ PROBLEM: WebSocket handshake failed")
            logger.info("\nSOLUTION:")
            logger.info("1. Check Django settings.py includes:")
            logger.info("   - INSTALLED_APPS has 'channels'")
            logger.info("   - ASGI_APPLICATION = 'fdpp_ems.asgi.application'")
            logger.info("2. Check asgi.py has proper routes:")
            logger.info("   - ws/biometric/ should map to BiometricConsumer")
            logger.info("3. Restart Daphne server")
            return False
        
        return False


async def main():
    """Run diagnostics for both localhost and network IP"""
    
    # Test 1: Localhost (always works if server running)
    logger.info("\n" + "🔍 TEST 1: Localhost Connection (127.0.0.1:8000)")
    tool1 = DiagnosticTool("127.0.0.1", 8000)
    result1 = await tool1.run_all_tests()
    
    # Test 2: Network IP (might fail if network config issue)
    logger.info("\n\n🔍 TEST 2: Network IP Connection (172.172.173.197:8000)")
    tool2 = DiagnosticTool("172.172.173.197", 8000)
    result2 = await tool2.run_all_tests()
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("SUMMARY:")
    logger.info("="*70)
    
    if result1:
        logger.info("✅ Localhost works - Use 127.0.0.1 for testing")
    else:
        logger.error("❌ Localhost failed - Check Daphne server")
    
    if result2:
        logger.info("✅ Network IP works - Use 172.172.173.197 for deployment")
    else:
        logger.error("❌ Network IP failed - Check network configuration")
    
    logger.info("\n" + "="*70)
    if result1:
        logger.info("✅ Server is operational! Ready to integrate biometric device.")
    else:
        logger.error("❌ Server not fully operational. Fix issues above.")
    logger.info("="*70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\nDiagnostics interrupted")

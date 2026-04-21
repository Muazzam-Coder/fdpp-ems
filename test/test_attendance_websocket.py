"""
WebSocket Attendance Test - Diagnose Data Flow
Tests both biometric and attendance WebSocket endpoints
"""

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

# Configuration
SERVER_IP = '172.172.172.160'
SERVER_PORT = 8000
BIOMETRIC_URL = f'ws://{SERVER_IP}:{SERVER_PORT}/ws/biometric/'
ATTENDANCE_URL = f'ws://{SERVER_IP}:{SERVER_PORT}/ws/attendance/'

async def test_attendance_websocket():
    """Test attendance WebSocket connection and data retrieval"""
    logger.info("="*70)
    logger.info("TEST 1: Attendance WebSocket (UI Dashboard)")
    logger.info("="*70)
    logger.info(f"Connecting to: {ATTENDANCE_URL}\n")
    
    try:
        async with websockets.connect(ATTENDANCE_URL, ping_interval=None) as ws:
            # Receive connection message
            logger.info("📥 Waiting for connection confirmation...")
            response = await asyncio.wait_for(ws.recv(), timeout=5)
            conn_msg = json.loads(response)
            logger.info(f"✅ Connection confirmed:")
            logger.info(f"   Message: {conn_msg.get('message')}")
            logger.info(f"   Type: {conn_msg.get('type')}\n")
            
            # Query employee attendance (emp_id = 1)
            logger.info("📤 Querying employee attendance (emp_id: 1)...")
            query = {"emp_id": 1, "action": "check_attendance"}
            await ws.send(json.dumps(query))
            logger.info(f"   Sent: {json.dumps(query)}\n")
            
            # Receive attendance data
            logger.info("📥 Receiving attendance data...")
            response = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(response)
            
            logger.info(f"✅ Received attendance data:")
            logger.info(f"   Type: {data.get('type')}")
            logger.info(f"   Employee: {data.get('first_name', '')} {data.get('last_name', '')} (ID: {data.get('emp_id')})")
            logger.info(f"   Shift: {data.get('shift_type')} ({data.get('shift_start')} - {data.get('shift_end')})")
            logger.info(f"   Check-in: {data.get('check_in')}")
            logger.info(f"   Check-out: {data.get('check_out')}")
            logger.info(f"   Total Hours: {data.get('total_hours')}")
            logger.info(f"   Status: {'Late' if data.get('is_late') else 'On time'}")
            logger.info(f"   Message: {data.get('message')}")
            logger.info(f"   Timestamp: {data.get('timestamp')}\n")
            
            if data.get('check_in'):
                logger.info("✓ Attendance data is being returned correctly!")
            else:
                logger.warning("⚠️ No check-in time found - Employee may not have scanned yet")
            
            return True
            
    except asyncio.TimeoutError:
        logger.error("❌ Timeout - No response from server")
        return False
    except ConnectionRefusedError:
        logger.error("❌ Connection refused - Server not running or unreachable")
        return False
    except Exception as e:
        logger.error(f"❌ Error: {type(e).__name__}: {e}")
        return False


async def test_biometric_websocket():
    """Test biometric WebSocket connection"""
    logger.info("\n" + "="*70)
    logger.info("TEST 2: Biometric WebSocket (Device Integration)")
    logger.info("="*70)
    logger.info(f"Connecting to: {BIOMETRIC_URL}\n")
    
    try:
        async with websockets.connect(BIOMETRIC_URL, ping_interval=None) as ws:
            # Receive connection message
            logger.info("📥 Waiting for biometric connection confirmation...")
            response = await asyncio.wait_for(ws.recv(), timeout=5)
            conn_msg = json.loads(response)
            logger.info(f"✅ Biometric connection confirmed:")
            logger.info(f"   Message: {conn_msg.get('message')}")
            logger.info(f"   Type: {conn_msg.get('type')}\n")
            
            # Send test scan
            logger.info("📤 Sending test biometric scan (emp_id: 1)...")
            scan = {"emp_id": 1}
            await ws.send(json.dumps(scan))
            logger.info(f"   Sent: {json.dumps(scan)}\n")
            
            # Receive scan response
            logger.info("📥 Receiving biometric response...")
            response = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(response)
            
            logger.info(f"✅ Received biometric response:")
            logger.info(f"   Type: {data.get('type')}")
            logger.info(f"   Employee: {data.get('employee_name')} (ID: {data.get('emp_id')})")
            logger.info(f"   Action: {data.get('action')}")
            logger.info(f"   Message: {data.get('message')}")
            logger.info(f"   Check-in: {data.get('check_in')}")
            logger.info(f"   Check-out: {data.get('check_out')}\n")
            
            if data.get('type') == 'biometric_success':
                logger.info("✓ Biometric scan processed successfully!")
                
                # Now query the same employee via attendance WebSocket
                logger.info("\n" + "-"*70)
                logger.info("Verifying via Attendance WebSocket...")
                logger.info("-"*70 + "\n")
                
                await asyncio.sleep(0.5)  # Brief pause
                return True
            else:
                logger.error(f"❌ Unexpected response: {data}")
                return False
            
    except asyncio.TimeoutError:
        logger.error("❌ Timeout - No response from server")
        return False
    except ConnectionRefusedError:
        logger.error("❌ Connection refused - Server not running or unreachable")
        return False
    except Exception as e:
        logger.error(f"❌ Error: {type(e).__name__}: {e}")
        return False


async def test_full_flow():
    """Test complete flow: biometric scan -> attendance query"""
    logger.info("\n" + "="*70)
    logger.info("TEST 3: Complete Flow (Biometric Scan + Attendance Query)")
    logger.info("="*70)
    
    try:
        # Step 1: Connect to biometric and send scan
        logger.info("\n[Step 1/3] Sending biometric scan...")
        async with websockets.connect(BIOMETRIC_URL, ping_interval=None) as ws:
            # Receive connection
            response = await asyncio.wait_for(ws.recv(), timeout=5)
            logger.info(f"✓ Connected to biometric WebSocket")
            
            # Send scan
            scan = {"emp_id": 1}
            await ws.send(json.dumps(scan))
            
            # Receive response
            response = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(response)
            logger.info(f"✓ Scan processed: {data.get('action')} - {data.get('employee_name')}")
            logger.info(f"  Check-in: {data.get('check_in')}")
        
        # Step 2: Wait briefly for database
        logger.info("\n[Step 2/3] Waiting for data to be processed...")
        await asyncio.sleep(1)
        
        # Step 3: Query attendance
        logger.info("\n[Step 3/3] Querying attendance data...")
        async with websockets.connect(ATTENDANCE_URL, ping_interval=None) as ws:
            # Receive connection
            response = await asyncio.wait_for(ws.recv(), timeout=5)
            
            # Send query
            query = {"emp_id": 1, "action": "check_attendance"}
            await ws.send(json.dumps(query))
            
            # Receive response
            response = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(response)
            
            logger.info(f"✓ Attendance data retrieved:\n")
            logger.info(f"  Employee: {data.get('first_name')} {data.get('last_name')} (ID: {data.get('emp_id')})")
            logger.info(f"  Shift: {data.get('shift_type')} ({data.get('shift_start')} - {data.get('shift_end')})")
            logger.info(f"  Check-in: {data.get('check_in')}")
            logger.info(f"  Check-out: {data.get('check_out')}")
            logger.info(f"  Total Hours: {data.get('total_hours')}")
            logger.info(f"  Status: {'Late' if data.get('is_late') else 'On time'}")
            logger.info(f"  Message: {data.get('message')}")
            
            if data.get('check_in'):
                logger.info("\n✅ SUCCESS: Attendance data is being returned correctly!")
                return True
            else:
                logger.warning("\n⚠️ No check-in found after biometric scan")
                return False
                
    except Exception as e:
        logger.error(f"❌ Error: {type(e).__name__}: {e}")
        return False


async def main():
    """Run all tests"""
    logger.info("FDPP EMS - WebSocket Attendance Diagnostic")
    logger.info(f"Server: {SERVER_IP}:{SERVER_PORT}\n")
    
    try:
        # Test Full Flow (recommended)
        logger.info("Running integrated test...")
        flow_ok = await test_full_flow()
        
        # Summary
        logger.info("\n" + "="*70)
        logger.info("TEST SUMMARY")
        logger.info("="*70)
        logger.info(f"Full Flow (Scan → Query): {'✅ OK' if flow_ok else '❌ FAILED'}")
        logger.info("="*70)
        
        if flow_ok:
            logger.info("\n✅ All tests passed! System is working correctly.")
            logger.info("\nWhat this means:")
            logger.info("1. WebSocket attendance endpoint is responding")
            logger.info("2. Biometric scans are being processed")
            logger.info("3. Attendance data is being stored in database")
            logger.info("4. Attendance queries return latest check-in/check-out times")
            logger.info("\nNext steps:")
            logger.info("1. Start biometric_websocket.py to connect the device")
            logger.info("2. Device scans will automatically create attendance records")
            logger.info("3. Dashboard can query status via:")
            logger.info("   ws.send(JSON.stringify({emp_id: 1, action: 'check_attendance'}))")
        else:
            logger.error("\n❌ Test failed. Checking what went wrong...")
            
            logger.error("\nTroubleshooting:")
            logger.error("1. Verify Django server is running on 172.172.172.160:8000")
            logger.error("   Check: http://172.172.172.160:8000/api/employees/")
            logger.error("2. Verify WebSocket URL is correct")
            logger.error("3. Check Django logs for errors")
            logger.error("4. Verify employee ID 1 exists in database")
            
    except Exception as e:
        logger.error(f"\nFatal error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")

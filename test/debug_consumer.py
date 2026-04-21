"""Debug: Check what the consumer method returns"""
import os, sys, django, json, asyncio
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fdpp_ems.settings')
sys.path.insert(0, 'fdpp_ems')
django.setup()

from management.consumers import AttendanceConsumer
from django.utils import timezone

async def test():
    consumer = AttendanceConsumer()
    
    # Call the method directly
    result = await consumer.check_employee_attendance(1)
    
    print("Raw result:")
    print(json.dumps(result, indent=2, default=str))
    
    print("\n\nIndividual fields:")
    print(f"type: {result.get('type')}")
    print(f"first_name: {repr(result.get('first_name'))}")
    print(f"last_name: {repr(result.get('last_name'))}")
    print(f"check_in: {repr(result.get('check_in'))}")
    print(f"check_out: {repr(result.get('check_out'))}")

asyncio.run(test())

#!/usr/bin/env python
"""Step 2: Restore shift data after migrations 0006 and 0007 have been applied.

Run AFTER `python manage.py migrate management` (i.e. AFTER 0006 and 0007).
This reads the JSON backup created by preserve_shift_data.py and:
  - Creates/retrieves Shift records matching the old shift_type names
  - Sets current_shift on each Employee
  - Creates EmployeeShiftHistory entries to preserve the historical data

Usage: python scripts/restore_shift_data.py
"""

import json
import os
import sys
from datetime import date, time
from decimal import Decimal
from pathlib import Path

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fdpp_ems.settings')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

django.setup()

from django.utils import timezone
from management.models import Employee, Shift, EmployeeShiftHistory

BACKUP_FILE = BASE_DIR / 'scripts' / 'shift_data_backup.json'


def _parse_time(val):
    if not val:
        return time(9, 0)
    parts = val.split(':')
    return time(int(parts[0]), int(parts[1]))


def _parse_date(val):
    if not val:
        return timezone.now().date()
    parts = val.split('-')
    return date(int(parts[0]), int(parts[1]), int(parts[2]))


def run():
    with open(BACKUP_FILE) as f:
        data = json.load(f)

    updated = 0
    hist_created = 0
    shifts_lookup = {}

    for item in data:
        emp = Employee.objects.filter(id=item['id']).first()
        if not emp:
            print(f"  ⚠ Employee id={item['id']} not found, skipping")
            continue

        shift_name = item.get('shift_type')
        if not shift_name or not shift_name.strip():
            continue

        shift_name = shift_name.strip()

        if shift_name not in shifts_lookup:
            shift, _ = Shift.objects.get_or_create(
                name=shift_name,
                defaults={
                    'start_time': _parse_time(item['start_time']),
                    'end_time': _parse_time(item['end_time']),
                },
            )
            shifts_lookup[shift_name] = shift

        shift = shifts_lookup[shift_name]

        emp.current_shift = shift
        emp.save(update_fields=['current_shift'])
        updated += 1

        _, created = EmployeeShiftHistory.objects.get_or_create(
            employee=emp,
            shift=shift,
            from_date=_parse_date(item['date_joined']),
            defaults={
                'salary': Decimal(str(item['salary'])) if item.get('salary') else None,
                'shift_start_time': _parse_time(item['start_time']),
                'shift_end_time': _parse_time(item['end_time']),
            },
        )
        if created:
            hist_created += 1

    print(f"Set current_shift for {updated} employees")
    print(f"Created {hist_created} EmployeeShiftHistory records")


if __name__ == '__main__':
    run()

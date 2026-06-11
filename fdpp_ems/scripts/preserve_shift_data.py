#!/usr/bin/env python
"""Step 1: Preserve old shift data before migration 0006 drops the columns.

Run BEFORE `python manage.py migrate management` (i.e. BEFORE 0006 is applied).
This saves shift_type/start_time/end_time from Employee into a JSON backup.

Usage: python scripts/preserve_shift_data.py
"""

import json
import sqlite3
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / 'db.sqlite3'
BACKUP_FILE = BASE_DIR / 'scripts' / 'shift_data_backup.json'


def run():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        'SELECT id, emp_id, name, shift_type, start_time, end_time, '
        'date_joined, salary, hourly_rate '
        'FROM management_employee'
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    # Convert non-serializable types
    for r in rows:
        for k in ('start_time', 'end_time'):
            r[k] = str(r[k]) if r[k] is not None else None
        for k in ('date_joined',):
            v = r[k]
            r[k] = v.isoformat() if isinstance(v, date) else v
        for k in ('salary', 'hourly_rate'):
            r[k] = float(r[k]) if r[k] is not None else None

    with open(BACKUP_FILE, 'w') as f:
        json.dump(rows, f, indent=2)

    print(f"Preserved shift data for {len(rows)} employees")
    print(f"Written to: {BACKUP_FILE}")


if __name__ == '__main__':
    run()

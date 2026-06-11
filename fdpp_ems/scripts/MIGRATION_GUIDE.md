# Live Server Migration Guide

Upgrade `db.sqlite3` to the latest migrations without losing data.

## Prerequisites

- Activate your virtual environment
- `cd` into the project directory (`fdpp_ems/`)
- The server should be stopped (Django app not running)

---

## Step 1 — Backup

```bash
copy db.sqlite3 db.sqlite3.backup
```

If anything goes wrong, restore with:

```bash
copy db.sqlite3.backup db.sqlite3
```

---

## Step 2 — Remove orphaned migration records

The `django_migrations` table has 3 records whose migration files no longer exist.
Delete them so Django stops getting confused:

```bash
python -c "import sqlite3; c=sqlite3.connect('db.sqlite3'); c.execute(\"DELETE FROM django_migrations WHERE app='management' AND name IN ('0002_employee_designation_alter_employee_cnic_and_more','0003_employee_referance_employee_relatives','0004_employee_deactivated_at_employee_deactivated_by_and_more')\"); c.commit(); c.close()"
```

---

## Step 3 — Fake-apply migrations 0002 → 0005

These migrations are **already applied** to the schema (the columns/tables exist).
Faking them just records them in `django_migrations` without running SQL:

```bash
python manage.py migrate --fake management 0005
```

Expected output:

```
Operations to perform:
  Target specific migration: 0005_employee_deactivated_at_employee_deactivated_by_and_more, from management
Running migrations:
  Rendering model states... DONE
  Applying management.0002_employee_nullable_fields_and_designation... FAKED
  Applying management.0003_alter_employee_date_joined_and_more... FAKED
  Applying management.0004_employee_referance_employee_relatives... FAKED
  Applying management.0005_employee_deactivated_at_employee_deactivated_by_and_more... FAKED
```

---

## Step 4 — Preserve old shift data

Migration 0006 **drops** the `shift_type`, `start_time`, and `end_time` columns from
Employee. Run this script to save that data to a JSON file before it's gone:

```bash
python scripts/preserve_shift_data.py
```

Expected output:

```
Preserved shift data for 34 employees → scripts\shift_data_backup.json
```

---

## Step 5 — Apply remaining migrations (0006 + 0007)

This creates the new tables (`Holiday`, `Overtime`, `EmployeeShiftHistory`), adds
`current_shift` / `weekly_off_day` to Employee, and removes the old columns:

```bash
python manage.py migrate management
```

Expected output:

```
Operations to perform:
  Apply all migrations: management
Running migrations:
  Applying management.0006_holiday_remove_employee_end_time_and_more... OK
  Applying management.0007_alter_employeeshifthistory_shift_end_time_and_more... OK
```

---

## Step 6 — Restore shift data

After 0006 + 0007 are applied, restore `current_shift` and create
`EmployeeShiftHistory` entries from the JSON backup:

```bash
python scripts/restore_shift_data.py
```

Expected output:

```
Set current_shift for 34 employees
Created 34 EmployeeShiftHistory records
```

---

## Step 7 — Verify

Check that all migrations are now accounted for:

```bash
python manage.py migrate --list
```

All management migrations should show `[X]` (applied).

Check a few employees via Django shell:

```bash
python manage.py shell
```

```python
from management.models import Employee, EmployeeShiftHistory
e = Employee.objects.first()
print(e.name, e.current_shift)
print(e.shift_history.count())
exit()
```

---

## Rollback

If anything goes wrong:

1. Restore the backup:
   ```bash
   copy db.sqlite3.backup db.sqlite3
   ```
2. Delete the new migration records (if any got applied):
   ```bash
   python -c "import sqlite3; c=sqlite3.connect('db.sqlite3'); c.execute(\"DELETE FROM django_migrations WHERE app='management' AND name IN ('0006_holiday_remove_employee_end_time_and_more','0007_alter_employeeshifthistory_shift_end_time_and_more')\"); c.commit(); c.close()"
   ```
3. Restore the old orphaned records:
   ```bash
   python -c "import sqlite3; c=sqlite3.connect('db.sqlite3'); c.execute(\"INSERT INTO django_migrations (app, name, applied) VALUES ('management', '0002_employee_designation_alter_employee_cnic_and_more', datetime('now')), ('management', '0003_employee_referance_employee_relatives', datetime('now')), ('management', '0004_employee_deactivated_at_employee_deactivated_by_and_more', datetime('now'))\"); c.commit(); c.close()"
   ```

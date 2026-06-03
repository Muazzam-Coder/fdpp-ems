# Backend Changes — Shift History, Holidays, Overtime, Payout

## Summary of Changes

### New Models (3)

| Model | Table | Purpose |
|---|---|---|
| `EmployeeShiftHistory` | `management_employeeshifthistory` | Tracks every shift assignment with salary snapshot |
| `Holiday` | `management_holiday` | Company-wide paid holidays |
| `Overtime` | `management_overtime` | Manager-approved overtime records |

### Modified Model

**`Employee`** (`management_employee`)
- **Removed**: `shift_type` (varchar), `start_time` (time), `end_time` (time)
- **Added**: `current_shift` (FK → Shift), `weekly_off_day` (int 0-6)

### Updated Logic

| Component | Change |
|---|---|
| `Attendance.is_late` | Uses `EmployeeShiftHistory` for the attendance date instead of `employee.start_time` |
| `build_absent_entries()` | Uses shift history to determine shift times per date |
| `mark_absent` action | Uses shift history for each date |
| `check_in` action | Uses active shift history for late calculation |
| `auto_attendance` action | Uses active shift history for late calculation + shift name |
| `daily_report` | Uses shift history per employee per date |
| `EmployeeFilter` | Replaced `shift_type` with `current_shift` filter |

---

## New API Endpoints

| Method | Path | Purpose |
|---|---|---|
| CRUD | `/api/holidays/` | Manage company holidays |
| CRUD | `/api/overtime/` | Manage overtime requests |
| POST | `/api/overtime/{id}/approve/` | Approve overtime |
| POST | `/api/overtime/{id}/reject/` | Reject overtime |
| GET/POST | `/api/employees/{emp_id}/assign_shift/` | Get/assign a shift |
| GET | `/api/employees/{emp_id}/shift_history/` | List all shift assignments |

---

## Payout Calculation Formula

For each `EmployeeShiftHistory` period within the requested date range:

```
month_days = total calendar days in the month
period_days = calendar days in this shift period
weekly_off_count = number of weekly off-days in this period
working_days = period_days - weekly_off_count
shift_hours = shift_end_time - shift_start_time (handles cross-midnight)
expected_hours = working_days × shift_hours
salary_portion = salary_snapshot × (period_days / month_days)
hourly_rate = salary_portion / expected_hours
```

**Per date:**
- Has attendance → `actual_hours × hourly_rate`
- Weekly off-day → `shift_hours × hourly_rate` (paid off-day)
- Company holiday (is_paid) → `shift_hours × hourly_rate`
- Approved paid leave → `shift_hours × hourly_rate`
- Absent → $0
- Approved overtime → `ot_hours × hourly_rate` (same rate, no multiplier)

---

## Admin Panel

All new models are registered in Django admin:
- **EmployeeShiftHistory**: list by employee, shift, date range
- **Holiday**: list by date, name, paid status
- **Overtime**: list by employee, date, status
- **Employee**: updated fields — `current_shift`, `weekly_off_day`

---

## Migration Steps

Already applied. For fresh setup:
```bash
python manage.py migrate
```

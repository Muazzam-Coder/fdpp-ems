# Frontend API Guide — Shift History, Holidays, Overtime, Updated Payout

## Table of Contents
1. [Employee Changes](#1-employee-changes)
2. [Shift History](#2-shift-history)
3. [Holidays](#3-holidays)
4. [Overtime](#4-overtime)
5. [Updated Payout](#5-updated-payout)
6. [Attendance (unchanged)](#6-attendance-unchanged)

---

## 1. Employee Changes

### Fields Removed
- `shift_type` (string)
- `start_time` (HH:MM)
- `end_time` (HH:MM)

### Fields Added
| Field | Type | Values |
|---|---|---|
| `current_shift` | integer (ID) | Shift ID from `/api/shifts/` |
| `current_shift_detail` | object (read-only) | `{id, name, start_time, end_time}` |
| `weekly_off_day` | integer (null=6) | 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun |

### GET `/api/employees/{emp_id}/` — Response
```json
{
  "emp_id": 1,
  "name": "John",
  "current_shift": 2,
  "current_shift_detail": {
    "id": 2,
    "name": "Night Shift",
    "start_time": "22:00",
    "end_time": "06:00"
  },
  "weekly_off_day": 5,
  "salary": 30000.00,
  ...
}
```

### POST/PUT `/api/employees/{emp_id}/` — Request
```json
{
  "name": "John",
  "current_shift": 2,
  "weekly_off_day": 5,
  "salary": 30000.00,
  ...
}
```

### GET `/api/employees/` — New Filter
| Filter | Type | Example |
|---|---|---|
| `current_shift` | integer | `?current_shift=1` |

---

## 2. Shift History

### POST `/api/employees/{emp_id}/assign_shift/`
Assign a new shift to an employee. Auto-closes the previous shift.

**Request:**
```json
{
  "shift_id": 2,
  "from_date": "2026-06-16"
}
```

**Response (201 Created):**
```json
{
  "id": 5,
  "employee": 1,
  "shift": 2,
  "shift_id": 2,
  "shift_name": "Night Shift",
  "from_date": "2026-06-16",
  "to_date": null,
  "salary": 30000.00,
  "shift_start_time": "22:00",
  "shift_end_time": "06:00"
}
```

### GET `/api/employees/{emp_id}/assign_shift/`
Returns the currently active shift assignment:

```json
{
  "id": 5,
  "employee": 1,
  "shift_name": "Night Shift",
  "from_date": "2026-06-16",
  "to_date": null,
  ...
}
```
Or if none active: `{"detail": "No active shift assignment found."}`

### GET `/api/employees/{emp_id}/shift_history/`
Returns ALL shift assignments, ordered by date descending:

```json
[
  {
    "id": 5,
    "shift_id": 2,
    "shift_name": "Night Shift",
    "from_date": "2026-06-16",
    "to_date": null,
    "salary": 30000.00,
    "shift_start_time": "22:00",
    "shift_end_time": "06:00"
  },
  {
    "id": 4,
    "shift_id": 1,
    "shift_name": "Morning Shift",
    "from_date": "2026-05-01",
    "to_date": "2026-06-15",
    "salary": 28000.00,
    "shift_start_time": "09:00",
    "shift_end_time": "17:00"
  }
]
```

---

## 3. Holidays

Full CRUD at `/api/holidays/`.

### GET `/api/holidays/`
```json
[
  {"id": 1, "date": "2026-06-07", "name": "Eid ul-Adha", "is_paid": true},
  {"id": 2, "date": "2026-12-25", "name": "Christmas", "is_paid": true}
]
```

### POST `/api/holidays/`
```json
{"date": "2026-06-07", "name": "Eid ul-Adha", "is_paid": true}
```

`is_paid` defaults to `true` — paid holidays contribute to salary even when not worked.

---

## 4. Overtime

Full CRUD at `/api/overtime/`.

### POST `/api/overtime/`
```json
{
  "employee": 1,
  "date": "2026-06-10",
  "start_time": "18:00",
  "end_time": "20:00",
  "note": "Inventory count"
}
```

### Response (201 Created)
```json
{
  "id": 1,
  "employee": 1,
  "employee_name": "John",
  "date": "2026-06-10",
  "start_time": "18:00",
  "end_time": "20:00",
  "total_hours": 2.0,
  "status": "pending",
  "approved_by": null,
  "approved_by_name": null,
  "note": "Inventory count",
  "created_at": "2026-06-03T12:00:00",
  "updated_at": "2026-06-03T12:00:00"
}
```

### GET `/api/overtime/` — Filters
| Filter | Example |
|---|---|
| `employee` (emp_id) | `?employee=1` |
| `status` | `?status=pending` |

### POST `/api/overtime/{id}/approve/`
**Request:** empty body

**Response:** Updated overtime record with `status: "approved"` and `approved_by` set.

### POST `/api/overtime/{id}/reject/`
**Request:** empty body

**Response:** Updated overtime record with `status: "rejected"`.

> Overtime is paid at the **same hourly rate** as regular hours (no 1.5× multiplier).

---

## 5. Updated Payout

### GET `/api/employees/{emp_id}/calculate_payout/?start_date=2026-06-01&end_date=2026-06-30`

The payout now:
- Uses **shift history** to determine which shift was active on each date
- Uses **salary snapshot** from each shift assignment period
- Includes **paid holidays** (full shift pay)
- Includes **weekly off-days** (full shift pay)
- Includes **approved paid leaves** (full shift pay)
- Includes **approved overtime** at the same hourly rate
- Calculates hourly rate per shift period based on working days

### Response Shape
```json
{
  "employee_id": 1,
  "employee_name": "John",
  "period": "2026-06-01 to 2026-06-30",
  "salary": 30000.00,
  "shift_periods": [
    {
      "shift_name": "Morning Shift",
      "from_date": "2026-06-01",
      "to_date": "2026-06-15",
      "days_in_period": 15,
      "weekly_off_days": 2,
      "working_days": 13,
      "expected_hours": 104.0,
      "salary_portion": 15000.0,
      "hourly_rate": 144.23,
      "present_days": 12,
      "absent_days": 1,
      "total_worked_hours": 94.5,
      "regular_pay": 13630.24,
      "holiday_pay": 0,
      "leave_pay": 0,
      "off_day_pay": 1153.84,
      "overtime_pay": 0,
      "total_pay": 14784.08
    },
    {
      "shift_name": "Night Shift",
      "from_date": "2026-06-16",
      "to_date": "2026-06-30",
      "days_in_period": 15,
      "weekly_off_days": 2,
      "working_days": 13,
      "expected_hours": 104.0,
      "salary_portion": 15000.0,
      "hourly_rate": 144.23,
      "present_days": 11,
      "absent_days": 2,
      "total_worked_hours": 86.0,
      "regular_pay": 12403.78,
      "holiday_pay": 1153.84,
      "leave_pay": 0,
      "off_day_pay": 1153.84,
      "overtime_pay": 288.46,
      "total_pay": 15000.00
    }
  ],
  "total_present_days": 23,
  "total_absent_days": 3,
  "total_holiday_pay": 1153.84,
  "total_leave_pay": 0,
  "total_off_day_pay": 2307.68,
  "total_overtime_pay": 288.46,
  "total_payout": 29784.08
}
```

### Key Fields Explained
| Field | Meaning |
|---|---|
| `days_in_period` | Calendar days in this shift period within the date range |
| `weekly_off_days` | Count of weekly off-days in this period |
| `working_days` | `days_in_period - weekly_off_days` |
| `expected_hours` | `working_days × shift_hours_per_day` |
| `salary_portion` | `salary × (period_days / month_days)` |
| `hourly_rate` | `salary_portion / expected_hours` |
| `regular_pay` | Actual attendance hours × hourly_rate |
| `off_day_pay` | Full shift pay for weekly off-days |
| `holiday_pay` | Full shift pay for company holidays |
| `leave_pay` | Full shift pay for approved leaves |
| `overtime_pay` | Overtime hours × hourly_rate (same rate, no multiplier) |

---

## 6. Attendance (unchanged)

All attendance endpoints work the same as before:
- `POST /api/attendance/check_in/`
- `POST /api/attendance/auto_attendance/`
- `GET /api/attendance/?date=2026-06-10`
- `GET /api/attendance/daily_report/`
- `GET /api/attendance/weekly_report/`
- `GET /api/attendance/monthly_report/`
- `GET /api/attendance/export_excel/`
- `GET /api/attendance/export_payout/`

> **Behind the scenes**: Check-in now uses the employee's **active shift** from `EmployeeShiftHistory` to determine lateness instead of the old `shift_type`/`start_time`/`end_time` fields.

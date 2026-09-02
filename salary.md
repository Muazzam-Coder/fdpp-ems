List salary history:
GET /api/employees/{emp_id}/salary/
Create new salary (auto-closes previous):
POST /api/employees/{emp_id}/salary/
Content-Type: application/json

{
  "salary": 55000,
  "effective_from": "2026-08-01"
}
Response (201 Created):
{
  "id": 3,
  "employee": 1,
  "salary": "55000.00",
  "effective_from": "2026-08-01",
  "effective_to": null,
  "created_at": "2026-07-14T15:00:00Z"
}
The previous entry (if any) will have effective_to set to "2026-07-31" automatically.
Pay Calculation Updated
Both the comprehensive report and period report now use get_salary_for_date() to pick the correct salary per day instead of a single snapshot. The resolution order is: Salary table → EmployeeShiftHistory.salary → Employee.salary.
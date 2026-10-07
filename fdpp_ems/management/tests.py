from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from datetime import datetime, date, time, timedelta
from django.contrib.auth.models import User
from management.models import (
    Employee, Shift, EmployeeShiftHistory, Attendance,
    get_duty_date_for_check_in, get_employee_shift_times
)

class DutyDateAndAttendanceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(username='admin', password='password123', email='admin@example.com')
        
        # Create shifts
        self.midnight_shift = Shift.objects.create(
            name="Midnight Shift",
            start_time=time(0, 0),
            end_time=time(8, 0)
        )
        self.day_shift = Shift.objects.create(
            name="Day Shift",
            start_time=time(8, 0),
            end_time=time(17, 0)
        )
        self.night_shift = Shift.objects.create(
            name="Night Shift",
            start_time=time(22, 0),
            end_time=time(6, 0)
        )

        # Create employees
        self.emp_midnight = Employee.objects.create(
            emp_id=101,
            name="Midnight Worker",
            status="active",
            current_shift=self.midnight_shift,
            salary=50000,
            hourly_rate=200
        )
        EmployeeShiftHistory.objects.create(
            employee=self.emp_midnight,
            shift=self.midnight_shift,
            from_date=date(2026, 1, 1),
            shift_start_time=time(0, 0),
            shift_end_time=time(8, 0)
        )

        self.emp_day = Employee.objects.create(
            emp_id=102,
            name="Day Worker",
            status="active",
            current_shift=self.day_shift,
            salary=50000,
            hourly_rate=200
        )
        EmployeeShiftHistory.objects.create(
            employee=self.emp_day,
            shift=self.day_shift,
            from_date=date(2026, 1, 1),
            shift_start_time=time(8, 0),
            shift_end_time=time(17, 0)
        )

    def test_get_duty_date_early_midnight_arrival(self):
        """Arriving at 11:50 PM on Oct 6 for a 12:00 AM shift on Oct 7 should resolve to Oct 7."""
        check_in_dt = datetime(2026, 10, 6, 23, 50, 0)
        duty_date = get_duty_date_for_check_in(self.emp_midnight, check_in_dt)
        self.assertEqual(duty_date, date(2026, 10, 7))

    def test_get_duty_date_day_shift_early_arrival(self):
        """Arriving at 06:50 AM on Oct 6 for an 08:00 AM shift on Oct 6 should resolve to Oct 6."""
        check_in_dt = datetime(2026, 10, 6, 6, 50, 0)
        duty_date = get_duty_date_for_check_in(self.emp_day, check_in_dt)
        self.assertEqual(duty_date, date(2026, 10, 6))

    def test_auto_attendance_midnight_early_check_in_and_out(self):
        """Test full check-in and check-out lifecycle for midnight shift early arrival."""
        # 1. Early Check-in at 11:50 PM on Oct 6
        check_in_time = datetime(2026, 10, 6, 23, 50, 0)
        res1 = self.client.post('/api/attendance/auto_attendance/', {
            'emp_id': self.emp_midnight.emp_id,
            'timestamp': check_in_time.strftime('%Y-%m-%d %H:%M:%S')
        })
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res1.data['action'], 'check_in')
        self.assertFalse(res1.data['data']['is_late'])
        self.assertEqual(res1.data['data']['late_message'], 'On time')

        att = Attendance.objects.get(employee=self.emp_midnight)
        self.assertEqual(att.date, date(2026, 10, 7)) # Duty date is Oct 7!
        self.assertEqual(att.status, 'on_time')
        self.assertFalse(att.is_late)

        # 2. Check-out at 08:00 AM on Oct 7
        check_out_time = datetime(2026, 10, 7, 8, 0, 0)
        res2 = self.client.post('/api/attendance/auto_attendance/', {
            'emp_id': self.emp_midnight.emp_id,
            'timestamp': check_out_time.strftime('%Y-%m-%d %H:%M:%S')
        })
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data['action'], 'check_out')
        
        att.refresh_from_db()
        self.assertIsNotNone(att.check_out)
        self.assertEqual(att.date, date(2026, 10, 7))
        # Total hours = 8 hours 10 mins = 8.17 hrs
        self.assertAlmostEqual(att.total_hours, 8.17, places=2)

    def test_auto_attendance_day_shift_early_arrival(self):
        """Test 06:50 AM arrival for 08:00 AM shift."""
        check_in_time = datetime(2026, 10, 6, 6, 50, 0)
        res1 = self.client.post('/api/attendance/auto_attendance/', {
            'emp_id': self.emp_day.emp_id,
            'timestamp': check_in_time.strftime('%Y-%m-%d %H:%M:%S')
        })
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res1.data['action'], 'check_in')
        self.assertFalse(res1.data['data']['is_late'])
        self.assertEqual(res1.data['data']['late_message'], 'On time')

        att = Attendance.objects.get(employee=self.emp_day)
        self.assertEqual(att.date, date(2026, 10, 6))
        self.assertEqual(att.status, 'on_time')
        self.assertFalse(att.is_late)

    def test_attendance_lateness_calculation(self):
        """Test lateness beyond grace period (10 minutes)."""
        # Check-in at 00:15 on Oct 7 for 00:00 shift -> 15 min late
        late_check_in = datetime(2026, 10, 7, 0, 15, 0)
        res = self.client.post('/api/attendance/auto_attendance/', {
            'emp_id': self.emp_midnight.emp_id,
            'timestamp': late_check_in.strftime('%Y-%m-%d %H:%M:%S')
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data['data']['is_late'])
        self.assertEqual(res.data['data']['late_message'], '15m late')

        att = Attendance.objects.get(employee=self.emp_midnight)
        self.assertEqual(att.status, 'late')
        self.assertTrue(att.is_late)

    def test_overnight_shift_early_arrival_and_checkout(self):
        """Test overnight shift (22:00 - 06:00) arriving early at 21:50 on Oct 6."""
        emp_night = Employee.objects.create(
            emp_id=103,
            name="Night Worker",
            status="active",
            current_shift=self.night_shift,
            salary=55000,
            hourly_rate=220
        )
        EmployeeShiftHistory.objects.create(
            employee=emp_night,
            shift=self.night_shift,
            from_date=date(2026, 1, 1),
            shift_start_time=time(22, 0),
            shift_end_time=time(6, 0)
        )

        # 1. Early arrival at 21:50 on Oct 6
        check_in_time = datetime(2026, 10, 6, 21, 50, 0)
        res1 = self.client.post('/api/attendance/auto_attendance/', {
            'emp_id': emp_night.emp_id,
            'timestamp': check_in_time.strftime('%Y-%m-%d %H:%M:%S')
        })
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertFalse(res1.data['data']['is_late'])
        self.assertEqual(res1.data['data']['late_message'], 'On time')

        att = Attendance.objects.get(employee=emp_night)
        self.assertEqual(att.date, date(2026, 10, 6))
        self.assertEqual(att.status, 'on_time')
        self.assertFalse(att.is_late)

        # 2. Check-out at 06:00 AM on Oct 7
        check_out_time = datetime(2026, 10, 7, 6, 0, 0)
        res2 = self.client.post('/api/attendance/auto_attendance/', {
            'emp_id': emp_night.emp_id,
            'timestamp': check_out_time.strftime('%Y-%m-%d %H:%M:%S')
        })
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data['action'], 'check_out')

        att.refresh_from_db()
        self.assertAlmostEqual(att.total_hours, 8.17, places=2)

    def test_multiple_punches_and_detailed_logs(self):
        """Test split/multiple check-ins on the same day:
        Session 1: 08:05 AM to 04:00 PM (7h 55m = 7.92 hrs)
        Session 2: 08:00 PM to 11:00 PM (3h 0m = 3.00 hrs)
        Total: 10h 55m = 10.92 hrs
        """
        self.client.force_authenticate(user=self.admin_user)

        # Create 2 attendance sessions on Oct 6
        att1 = Attendance.objects.create(
            employee=self.emp_day,
            date=date(2026, 10, 6),
            check_in=datetime(2026, 10, 6, 8, 5, 0),
            check_out=datetime(2026, 10, 6, 16, 0, 0),
            status='on_time',
            message_late='On time'
        )
        att2 = Attendance.objects.create(
            employee=self.emp_day,
            date=date(2026, 10, 6),
            check_in=datetime(2026, 10, 6, 20, 0, 0),
            check_out=datetime(2026, 10, 6, 23, 0, 0),
            status='on_time',
            message_late='On time'
        )

        # 1. Test detailed employee logs endpoint
        res = self.client.get('/api/attendance/employee_logs/', {
            'emp_id': self.emp_day.emp_id,
            'date': '2026-10-06'
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['summary']['total_sessions'], 2)
        self.assertEqual(res.data['summary']['total_hours'], '10h 55m')
        self.assertAlmostEqual(res.data['summary']['total_hours_value'], 10.92, places=2)
        # Expected pay = 10.92 * 200 = 2184.00
        self.assertAlmostEqual(res.data['summary']['estimated_pay'], 2184.0, places=1)

        day_log = res.data['daily_logs'][0]
        self.assertEqual(day_log['total_sessions'], 2)
        self.assertEqual(day_log['first_check_in'], '08:05:00 AM')
        self.assertEqual(day_log['last_check_out'], '11:00:00 PM')
        self.assertEqual(len(day_log['sessions']), 2)
        self.assertEqual(day_log['sessions'][0]['total_hours'], '7h 55m')
        self.assertEqual(day_log['sessions'][1]['total_hours'], '3h 0m')

        # 2. Test detailed logs via EmployeeViewSet detail action
        res_detail = self.client.get(f'/api/employees/{self.emp_day.emp_id}/detailed_logs/?date=2026-10-06')
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data['summary']['total_hours_value'], 10.92)

        # 3. Test daily_report consolidation (should return 1 consolidated record for emp_day)
        res_daily = self.client.get('/api/attendance/daily_report/?date=2026-10-06')
        self.assertEqual(res_daily.status_code, status.HTTP_200_OK)
        emp_records = [r for r in res_daily.data['attendance_details'] if r['employee'] == self.emp_day.emp_id]
        self.assertEqual(len(emp_records), 1)
        record = emp_records[0]
        self.assertEqual(record['check_in'], '08:05:00 AM')
        self.assertEqual(record['check_out'], '11:00:00 PM')
        self.assertEqual(record['total_hours'], '10h 55m')
        self.assertAlmostEqual(record['total_hours_value'], 10.92, places=2)
        self.assertEqual(record['sessions_count'], 2)

        # 4. Test Comprehensive Report View does not raise 500 and returns proper summary
        res_comp = self.client.get('/api/reports/comprehensive/', {
            'start_date': '2026-10-01',
            'end_date': '2026-10-29',
            'format': 'json',
            'employee_ids': str(self.emp_day.emp_id)
        })
        self.assertEqual(res_comp.status_code, status.HTTP_200_OK)
        emp_summary = res_comp.data['summary'].get(str(self.emp_day.emp_id))
        self.assertIsNotNone(emp_summary)
        self.assertAlmostEqual(emp_summary['total_hours'], 10.92, places=2)
        self.assertEqual(emp_summary['days_present'], 1)

    def test_user_creation_and_editing_optional_email_compulsory_username(self):
        """Test that username is compulsory and email is optional when creating or editing users."""
        self.client.force_authenticate(user=self.admin_user)

        # 1. Register without email -> Should Succeed (201)
        res_reg = self.client.post('/api/auth/register/', {
            'username': 'no_email_user',
            'password': 'password123',
            'first_name': 'No Email',
            'designation': 'Worker'
        })
        self.assertEqual(res_reg.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_reg.data['user']['username'], 'no_email_user')
        self.assertEqual(res_reg.data['user']['email'], '')

        # 2. Register without username -> Should Fail (400)
        res_no_user = self.client.post('/api/auth/register/', {
            'password': 'password123',
            'email': 'test@example.com'
        })
        self.assertEqual(res_no_user.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', res_no_user.data)

        # 3. Create admin/manager without email -> Should Succeed (201)
        res_admin = self.client.post('/api/auth/create_admin_manager/', {
            'username': 'new_manager',
            'password': 'password123',
            'role': 'manager',
            'first_name': 'Manager'
        })
        self.assertEqual(res_admin.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_admin.data['user']['username'], 'new_manager')

        # 4. Edit user access level via PUT with full payload (as sent by frontend)
        from management.models import UserAccessLevel
        ual = UserAccessLevel.objects.get(user__username='new_manager')
        res_put = self.client.put(f'/api/access-levels/{ual.id}/', {
            "username": "Khadaija",
            "email": "khadijasheikh3355@gmail.com",
            "first_name": "khadija",
            "last_name": "umer farooq",
            "role": "admin",
            "address": "",
            "r_address": "",
            "r_phone": "",
            "relative": "",
            "start_time": "09:00:00",
            "end_time": "17:00:00"
        })
        self.assertEqual(res_put.status_code, status.HTTP_200_OK)
        ual.refresh_from_db()
        self.assertEqual(ual.user.username, "Khadaija")
        self.assertEqual(ual.user.email, "khadijasheikh3355@gmail.com")
        self.assertEqual(ual.user.first_name, "khadija")
        self.assertEqual(ual.user.last_name, "umer farooq")

    def test_password_update_endpoints(self):
        """Test all password update/change endpoints."""
        self.client.force_authenticate(user=self.admin_user)

        # 1. Create a user to test password changes
        res_create = self.client.post('/api/auth/register/', {
            'username': 'pwd_test_user',
            'password': 'initial_password123',
            'first_name': 'Password',
            'last_name': 'Tester'
        })
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='pwd_test_user')

        # 2. Test POST /api/auth/change_password/ as regular user (requires old_password)
        self.client.force_authenticate(user=user)
        # 2a. Incorrect old password -> 400
        res_bad_old = self.client.post('/api/auth/change_password/', {
            'old_password': 'wrong_password',
            'new_password': 'new_secure_password123'
        })
        self.assertEqual(res_bad_old.status_code, status.HTTP_400_BAD_REQUEST)

        # 2b. Correct old password -> 200
        res_good = self.client.post('/api/auth/change_password/', {
            'old_password': 'initial_password123',
            'new_password': 'new_secure_password123'
        })
        self.assertEqual(res_good.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password('new_secure_password123'))

        # 3. Test POST /api/auth/update_password/ as admin (resetting another user's password)
        self.client.force_authenticate(user=self.admin_user)
        res_admin_update = self.client.post('/api/auth/update_password/', {
            'username': 'pwd_test_user',
            'new_password': 'admin_reset_password123'
        })
        self.assertEqual(res_admin_update.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password('admin_reset_password123'))

        # 4. Test POST /api/access-levels/{id}/change_password/
        from management.models import UserAccessLevel
        ual, _ = UserAccessLevel.objects.get_or_create(user=user, defaults={'role': 'manager'})
        res_ual_pwd = self.client.post(f'/api/access-levels/{ual.id}/change_password/', {
            'password': 'ual_password_change123'
        })
        self.assertEqual(res_ual_pwd.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password('ual_password_change123'))

        # 5. Test POST /api/employees/{emp_id}/change_password/
        emp = user.employee_profile
        res_emp_pwd = self.client.post(f'/api/employees/{emp.emp_id}/change_password/', {
            'password': 'emp_password_change123'
        })
        self.assertEqual(res_emp_pwd.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password('emp_password_change123'))

        # 6. Test POST /api/users/{id}/change_password/ without access-level in URL
        res_users_pwd = self.client.post(f'/api/users/{ual.id}/change_password/', {
            'password': 'direct_user_pwd123'
        })
        self.assertEqual(res_users_pwd.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password('direct_user_pwd123'))


class ActivityLogTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            username='admin_audit',
            password='password123',
            email='admin_audit@example.com'
        )
        from management.models import UserAccessLevel
        UserAccessLevel.objects.filter(user=self.admin_user).update(role='admin')

        self.shift = Shift.objects.create(
            name="General Shift",
            start_time=time(9, 0),
            end_time=time(17, 0)
        )

    def test_login_activity_logging(self):
        """Test that both successful and failed logins generate activity logs."""
        from management.models import ActivityLog
        initial_count = ActivityLog.objects.count()

        # 1. Successful login
        res_success = self.client.post('/api/auth/login/', {
            'username': 'admin_audit',
            'password': 'password123'
        })
        self.assertEqual(res_success.status_code, status.HTTP_200_OK)
        log_success = ActivityLog.objects.filter(action_type='login_success').first()
        self.assertIsNotNone(log_success)
        self.assertEqual(log_success.actor_username, 'admin_audit')
        self.assertEqual(log_success.category, 'auth')

        # 2. Failed login
        res_fail = self.client.post('/api/auth/login/', {
            'username': 'non_existent_user',
            'password': 'wrongpassword'
        })
        self.assertEqual(res_fail.status_code, status.HTTP_401_UNAUTHORIZED)
        log_fail = ActivityLog.objects.filter(action_type='login_failed').first()
        self.assertIsNotNone(log_fail)
        self.assertEqual(log_fail.category, 'auth')

    def test_employee_crud_and_lifecycle_logging(self):
        """Test activity logging for employee creation, update, deactivation, reactivation, and deletion."""
        from management.models import ActivityLog
        self.client.force_authenticate(user=self.admin_user)

        # 1. Create employee
        res_create = self.client.post('/api/employees/', {
            'name': 'Audit Employee',
            'designation': 'Software Engineer',
            'status': 'active',
            'current_shift': self.shift.id,
            'phone': '1234567890',
            'salary': 75000,
            'hourly_rate': 300
        })
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        emp_id = res_create.data['emp_id']
        log_create = ActivityLog.objects.filter(action_type='employee_create', target_id=str(emp_id)).first()
        self.assertIsNotNone(log_create)
        self.assertEqual(log_create.category, 'employee')

        # 2. Update employee status to inactive (deactivation)
        res_deact = self.client.patch(f'/api/employees/{emp_id}/', {
            'status': 'inactive'
        })
        self.assertEqual(res_deact.status_code, status.HTTP_200_OK)
        log_deact = ActivityLog.objects.filter(action_type='employee_deactivate', target_id=str(emp_id)).first()
        self.assertIsNotNone(log_deact)
        self.assertIn('Deactivated', log_deact.description)

        # 3. Reactivate employee
        res_react = self.client.patch(f'/api/employees/{emp_id}/', {
            'status': 'active'
        })
        self.assertEqual(res_react.status_code, status.HTTP_200_OK)
        log_react = ActivityLog.objects.filter(action_type='employee_activate', target_id=str(emp_id)).first()
        self.assertIsNotNone(log_react)

        # 4. Assign shift and update salary
        new_shift = Shift.objects.create(name="Evening Shift", start_time=time(16, 0), end_time=time(0, 0))
        res_shift = self.client.post(f'/api/employees/{emp_id}/assign_shift/', {
            'shift_id': new_shift.id,
            'from_date': '2026-10-01'
        })
        self.assertEqual(res_shift.status_code, status.HTTP_201_CREATED)
        log_shift = ActivityLog.objects.filter(action_type='shift_assign', target_id=str(emp_id)).first()
        self.assertIsNotNone(log_shift)

        res_salary = self.client.post(f'/api/employees/{emp_id}/salary/', {
            'salary': 85000,
            'effective_from': '2026-10-01'
        })
        self.assertEqual(res_salary.status_code, status.HTTP_201_CREATED)
        log_salary = ActivityLog.objects.filter(action_type='salary_update', target_id=str(emp_id)).first()
        self.assertIsNotNone(log_salary)

        # 5. Delete employee
        res_delete = self.client.delete(f'/api/employees/{emp_id}/')
        self.assertEqual(res_delete.status_code, status.HTTP_204_NO_CONTENT)
        log_delete = ActivityLog.objects.filter(action_type='employee_delete', target_id=str(emp_id)).first()
        self.assertIsNotNone(log_delete)

    def test_user_management_and_password_logging(self):
        """Test logging for user creation, role update, user deletion, and password reset."""
        from management.models import ActivityLog, UserAccessLevel
        self.client.force_authenticate(user=self.admin_user)

        # 1. Create admin/manager
        res_create_user = self.client.post('/api/auth/create_admin_manager/', {
            'username': 'manager_audit',
            'password': 'Password123!',
            'role': 'manager',
            'email': 'manager@audit.com',
            'first_name': 'Manager',
            'last_name': 'Audit'
        })
        self.assertEqual(res_create_user.status_code, status.HTTP_201_CREATED)
        log_create_user = ActivityLog.objects.filter(action_type='create_admin_manager').first()
        self.assertIsNotNone(log_create_user)

        user_id = res_create_user.data['user']['id']
        ual = UserAccessLevel.objects.get(user_id=user_id)

        # 2. Update user role
        res_update_role = self.client.patch(f'/api/users/{ual.id}/', {
            'role': 'admin'
        })
        self.assertEqual(res_update_role.status_code, status.HTTP_200_OK)
        log_role = ActivityLog.objects.filter(action_type='role_change').first()
        self.assertIsNotNone(log_role)

        # 3. Change user password
        res_pwd = self.client.post(f'/api/users/{ual.id}/change_password/', {
            'password': 'NewPassword123!'
        })
        self.assertEqual(res_pwd.status_code, status.HTTP_200_OK)
        log_pwd = ActivityLog.objects.filter(action_type='password_change', target_id=str(user_id)).first()
        self.assertIsNotNone(log_pwd)

        # 4. Delete user access level
        res_del_user = self.client.delete(f'/api/users/{ual.id}/')
        self.assertEqual(res_del_user.status_code, status.HTTP_204_NO_CONTENT)
        log_del_user = ActivityLog.objects.filter(action_type='user_delete').first()
        self.assertIsNotNone(log_del_user)

    def test_attendance_leave_and_overtime_logging(self):
        """Test logging for attendance, paid leave, and overtime actions."""
        from management.models import ActivityLog, PaidLeave, Overtime
        self.client.force_authenticate(user=self.admin_user)

        emp = Employee.objects.create(
            emp_id=601,
            name="Audit Staff",
            status="active",
            current_shift=self.shift,
            salary=60000,
            hourly_rate=250
        )

        # 1. Manual Attendance Create
        res_att_create = self.client.post('/api/attendance/', {
            'employee': 601,
            'date': '2026-10-06',
            'check_in_time': '09:00:00',
            'status': 'on_time'
        })
        self.assertEqual(res_att_create.status_code, status.HTTP_201_CREATED)
        log_att_create = ActivityLog.objects.filter(action_type='attendance_manual_create').first()
        self.assertIsNotNone(log_att_create)

        att_id = res_att_create.data['id']

        # 2. Attendance Update & Delete
        res_att_upd = self.client.patch(f'/api/attendance/{att_id}/', {
            'status': 'late',
            'message_late': '15m late'
        })
        self.assertEqual(res_att_upd.status_code, status.HTTP_200_OK)
        log_att_upd = ActivityLog.objects.filter(action_type='attendance_update').first()
        self.assertIsNotNone(log_att_upd)

        res_att_del = self.client.delete(f'/api/attendance/{att_id}/')
        self.assertEqual(res_att_del.status_code, status.HTTP_204_NO_CONTENT)
        log_att_del = ActivityLog.objects.filter(action_type='attendance_delete').first()
        self.assertIsNotNone(log_att_del)

        # 3. Paid Leave Apply & Approve
        res_leave = self.client.post('/api/leave/', {
            'employee': 601,
            'leave_type': 'casual',
            'start_time': '2026-10-10T09:00:00',
            'end_time': '2026-10-11T17:00:00',
            'reason': 'Family emergency'
        })
        self.assertEqual(res_leave.status_code, status.HTTP_201_CREATED)
        leave_id = res_leave.data['id']
        log_leave_apply = ActivityLog.objects.filter(action_type='leave_apply').first()
        self.assertIsNotNone(log_leave_apply)

        res_leave_app = self.client.post(f'/api/leave/{leave_id}/approve/', {
            'approved_by': 'Admin'
        })
        self.assertEqual(res_leave_app.status_code, status.HTTP_200_OK)
        log_leave_app = ActivityLog.objects.filter(action_type='leave_approve').first()
        self.assertIsNotNone(log_leave_app)

        # 4. Overtime Create & Approve
        res_ot = self.client.post('/api/overtime/', {
            'employee': 601,
            'date': '2026-10-06',
            'start_time': '17:00:00',
            'end_time': '19:00:00',
            'status': 'pending'
        })
        self.assertEqual(res_ot.status_code, status.HTTP_201_CREATED)
        ot_id = res_ot.data['id']
        log_ot_create = ActivityLog.objects.filter(action_type='overtime_create').first()
        self.assertIsNotNone(log_ot_create)

        res_ot_app = self.client.post(f'/api/overtime/{ot_id}/approve/')
        self.assertEqual(res_ot_app.status_code, status.HTTP_200_OK)
        log_ot_app = ActivityLog.objects.filter(action_type='overtime_approve').first()
        self.assertIsNotNone(log_ot_app)

    def test_activities_api_endpoints_and_filtering(self):
        """Test GET /api/activities/, search, filtering, summary, and categories endpoints."""
        from management.models import ActivityLog, log_activity
        self.client.force_authenticate(user=self.admin_user)

        # Create sample logs
        log_activity(
            actor=self.admin_user,
            action_type='employee_create',
            category='employee',
            description='Test employee creation audit',
            target_model='Employee',
            target_id='999',
            target_name='Test Person'
        )
        log_activity(
            actor=self.admin_user,
            action_type='password_change',
            category='auth',
            description='Admin changed password for user test',
            target_model='User',
            target_id='10',
            target_name='testuser'
        )

        # 1. List activities
        res_list = self.client.get('/api/activities/')
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertIn('results', res_list.data)
        self.assertGreaterEqual(res_list.data['count'], 2)

        # 2. Filter by category
        res_cat = self.client.get('/api/activities/?category=employee')
        self.assertEqual(res_cat.status_code, status.HTTP_200_OK)
        for item in res_cat.data['results']:
            self.assertEqual(item['category'], 'employee')

        # 3. Search query
        res_search = self.client.get('/api/activities/?search=Test Person')
        self.assertEqual(res_search.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res_search.data['results']), 1)

        # 4. Summary endpoint
        res_sum = self.client.get('/api/activities/summary/')
        self.assertEqual(res_sum.status_code, status.HTTP_200_OK)
        self.assertIn('total_activities', res_sum.data)
        self.assertIn('categories_breakdown', res_sum.data)
        self.assertIn('top_actions', res_sum.data)
        self.assertIn('recent_activities', res_sum.data)

        # 5. Categories endpoint
        res_cats = self.client.get('/api/activities/categories/')
        self.assertEqual(res_cats.status_code, status.HTTP_200_OK)
        self.assertIn('categories', res_cats.data)
        self.assertIn('actions', res_cats.data)

    def test_daily_report_search_and_filters(self):
        """Test search, employee filter, and status filter on daily_report endpoint."""
        self.client.force_authenticate(user=self.admin_user)
        emp1 = Employee.objects.create(
            emp_id=9987,
            name="Bob Builder",
            designation="Engineer",
            salary=60000,
            status='active'
        )
        emp2 = Employee.objects.create(
            emp_id=9988,
            name="Alice Wonder",
            designation="Designer",
            salary=50000,
            status='active'
        )
        Attendance.objects.create(
            employee=emp1,
            date=date(2026, 10, 6),
            check_in=datetime(2026, 10, 6, 9, 0, 0),
            check_out=datetime(2026, 10, 6, 17, 0, 0),
            status='on_time'
        )
        Attendance.objects.create(
            employee=emp2,
            date=date(2026, 10, 6),
            check_in=datetime(2026, 10, 6, 10, 30, 0),
            check_out=datetime(2026, 10, 6, 17, 0, 0),
            status='late'
        )

        # 1. Base daily report
        res_all = self.client.get('/api/attendance/daily_report/?date=2026-10-06')
        self.assertEqual(res_all.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_all.data['attendance_details']), 2)

        # 2. Search by employee name 'Alice'
        res_search_name = self.client.get('/api/attendance/daily_report/?date=2026-10-06&search=Alice')
        self.assertEqual(res_search_name.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_search_name.data['attendance_details']), 1)
        self.assertEqual(res_search_name.data['attendance_details'][0]['employee_name'], 'Alice Wonder')

        # 3. Search by emp_id '9988'
        res_search_id = self.client.get('/api/attendance/daily_report/?date=2026-10-06&search=9988')
        self.assertEqual(res_search_id.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_search_id.data['attendance_details']), 1)
        self.assertEqual(res_search_id.data['attendance_details'][0]['employee'], 9988)

        # 4. Filter by status 'late'
        res_late = self.client.get('/api/attendance/daily_report/?date=2026-10-06&status=late')
        self.assertEqual(res_late.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_late.data['attendance_details']), 1)
        self.assertEqual(res_late.data['attendance_details'][0]['employee'], 9988)

        # 5. Filter by status 'on_time'
        res_ontime = self.client.get('/api/attendance/daily_report/?date=2026-10-06&status=on_time')
        self.assertEqual(res_ontime.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_ontime.data['attendance_details']), 1)
        self.assertEqual(res_ontime.data['attendance_details'][0]['employee'], 9987)

        # 6. Filter by employee param
        res_emp = self.client.get(f'/api/attendance/daily_report/?date=2026-10-06&employee=9987')
        self.assertEqual(res_emp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_emp.data['attendance_details']), 1)
        self.assertEqual(res_emp.data['attendance_details'][0]['employee'], 9987)








from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EmployeeViewSet, AttendanceViewSet, PaidLeaveViewSet, ShiftViewSet, 
    AuthViewSet, UserAccessLevelViewSet, HolidayViewSet, OvertimeViewSet,
    ActivityLogViewSet,
    ComprehensiveReportView,
)
from .views import employee_list

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'attendance', AttendanceViewSet, basename='attendance')
router.register(r'attendances', AttendanceViewSet, basename='attendances')
router.register(r'leave', PaidLeaveViewSet, basename='leave')
router.register(r'leaves', PaidLeaveViewSet, basename='leaves')
router.register(r'shifts', ShiftViewSet, basename='shift')
router.register(r'holidays', HolidayViewSet, basename='holiday')
router.register(r'overtime', OvertimeViewSet, basename='overtime')
router.register(r'access-levels', UserAccessLevelViewSet, basename='access-level')
router.register(r'users', UserAccessLevelViewSet, basename='user')
router.register(r'activities', ActivityLogViewSet, basename='activity')
router.register(r'activity-logs', ActivityLogViewSet, basename='activity-log')

urlpatterns = [
    path('employee_list/', employee_list, name='employee_list'),
    path('reports/comprehensive/', ComprehensiveReportView.as_view(), name='comprehensive_report'),
    path('', include(router.urls)),
]

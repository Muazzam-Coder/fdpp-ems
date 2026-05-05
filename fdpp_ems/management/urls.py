from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EmployeeViewSet, AttendanceViewSet, PaidLeaveViewSet, ShiftViewSet, 
    AuthViewSet, UserAccessLevelViewSet
)

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'attendance', AttendanceViewSet, basename='attendance')
# Also register plural alias so clients using /attendances/ continue to work
router.register(r'attendances', AttendanceViewSet, basename='attendances')
router.register(r'leave', PaidLeaveViewSet, basename='leave')
router.register(r'shifts', ShiftViewSet, basename='shift')
router.register(r'access-levels', UserAccessLevelViewSet, basename='access-level')

urlpatterns = [
    path('', include(router.urls)),
]
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory
from management.models import Employee
from management.views import EmployeeViewSet

# Ensure a test user exists
user, _ = User.objects.get_or_create(username='test_relatives_user', defaults={'email':'test@local','password':'notused'})

# Create uniquely named employees to avoid clobbering fixtures
base = 'auto_test'
A = Employee.objects.create(name=f'EmpA_{base}')
B = Employee.objects.create(name=f'EmpB_{base}')
T = Employee.objects.create(name=f'EmpT_{base}')

# Link relatives: B <-> A, T <-> B
B.relatives.add(A)
T.relatives.add(B)

# Call the view
factory = APIRequestFactory()

from rest_framework.test import force_authenticate
request = factory.get('/employees/relatives/', {'emp_id': A.emp_id, 'transitive': 'true'})
force_authenticate(request, user=user)

view = EmployeeViewSet.as_view({'get': 'relatives'})
response = view(request)

print('STATUS:', response.status_code)
print(response.data)

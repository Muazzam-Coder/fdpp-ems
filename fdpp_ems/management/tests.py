from django.test import TestCase

# Management test suite
class SystemSanityTest(TestCase):
    def test_environment_loads(self):
        self.assertTrue(True)

import django
from django.test import TestCase

class DjangoProjectTestCase(TestCase):
    def test_django_1_11(self):
        django_major_minor = '.'.join(django.__version__.split('.')[:2])
        self.assertEquals(django_major_minor, '1.11')

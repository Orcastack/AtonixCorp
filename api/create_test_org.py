import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_api.settings')
django.setup()

from django.contrib.auth.models import User
from finances.models import Organization

# Create a test user if it doesn't exist
user, created = User.objects.get_or_create(
    username='testuser',
    defaults={'email': 'test@example.com'}
)
if created:
    user.set_password('testpass123')
    user.save()
    print(f"Created test user: {user.username}")
else:
    print(f"User already exists: {user.username}")

# Create a test organization if it doesn't exist
org, created = Organization.objects.get_or_create(
    id=1,
    defaults={
        'owner': user,
        'name': 'Ledgora',
        'slug': 'atonix-capital',
        'description': 'Test organization',
        'industry': 'Financial Services',
        'employee_count': 50,
        'primary_currency': 'US',
        'primary_country': 'South Africa'
    }
)
if created:
    print(f"Created organization: {org.name} (id={org.id})")
else:
    print(f"Organization already exists: {org.name} (id={org.id})")

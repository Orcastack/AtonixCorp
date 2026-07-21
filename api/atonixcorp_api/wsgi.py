"""Legacy WSGI compatibility entry point for the AtonixCorp API project."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atonixcorp_api.settings')

application = get_wsgi_application()

"""ASGI config for the AtonixCorp API project."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atonixcorp_api.settings')

application = get_asgi_application()
"""Django settings for finance_api project."""

import os
from pathlib import Path

import dj_database_url

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=''):
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(',') if item.strip()]

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-your-secret-key-here-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool('DJANGO_DEBUG', True)

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')

if not DEBUG:
    if SECRET_KEY.startswith('django-insecure-') or len(SECRET_KEY) < 50:
        raise RuntimeError('DJANGO_SECRET_KEY must be a unique, random value of at least 50 characters in production.')
    if not ALLOWED_HOSTS:
        raise RuntimeError('DJANGO_ALLOWED_HOSTS must list the production hostnames when DJANGO_DEBUG is false.')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'finances',
    'workspaces',
    'equity',
    'intelligence',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'finance_api.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'finance_api.wsgi.application'

# Database
DATABASES = {
    'default': dj_database_url.parse(
        os.getenv('DATABASE_URL', f'sqlite:///{BASE_DIR / "db.sqlite3"}'),
        conn_max_age=int(os.getenv('DB_CONN_MAX_AGE', '60')),
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
WORKSPACE_FILE_ENCRYPTION_KEY = os.getenv('WORKSPACE_FILE_ENCRYPTION_KEY', '')
WORKSPACE_FILE_MAX_BYTES = int(os.getenv('WORKSPACE_FILE_MAX_BYTES', str(25 * 1024 * 1024)))
WORKSPACE_FILE_STORAGE_BACKEND = os.getenv('WORKSPACE_FILE_STORAGE_BACKEND', 'django.core.files.storage.FileSystemStorage')
if not DEBUG and not WORKSPACE_FILE_ENCRYPTION_KEY:
    raise RuntimeError('WORKSPACE_FILE_ENCRYPTION_KEY is required when DJANGO_DEBUG is false.')
STORAGES = {
    'default': {
        'BACKEND': WORKSPACE_FILE_STORAGE_BACKEND,
        'OPTIONS': {},
    },
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
if WORKSPACE_FILE_STORAGE_BACKEND == 'storages.backends.s3.S3Storage':
    STORAGES['default']['OPTIONS'] = {
        'bucket_name': os.getenv('AWS_STORAGE_BUCKET_NAME', ''),
        'region_name': os.getenv('AWS_S3_REGION_NAME', ''),
        'access_key': os.getenv('AWS_ACCESS_KEY_ID', ''),
        'secret_key': os.getenv('AWS_SECRET_ACCESS_KEY', ''),
        'default_acl': None,
        'querystring_auth': True,
        'file_overwrite': False,
    }

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'finances.v1_auth.APIKeyAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_THROTTLE_RATES': {
        'v1_org_burst': '120/minute',
        'v1_endpoint': '30/minute',
        'tax_api_burst': '90/minute',
        'tax_api_write': '20/minute',
    },
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS settings
CORS_ALLOWED_ORIGINS = env_list(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001'
)

CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = env_list(
    'CSRF_TRUSTED_ORIGINS',
    'http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001'
)

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', not DEBUG)
SESSION_COOKIE_SECURE = env_bool('DJANGO_SESSION_COOKIE_SECURE', not DEBUG)
CSRF_COOKIE_SECURE = env_bool('DJANGO_CSRF_COOKIE_SECURE', not DEBUG)
SECURE_HSTS_SECONDS = int(os.getenv('DJANGO_SECURE_HSTS_SECONDS', '31536000')) if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', not DEBUG)
SECURE_HSTS_PRELOAD = env_bool('DJANGO_SECURE_HSTS_PRELOAD', not DEBUG)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = os.getenv('DJANGO_SECURE_REFERRER_POLICY', 'same-origin')
X_FRAME_OPTIONS = 'DENY'

PLATFORM_EVENT_TOKEN = os.getenv('PLATFORM_EVENT_TOKEN', '')
PLATFORM_EVENT_LOGGER = os.getenv('PLATFORM_EVENT_LOGGER', 'platform_events')
APP_VERSION = os.getenv('APP_VERSION', 'dev')
DEPLOYMENT_ENVIRONMENT = os.getenv('DEPLOYMENT_ENVIRONMENT', 'local')
ATONIXCORP_API_ENVIRONMENT = os.getenv(
    'ATONIXCORP_API_ENVIRONMENT',
    os.getenv('ATONIXCORP_API_ENVIRONMENT', 'sandbox' if DEBUG else 'production'),
)
BANKING_TOKEN_ENCRYPTION_KEY = os.getenv('BANKING_TOKEN_ENCRYPTION_KEY', '')
FRONTEND_BASE_URL = os.getenv('FRONTEND_BASE_URL', 'http://localhost:3000')
APPROVAL_NOTIFICATION_BASE_URL = os.getenv('APPROVAL_NOTIFICATION_BASE_URL', FRONTEND_BASE_URL)

EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '25'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', not DEBUG)
EMAIL_USE_SSL = env_bool('EMAIL_USE_SSL', False)
if EMAIL_USE_TLS and EMAIL_USE_SSL:
    raise RuntimeError('EMAIL_USE_TLS and EMAIL_USE_SSL cannot both be enabled.')
if not DEBUG and EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend' and not (EMAIL_USE_TLS or EMAIL_USE_SSL):
    raise RuntimeError('Production SMTP delivery requires EMAIL_USE_TLS or EMAIL_USE_SSL.')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'no-reply@atonixcorp.local')
ORGANIZATION_EMAIL_DOMAIN = os.getenv('ORGANIZATION_EMAIL_DOMAIN', 'atonixcorp.local')
EMAIL_BRAND_NAME = os.getenv('EMAIL_BRAND_NAME', 'AtonixCorp')
EMAIL_BRAND_TITLE = os.getenv('EMAIL_BRAND_TITLE', 'Institutional Finance Operations')
EMAIL_BRAND_FOOTER = os.getenv(
    'EMAIL_BRAND_FOOTER',
    'AtonixCorp finance operations communications are designed for secure approval workflows, accountable execution, and institutional-grade control.',
)
EMAIL_SUPPORT_EMAIL = os.getenv('EMAIL_SUPPORT_EMAIL', 'support@atonixcorp.local')
EMAIL_SUPPORT_URL = os.getenv('EMAIL_SUPPORT_URL', FRONTEND_BASE_URL)

AI_ENABLE_EXTERNAL_MODELS = env_bool('AI_ENABLE_EXTERNAL_MODELS', False)
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
ANTHROPIC_API_BASE_URL = os.getenv('ANTHROPIC_API_BASE_URL', 'https://api.anthropic.com')
CLAUDE_OPUS_MODEL = os.getenv('CLAUDE_OPUS_MODEL', 'claude-opus-4-1')
CLAUDE_SONNET_MODEL = os.getenv('CLAUDE_SONNET_MODEL', 'claude-sonnet-4-0')
AI_DEFAULT_MAX_TOKENS = int(os.getenv('AI_DEFAULT_MAX_TOKENS', '2000'))

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'structured': {
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'structured',
        }
    },
    'loggers': {
        'platform_events': {
            'handlers': ['console'],
            'level': os.getenv('PLATFORM_EVENT_LOG_LEVEL', 'INFO'),
            'propagate': False,
        }
    }
}

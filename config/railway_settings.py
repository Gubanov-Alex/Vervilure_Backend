"""
Railway-specific Django settings.
This file extends base settings and configures production environment.
"""

import os
import dj_database_url

# IMPORTANT: Set this before importing base settings to prevent .env loading
os.environ['RAILWAY_ENVIRONMENT'] = 'production'

# Import base settings
from .settings import *

# Railway Production Settings
DEBUG = False

# Security - use Railway's provided SECRET_KEY
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set in Railway environment variables")

# Allowed hosts
ALLOWED_HOSTS = [
    '.railway.app',
    '.up.railway.app',
    'hospitable-intuition-deveop.up.railway.app',
    'hospitable-intuition-production.up.railway.app',
    'hospitable-intuition.up.railway.app',
    '*',
]

# Add Railway internal host if provided
if railway_static_url := os.getenv('RAILWAY_STATIC_URL'):
    ALLOWED_HOSTS.append(railway_static_url.replace('https://', '').replace('http://', '').split('/')[0])

# Database from Railway
if database_url := os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.parse(database_url, conn_max_age=600)
    }
    print("✅ PostgreSQL database configured")
else:
    raise ValueError("DATABASE_URL must be set in Railway environment variables")

# Disable Redis - use dummy cache (since REDIS_URL not set)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# Disable Celery - run tasks synchronously (since Redis not available)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"


# Email Configuration
# Use environment variables if set, otherwise console backend
if all([os.getenv('DEFAULT_FROM_EMAIL'), os.getenv('EMAIL_BACKEND')]):
    EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL')

    # If SMTP backend, configure additional settings
    if 'smtp' in EMAIL_BACKEND.lower():
        EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
        EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
        EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
        EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
        EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
else:
    # Fallback to console for debugging
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    DEFAULT_FROM_EMAIL = "Vervilure <noreply@railway.app>"

# Static files with WhiteNoise
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# CORS Settings
CORS_ALLOWED_ORIGINS = [
    "https://hospitable-intuition-production.up.railway.app",
    "https://hospitable-intuition.up.railway.app",
]

# Add frontend URL from env if set
if frontend_url := os.getenv('FRONTEND_URL'):
    CORS_ALLOWED_ORIGINS.append(frontend_url)

# CSRF trusted origins
CSRF_TRUSTED_ORIGINS = [
    "https://hospitable-intuition-deveop.up.railway.app",
    "https://hospitable-intuition-production.up.railway.app",
    "http://localhost:3000",
]

# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True

# Use Railway environment variables for OAuth if set
if google_client_id := os.getenv('GOOGLE_OAUTH_CLIENT_ID'):
    GOOGLE_OAUTH_CLIENT_ID = google_client_id
    GOOGLE_OAUTH_SECRET = os.getenv('GOOGLE_OAUTH_SECRET', '')

    # Update social account providers
    SOCIALACCOUNT_PROVIDERS['google']['APP'] = {
        'client_id': GOOGLE_OAUTH_CLIENT_ID,
        'secret': GOOGLE_OAUTH_SECRET,
        'key': '',
    }

# Override any CI/Testing settings
IS_CI = False
IS_TESTING = False
CELERY_TASK_ALWAYS_EAGER = True  # Force synchronous tasks without Redis

# Simplified logging for Railway
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

print("🚀 Railway settings loaded successfully")
print(f"🔐 Secret key: {'✅ Set' if SECRET_KEY else '❌ Missing'}")
print(f"📦 Database: {'✅ PostgreSQL' if 'DATABASE_URL' in os.environ else '❌ Missing'}")
print(f"💾 Cache: Dummy (Redis not configured)")
print(f"📧 Email: {EMAIL_BACKEND.split('.')[-1]}")
print(f"🌐 CORS: {len(CORS_ALLOWED_ORIGINS)} origins configured")

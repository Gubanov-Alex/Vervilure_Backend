"""
Railway-specific Django settings.
Создай этот файл как config/railway_settings.py
"""

from .settings import *
import dj_database_url

# Railway Production Settings
DEBUG = False
ALLOWED_HOSTS = [
    '.railway.app',
    '.up.railway.app',
    'hospitable-intuition-production.up.railway.app',
]

# Database from Railway
DATABASES = {
    'default': dj_database_url.parse(os.environ.get('DATABASE_URL'), conn_max_age=600)
}

# Disable Redis - use dummy cache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# Disable Celery - run tasks synchronously
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

# Email to console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "Vervilure <noreply@railway.app>"

# Static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# CORS
CSRF_TRUSTED_ORIGINS = [
    "https://hospitable-intuition-production.up.railway.app",
    "http://localhost:3000",
]

print("🚀 Railway settings loaded successfully")

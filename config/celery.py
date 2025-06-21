import os

from celery import Celery
from kombu import Queue

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("vervilure")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Additional configuration for better reliability
app.conf.update(
    # Acknowledge tasks after they have been executed
    task_acks_late=True,
    # Reject tasks on worker lost to requeue them
    task_reject_on_worker_lost=True,
    # Task time limits
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,  # 10 minutes hard limit
    # Worker configuration
    worker_prefetch_multiplier=1,  # Disable prefetching for better task distribution
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks to prevent memory leaks
    # Database connection pooling
    worker_pool_restarts=True,
)

# Define queues for better task organization
app.conf.task_routes = {
    "src.apps.accounts.tasks.send_verification_email": {"queue": "emails"},
    "src.apps.accounts.tasks.send_password_reset_email": {"queue": "emails"},
    "src.apps.accounts.tasks.cleanup_expired_tokens": {"queue": "maintenance"},
}

app.autodiscover_tasks()

# In your Django settings.py, add:
"""
# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# Task execution settings
CELERY_TASK_ALWAYS_EAGER = False  # Never set to True in production
CELERY_TASK_EAGER_PROPAGATES = True

# Broker connection retry settings
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10

# Result backend settings
CELERY_RESULT_EXPIRES = 3600  # Results expire after 1 hour
CELERY_RESULT_PERSISTENT = True

# Serialization
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

# Time zone
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Beat schedule (if using periodic tasks)
CELERY_BEAT_SCHEDULE = {
    'cleanup-expired-tokens': {
        'task': 'src.apps.accounts.tasks.cleanup_expired_tokens',
        'schedule': 3600,  # Run every hour
    },
}
"""

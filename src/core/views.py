"""
Core views for health checking and error handling.
"""

import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


@require_GET
@never_cache
@csrf_exempt
def health_check(request: HttpRequest) -> JsonResponse:
    """
    Health check endpoint for monitoring and load balancers.

    Checks:
    - Database connectivity
    - Redis connectivity (if configured)
    - Basic system status

    Returns:
        JsonResponse: Health status with details
    """
    start_time = time.time()
    health_status = {
        "status": "healthy",
        "timestamp": timezone.now().isoformat(),
        "version": getattr(settings, "VERSION", "1.0.0"),
        "checks": {},
    }

    # Database check
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        health_status["checks"]["database"] = {"status": "healthy", "message": "Database connection successful"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}",
        }
        health_status["status"] = "unhealthy"

    # Redis/Cache check
    try:
        cache_key = "health_check_test"
        cache.set(cache_key, "test_value", 10)
        cached_value = cache.get(cache_key)
        if cached_value == "test_value":
            health_status["checks"]["cache"] = {"status": "healthy", "message": "Cache connection successful"}
        else:
            health_status["checks"]["cache"] = {"status": "degraded", "message": "Cache write/read mismatch"}
    except Exception as e:
        logger.warning(f"Cache health check failed: {e}")
        health_status["checks"]["cache"] = {"status": "unhealthy", "message": f"Cache connection failed: {str(e)}"}
        # Don't mark overall status as unhealthy for cache issues

    # Performance metrics
    response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
    health_status["response_time_ms"] = round(response_time, 2)

    # Determine HTTP status code
    status_code = 200 if health_status["status"] == "healthy" else 503

    return JsonResponse(health_status, status=status_code)


@require_GET
@never_cache
def readiness_check(request: HttpRequest) -> JsonResponse:
    """
    Readiness check for Kubernetes/container orchestration.

    Returns:
        JsonResponse: Readiness status
    """
    # Basic readiness checks
    ready_checks = {
        "django": True,
        "database": True,
    }

    try:
        # Check database readiness
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        ready_checks["database"] = False

    is_ready = all(ready_checks.values())

    return JsonResponse(
        {"ready": is_ready, "checks": ready_checks, "timestamp": timezone.now().isoformat()},
        status=200 if is_ready else 503,
    )


@require_GET
@never_cache
def liveness_check(request: HttpRequest) -> JsonResponse:
    """
    Liveness check for Kubernetes/container orchestration.

    Returns:
        JsonResponse: Simple alive status
    """
    return JsonResponse({"alive": True, "timestamp": timezone.now().isoformat()})


# Error handlers
def api_400_handler(request: HttpRequest, exception: Exception = None) -> JsonResponse:
    """Handle 400 Bad Request errors."""
    return JsonResponse(
        {
            "error": "Bad Request",
            "code": 400,
            "message": "The request could not be understood.",
            "timestamp": timezone.now().isoformat(),
        },
        status=400,
    )


def api_401_handler(request: HttpRequest, exception: Exception = None) -> JsonResponse:
    """Handle 401 Unauthorized errors."""
    return JsonResponse(
        {
            "error": "Unauthorized",
            "code": 401,
            "message": "Authentication credentials required.",
            "timestamp": timezone.now().isoformat(),
        },
        status=401,
    )


def api_404_handler(request: HttpRequest, exception: Exception = None) -> JsonResponse:
    """Handle 404 Not Found errors."""
    return JsonResponse(
        {
            "error": "Not Found",
            "code": 404,
            "message": "The requested resource was not found.",
            "timestamp": timezone.now().isoformat(),
        },
        status=404,
    )


def api_500_handler(request: HttpRequest) -> JsonResponse:
    """Handle 500 Internal Server Error."""
    logger.error(f"Server error on {request.path}", exc_info=True)
    return JsonResponse(
        {
            "error": "Internal Server Error",
            "code": 500,
            "message": "An unexpected error occurred.",
            "timestamp": timezone.now().isoformat(),
        },
        status=500,
    )

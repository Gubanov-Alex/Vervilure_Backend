import logging

from django.http import JsonResponse
from django.utils import timezone

logger = logging.getLogger(__name__)


def api_400_handler(request, exception=None):
    """Custom 400 error handler for API."""
    return JsonResponse(
        {
            "error": "Bad Request",
            "code": 400,
            "message": "The request could not be understood.",
            "timestamp": timezone.now().isoformat(),
        },
        status=400,
    )


def api_401_handler(request, exception=None):
    """Custom 401 error handler for API."""
    return JsonResponse(
        {
            "error": "Unauthorized",
            "code": 401,
            "message": "Authentication credentials required.",
            "timestamp": timezone.now().isoformat(),
        },
        status=401,
    )


def api_404_handler(request, exception=None):
    """Custom 404 error handler for API."""
    return JsonResponse(
        {
            "error": "Not Found",
            "code": 404,
            "message": "The requested resource was not found.",
            "timestamp": timezone.now().isoformat(),
        },
        status=404,
    )


def api_500_handler(request):
    """Custom 500 error handler for API."""
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

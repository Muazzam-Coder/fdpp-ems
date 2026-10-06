from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Custom DRF exception handler that produces friendlier 404 responses
    and ensures CORS headers / JSON format are preserved on 500 errors.
    """
    response = drf_exception_handler(exc, context)

    if response is not None:
        if response.status_code == status.HTTP_404_NOT_FOUND:
            detail = getattr(exc, 'detail', None) or response.data.get('detail', 'Not found.')
            user_msg = str(detail)
            if user_msg in ("Not found.", '', 'None'):
                user_msg = (
                    "Resource not found. Verify the endpoint path and ensure any required "
                    "parameters (path or query parameters) are provided."
                )
            response.data = {"error": user_msg}
        return response

    logger.exception("Unhandled exception in API request: %s", exc)
    return Response(
        {"error": f"Server Error: {str(exc)}"},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )

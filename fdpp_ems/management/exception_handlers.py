from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """Custom DRF exception handler that produces friendlier 404 responses.

    - Wraps DRF's default handler.
    - When a 404/NotFound is returned, replace the default message with
      a clearer hint about checking the endpoint and required parameters.
    """
    response = drf_exception_handler(exc, context)

    # If DRF couldn't handle the exception and it's an API request, return a JSON 404
    request = context.get('request') if context else None
    if response is None:
        if request and request.path.startswith('/api/'):
            return Response(
                {
                    "error": "Resource not found",
                    "detail": "The requested endpoint or resource was not found. Verify the URL and required parameters."
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return response

    # If DRF returned a 404, make the message more helpful
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

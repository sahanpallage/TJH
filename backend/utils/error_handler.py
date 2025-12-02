"""
Error handling utilities to sanitize error messages and prevent information leakage.
"""
import logging
import traceback
from typing import Any, Dict
from fastapi import HTTPException

from settings import settings

logger = logging.getLogger(__name__)

# Sensitive patterns that should be redacted from error messages
SENSITIVE_PATTERNS = [
    "api_key",
    "apikey",
    "api-key",
    "token",
    "password",
    "secret",
    "apify_api",
    "rapid_api",
    "supabase_key",
]


def sanitize_error_message(error_msg: str) -> str:
    """
    Remove sensitive information from error messages.
    
    Args:
        error_msg: Original error message
        
    Returns:
        Sanitized error message safe to return to clients
    """
    if not error_msg:
        return "An error occurred"
    
    # In production, be more restrictive
    if settings.ENVIRONMENT == "production":
        # Don't expose internal error details
        if any(pattern in error_msg.lower() for pattern in SENSITIVE_PATTERNS):
            return "An error occurred while processing your request. Please try again later."
        
        # Don't expose stack traces or file paths
        if "Traceback" in error_msg or "File" in error_msg or ".py" in error_msg:
            return "An internal error occurred. Please contact support if the issue persists."
    
    # In development, show more details but still sanitize sensitive info
    sanitized = error_msg
    for pattern in SENSITIVE_PATTERNS:
        # Simple redaction (could be improved with regex)
        if pattern.lower() in sanitized.lower():
            sanitized = sanitized.replace(pattern, "[REDACTED]")
    
    return sanitized


def handle_exception(e: Exception, endpoint: str = "unknown") -> HTTPException:
    """
    Handle exceptions and return appropriate HTTPException.
    
    Args:
        e: The exception that occurred
        endpoint: Name of the endpoint where error occurred
        
    Returns:
        HTTPException with sanitized error message
    """
    # Log full error details (for internal debugging)
    logger.exception(f"Error in {endpoint}: {str(e)}")
    
    # Determine status code
    if isinstance(e, HTTPException):
        # Preserve status code but sanitize detail
        detail = sanitize_error_message(str(e.detail)) if e.detail else "An error occurred"
        return HTTPException(status_code=e.status_code, detail=detail)
    
    # Default to 500 for unexpected errors
    detail = sanitize_error_message(str(e))
    
    return HTTPException(
        status_code=500,
        detail=detail
    )


def log_error_with_context(
    error: Exception,
    endpoint: str,
    request_data: Dict[str, Any] = None,
    user_info: str = None
):
    """
    Log error with full context for debugging (not sent to client).
    
    Args:
        error: The exception
        endpoint: Endpoint name
        request_data: Request data (sanitized)
        user_info: User/request identifier
    """
    context = {
        "endpoint": endpoint,
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    
    if request_data:
        # Sanitize request data
        sanitized_data = {}
        for key, value in request_data.items():
            if any(pattern in key.lower() for pattern in SENSITIVE_PATTERNS):
                sanitized_data[key] = "[REDACTED]"
            else:
                sanitized_data[key] = value
        context["request_data"] = sanitized_data
    
    if user_info:
        context["user"] = user_info
    
    logger.error(f"Error in {endpoint}", extra=context, exc_info=True)


"""
Authentication middleware for API key-based authentication.
"""
import logging
from fastapi import Request, status
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from settings import settings

logger = logging.getLogger(__name__)

# API key header (kept for future use if needed)
api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to authenticate requests using API key.
    Skips authentication for health checks and root endpoint.
    """

    # Endpoints that don't require authentication
    # Use exact path matching to avoid accidentally skipping auth on all routes.
    PUBLIC_ENDPOINTS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        # Skip authentication for public endpoints (exact path match)
        if request.url.path in self.PUBLIC_ENDPOINTS:
            return await call_next(request)

        # Skip if API key is not configured (development mode)
        if not settings.API_KEY:
            logger.warning("API_KEY not configured - allowing all requests (development mode)")
            return await call_next(request)

        # Get API key from header
        api_key = request.headers.get(settings.API_KEY_HEADER)

        if not api_key:
            logger.warning(f"Missing API key in request to {request.url.path}")
            # Return 401 directly instead of raising HTTPException from middleware
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing API key. Please provide X-API-Key header."},
            )

        if api_key != settings.API_KEY:
            logger.warning(f"Invalid API key attempt for {request.url.path}")
            # Return 403 directly instead of raising HTTPException from middleware
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Invalid API key."},
            )

        # Add user info to request state (for future use)
        request.state.authenticated = True

        return await call_next(request)


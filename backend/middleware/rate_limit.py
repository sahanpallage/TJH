"""
Rate limiting middleware to prevent API abuse.
"""
import time
import logging
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from settings import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    For production with multiple instances, consider using Redis.
    """
    
    # Store request counts: {ip: [(timestamp, count), ...]}
    _request_counts: Dict[str, list] = defaultdict(list)
    
    # Endpoints that don't require rate limiting
    EXEMPT_ENDPOINTS = ["/", "/health", "/docs", "/openapi.json", "/redoc"]
    
    def __init__(self, app):
        super().__init__(app)
        self.enabled = settings.RATE_LIMIT_ENABLED
        self.per_minute = settings.RATE_LIMIT_PER_MINUTE
        self.per_hour = settings.RATE_LIMIT_PER_HOUR
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check for forwarded IP (when behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _cleanup_old_entries(self, ip: str, current_time: float):
        """Remove entries older than 1 hour."""
        cutoff = current_time - 3600
        self._request_counts[ip] = [
            (ts, count) for ts, count in self._request_counts[ip]
            if ts > cutoff
        ]
    
    def _check_rate_limit(self, ip: str) -> Tuple[bool, str]:
        """Check if IP has exceeded rate limits."""
        if not self.enabled:
            return True, ""
        
        current_time = time.time()
        
        # Cleanup old entries
        self._cleanup_old_entries(ip, current_time)
        
        # Count requests in last minute and hour
        minute_ago = current_time - 60
        hour_ago = current_time - 3600
        
        minute_count = sum(
            count for ts, count in self._request_counts[ip]
            if ts > minute_ago
        )
        hour_count = sum(
            count for ts, count in self._request_counts[ip]
            if ts > hour_ago
        )
        
        # Check limits
        if minute_count >= self.per_minute:
            return False, f"Rate limit exceeded: {minute_count}/{self.per_minute} requests per minute"
        
        if hour_count >= self.per_hour:
            return False, f"Rate limit exceeded: {hour_count}/{self.per_hour} requests per hour"
        
        # Record this request
        self._request_counts[ip].append((current_time, 1))
        
        return True, ""
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for exempt endpoints
        if any(request.url.path.startswith(endpoint) for endpoint in self.EXEMPT_ENDPOINTS):
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check rate limit
        allowed, error_msg = self._check_rate_limit(client_ip)
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for IP {client_ip} on {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_msg,
                headers={"Retry-After": "60"}
            )
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit-Minute"] = str(self.per_minute)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.per_hour)
        
        return response


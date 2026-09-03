"""Monitoring middleware for automatic request metrics collection."""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.services.monitoring_service import MonitoringService


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP request metrics for Prometheus."""

    async def dispatch(self, request: Request, call_next):
        """Record request start time, process request, and record metrics."""
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time
        method = request.method
        endpoint = request.url.path
        status_code = response.status_code

        MonitoringService.record_request(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            duration=duration,
        )

        return response

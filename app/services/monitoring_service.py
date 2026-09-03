"""Monitoring service with Prometheus metrics for system observability."""

import time
from functools import wraps

from prometheus_client import Counter, Gauge, Histogram, Info

# Application info
APP_INFO = Info("qvs_app", "Qualification Verification System application info")
APP_INFO.info({"version": "1.0.0", "name": "qualification-verification-system"})

# Request metrics
REQUEST_COUNT = Counter(
    "qvs_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "qvs_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Business metrics
QUALIFICATIONS_TOTAL = Gauge(
    "qvs_qualifications_total",
    "Total number of qualifications in the system",
)

VERIFICATIONS_TOTAL = Counter(
    "qvs_verifications_total",
    "Total verification attempts",
    ["result", "method"],
)

VERIFICATION_DURATION = Histogram(
    "qvs_verification_duration_seconds",
    "Time spent on verification in seconds",
    ["method"],
)

AI_ANALYSES_TOTAL = Counter(
    "qvs_ai_analyses_total",
    "Total AI credential analyses",
    ["result"],
)

ACTIVE_USERS = Gauge(
    "qvs_active_users_total",
    "Total active users in the system",
)

AUDIT_LOGS_TOTAL = Gauge(
    "qvs_audit_logs_total",
    "Total audit log entries",
)


class MonitoringService:
    """Service for recording and tracking system metrics."""

    @staticmethod
    def record_request(method: str, endpoint: str, status_code: int, duration: float):
        """Record an HTTP request metric."""
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status=str(status_code),
        ).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)

    @staticmethod
    def record_verification(result: str, method: str, duration: float):
        """Record a verification attempt metric."""
        VERIFICATIONS_TOTAL.labels(result=result, method=method).inc()
        VERIFICATION_DURATION.labels(method=method).observe(duration)

    @staticmethod
    def record_ai_analysis(result: str):
        """Record an AI analysis metric."""
        AI_ANALYSES_TOTAL.labels(result=result).inc()

    @staticmethod
    def update_qualifications_count(count: int):
        """Update the total qualifications gauge."""
        QUALIFICATIONS_TOTAL.set(count)

    @staticmethod
    def update_active_users(count: int):
        """Update the active users gauge."""
        ACTIVE_USERS.set(count)

    @staticmethod
    def update_audit_logs_count(count: int):
        """Update the audit logs gauge."""
        AUDIT_LOGS_TOTAL.set(count)

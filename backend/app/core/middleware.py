"""
AutoValue API Middleware.
Provides request correlation tracing (X-Request-ID), structured access logging,
in-memory rate limiting, and request body size enforcement.
"""
import time
import uuid
import logging
from collections import defaultdict
from typing import Callable, Dict, List, Tuple
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .config import settings

logger = logging.getLogger("autovalue.access")


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """
    Extracts or generates a unique correlation ID (X-Request-ID) for every incoming HTTP request,
    attaches it to request state and response headers, and records structured request telemetry.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID")
        if not request_id or len(request_id) > 64:
            request_id = f"val-{uuid.uuid4().hex[:12]}"

        request.state.request_id = request_id
        start_time = time.perf_counter()

        response: Response
        try:
            response = await call_next(request)
        except Exception as e:
            latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            logger.error(
                f"Unhandled server error: {e}",
                extra={
                    "request_id": request_id,
                    "route": request.url.path,
                    "method": request.method,
                    "status_code": 500,
                    "latency_ms": latency_ms
                }
            )
            raise e

        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        response.headers["X-Request-ID"] = request_id

        # Log structured request access
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} ({latency_ms} ms)",
            extra={
                "request_id": request_id,
                "route": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "latency_ms": latency_ms
            }
        )

        return response


class InMemoryRateLimiter:
    """
    Sliding window in-memory rate limiter per client IP.
    Suitable for single-instance deployments; documents replacement with Redis in cluster mode.
    """

    def __init__(self, requests_per_minute: int = 60):
        self.limit = requests_per_minute
        self.window_seconds = 60.0
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> Tuple[bool, int]:
        now = time.time()
        timestamps = self.requests[client_ip]
        current_limit = getattr(settings, "RATE_LIMIT_PER_MINUTE", self.limit)

        # Prune timestamps outside current 60s window
        cutoff = now - self.window_seconds
        while timestamps and timestamps[0] < cutoff:
            timestamps.pop(0)

        if len(timestamps) >= current_limit:
            retry_after = int(self.window_seconds - (now - timestamps[0])) + 1
            return False, max(1, retry_after)

        timestamps.append(now)
        return True, 0

    def reset(self):
        self.requests.clear()


rate_limiter = InMemoryRateLimiter(requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)


class ValuationRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Applies rate limiting on valuation calculation endpoints to prevent abuse.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path.endswith("/valuation") and request.method == "POST":
            client_ip = request.client.host if request.client else "127.0.0.1"
            # Respect X-Forwarded-For if behind a reverse proxy
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()

            allowed, retry_after = rate_limiter.is_allowed(client_ip)
            if not allowed:
                request_id = getattr(request.state, "request_id", "unknown")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={
                        "Retry-After": str(retry_after),
                        "X-Request-ID": request_id
                    },
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": f"Rate limit exceeded. Maximum {settings.RATE_LIMIT_PER_MINUTE} requests per minute.",
                            "retry_after_seconds": retry_after,
                            "request_id": request_id
                        }
                    }
                )

        return await call_next(request)


class RequestBodyLimitMiddleware(BaseHTTPMiddleware):
    """
    Enforces maximum request payload size to prevent denial-of-service via large payloads.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("Content-Length")
        if content_length:
            try:
                length = int(content_length)
                if length > settings.MAX_REQUEST_BODY_BYTES:
                    request_id = getattr(request.state, "request_id", "unknown")
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        headers={"X-Request-ID": request_id},
                        content={
                            "error": {
                                "code": "REQUEST_TOO_LARGE",
                                "message": f"Request body exceeds maximum allowed size of {settings.MAX_REQUEST_BODY_BYTES} bytes.",
                                "request_id": request_id
                            }
                        }
                    )
            except ValueError:
                pass

        return await call_next(request)

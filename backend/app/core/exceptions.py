"""
AutoValue Centralized Exceptions and Global FastAPI Error Handlers.
Formats all application errors into consistent, structured envelopes with request correlation IDs.
"""
from datetime import datetime, timezone
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError, HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

logger = logging.getLogger("autovalue.exceptions")


class AutoValueException(Exception):
    """Base application exception."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class ModelNotFoundError(AutoValueException):
    def __init__(self, version: str, message: Optional[str] = None):
        super().__init__(
            message=message or f"Configured model version '{version}' or its required artifacts could not be found.",
            code="MODEL_NOT_FOUND",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


class ModelIntegrityError(AutoValueException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="MODEL_INTEGRITY_FAILURE",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class ModelInferenceError(AutoValueException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="INFERENCE_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class DatabaseConnectionError(AutoValueException):
    def __init__(self, message: str = "Database service is temporarily unavailable."):
        super().__init__(
            message=message,
            code="DATABASE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


def create_error_response(
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    details: Optional[Any] = None
) -> JSONResponse:
    """Builds a standard JSON error response envelope."""
    payload = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }
    if details is not None:
        payload["error"]["details"] = details

    return JSONResponse(
        status_code=status_code,
        headers={"X-Request-ID": request_id},
        content=payload
    )


def register_exception_handlers(app: FastAPI):
    """Registers centralized global exception handlers on the FastAPI application."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", "unknown")
        errors = []
        for err in exc.errors():
            loc = " -> ".join(str(l) for l in err.get("loc", []))
            msg = err.get("msg", "Validation error")
            errors.append({"field": loc, "message": msg, "type": err.get("type")})

        logger.warning(
            f"Validation failure on {request.method} {request.url.path}: {errors}",
            extra={"request_id": request_id}
        )

        return create_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message="Invalid request input payload.",
            request_id=request_id,
            details=errors
        )

    @app.exception_handler(StarletteHTTPException)
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        status_code = getattr(exc, "status_code", 500)
        detail = getattr(exc, "detail", "HTTP Error")
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            413: "REQUEST_TOO_LARGE",
            422: "VALIDATION_ERROR",
            429: "RATE_LIMIT_EXCEEDED",
            500: "INTERNAL_SERVER_ERROR",
            503: "SERVICE_UNAVAILABLE"
        }
        code = code_map.get(status_code, "HTTP_ERROR")
        return create_error_response(
            status_code=status_code,
            code=code,
            message=str(detail),
            request_id=request_id
        )

    @app.exception_handler(AutoValueException)
    async def autovalue_exception_handler(request: Request, exc: AutoValueException):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(
            f"Application error ({exc.code}): {exc.message}",
            extra={"request_id": request_id}
        )
        return create_error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            request_id=request_id,
            details=exc.details
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception(
            f"Unhandled internal server error: {exc}",
            extra={"request_id": request_id}
        )
        # Never leak raw Python tracebacks to external clients in production
        return create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred. Please contact system administrator with the request ID.",
            request_id=request_id
        )

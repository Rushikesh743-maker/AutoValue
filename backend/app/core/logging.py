"""
AutoValue Structured Application Logging Configuration.
Provides JSON and formatted text logging with correlation IDs and safe telemetry.
"""
import logging
import json
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from .config import settings


class StructuredJSONFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON objects suitable for log aggregation systems
    (Elasticsearch, Datadog, CloudWatch, Loki).
    """

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include request context if present
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if hasattr(record, "route"):
            log_obj["route"] = record.route
        if hasattr(record, "method"):
            log_obj["method"] = record.method
        if hasattr(record, "status_code"):
            log_obj["status_code"] = record.status_code
        if hasattr(record, "latency_ms"):
            log_obj["latency_ms"] = record.latency_ms

        # Include exception details if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


def setup_logging():
    """Configures application-wide root logging."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicate output
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    if settings.LOG_FORMAT.lower() == "json":
        formatter = StructuredJSONFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s (req=%(request_id)s): %(message)s",
            defaults={"request_id": "none"}
        )
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    # Suppress overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(log_level)

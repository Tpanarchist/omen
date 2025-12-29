"""
Logging — Structured logging with correlation ID propagation.

Provides consistent logging across all OMEN components with
correlation ID tracking for request tracing.
"""

import logging
import json
import sys
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


# Context variable for correlation ID
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def set_correlation_id(cid: UUID | str | None) -> None:
    """Set correlation ID for current context."""
    _correlation_id.set(str(cid) if cid else None)


def get_correlation_id() -> str | None:
    """Get correlation ID from current context."""
    return _correlation_id.get()


class CorrelationFilter(logging.Filter):
    """Adds correlation_id to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "-"
        return True


class JSONFormatter(logging.Formatter):
    """
    Formats log records as JSON for structured logging.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None),
        }
        
        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class ReadableFormatter(logging.Formatter):
    """
    Human-readable formatter for development.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        cid = getattr(record, "correlation_id", "-")
        cid_short = cid[:8] if cid and cid != "-" else "-"
        
        base = f"{record.levelname:<7} [{cid_short}] {record.name}: {record.getMessage()}"
        
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        
        return base


def configure_logging(
    level: int = logging.INFO,
    json_format: bool = False,
    stream: Any = None,
) -> None:
    """
    Configure OMEN logging.
    
    Args:
        level: Logging level
        json_format: Use JSON format (for production)
        stream: Output stream (default: stderr)
    """
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.addFilter(CorrelationFilter())
    
    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(ReadableFormatter())
    
    # Configure OMEN loggers
    omen_logger = logging.getLogger("omen")
    omen_logger.setLevel(level)
    omen_logger.handlers.clear()
    omen_logger.addHandler(handler)
    omen_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get a logger for OMEN component."""
    return logging.getLogger(f"omen.{name}")


class LogContext:
    """
    Context manager for logging with correlation ID.
    
    Usage:
        with LogContext(correlation_id):
            logger.info("Processing...")  # Includes correlation_id
    """
    
    def __init__(self, correlation_id: UUID | str | None):
        self.correlation_id = correlation_id
        self._token = None
    
    def __enter__(self):
        self._token = _correlation_id.set(
            str(self.correlation_id) if self.correlation_id else None
        )
        return self
    
    def __exit__(self, *args):
        if self._token is not None:
            _correlation_id.reset(self._token)

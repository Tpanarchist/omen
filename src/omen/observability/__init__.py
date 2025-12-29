"""
Observability — Logging, metrics, and debugging for OMEN.

Provides:
- Structured logging with correlation ID
- Metrics collection (counters, gauges, histograms)
- Debug mode for development
"""

from omen.observability.logging import (
    set_correlation_id,
    get_correlation_id,
    configure_logging,
    get_logger,
    LogContext,
    JSONFormatter,
    ReadableFormatter,
)
from omen.observability.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsRegistry,
    get_metrics,
    reset_metrics,
)
from omen.observability.debug import (
    DebugCapture,
    DebugRecorder,
    enable_debug,
    disable_debug,
    get_debug_recorder,
    is_debug_enabled,
)

__all__ = [
    # Logging
    "set_correlation_id",
    "get_correlation_id",
    "configure_logging",
    "get_logger",
    "LogContext",
    "JSONFormatter",
    "ReadableFormatter",
    # Metrics
    "Counter",
    "Gauge",
    "Histogram",
    "MetricsRegistry",
    "get_metrics",
    "reset_metrics",
    # Debug
    "DebugCapture",
    "DebugRecorder",
    "enable_debug",
    "disable_debug",
    "get_debug_recorder",
    "is_debug_enabled",
]

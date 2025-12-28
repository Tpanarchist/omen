"""
Integrity Overlay — System safety and constraint enforcement.

Provides:
- IntegrityMonitor: Watches buses, enforces constraints
- SafeMode: System safety states
- Budget enforcement and token revocation
- Constitutional veto processing

Spec: OMEN.md §12
"""

from omen.integrity.monitor import (
    SafeMode,
    AlertSeverity,
    AlertType,
    IntegrityEvent,
    MonitorConfig,
    IntegrityMonitor,
    create_monitor,
)

__all__ = [
    "SafeMode",
    "AlertSeverity",
    "AlertType",
    "IntegrityEvent",
    "MonitorConfig",
    "IntegrityMonitor",
    "create_monitor",
]

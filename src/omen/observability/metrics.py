"""
Metrics — Simple metrics collection for OMEN.

Tracks key performance and reliability metrics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any


@dataclass
class MetricValue:
    """Single metric value with timestamp."""
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    labels: dict[str, str] = field(default_factory=dict)


class Counter:
    """Monotonically increasing counter."""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._value = 0.0
        self._lock = Lock()
    
    def inc(self, amount: float = 1.0) -> None:
        """Increment counter."""
        with self._lock:
            self._value += amount
    
    @property
    def value(self) -> float:
        return self._value
    
    def reset(self) -> None:
        """Reset counter (for testing)."""
        with self._lock:
            self._value = 0.0


class Gauge:
    """Value that can go up and down."""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._value = 0.0
        self._lock = Lock()
    
    def set(self, value: float) -> None:
        """Set gauge value."""
        with self._lock:
            self._value = value
    
    def inc(self, amount: float = 1.0) -> None:
        """Increment gauge."""
        with self._lock:
            self._value += amount
    
    def dec(self, amount: float = 1.0) -> None:
        """Decrement gauge."""
        with self._lock:
            self._value -= amount
    
    @property
    def value(self) -> float:
        return self._value
    
    def reset(self) -> None:
        with self._lock:
            self._value = 0.0


class Histogram:
    """
    Simple histogram for tracking distributions.
    
    Tracks count, sum, min, max for calculating stats.
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._count = 0
        self._sum = 0.0
        self._min = float("inf")
        self._max = float("-inf")
        self._lock = Lock()
    
    def observe(self, value: float) -> None:
        """Record an observation."""
        with self._lock:
            self._count += 1
            self._sum += value
            self._min = min(self._min, value)
            self._max = max(self._max, value)
    
    @property
    def count(self) -> int:
        return self._count
    
    @property
    def sum(self) -> float:
        return self._sum
    
    @property
    def avg(self) -> float:
        if self._count == 0:
            return 0.0
        return self._sum / self._count
    
    @property
    def min(self) -> float:
        return self._min if self._count > 0 else 0.0
    
    @property
    def max(self) -> float:
        return self._max if self._count > 0 else 0.0
    
    def reset(self) -> None:
        with self._lock:
            self._count = 0
            self._sum = 0.0
            self._min = float("inf")
            self._max = float("-inf")
    
    def to_dict(self) -> dict[str, float]:
        return {
            "count": self._count,
            "sum": self._sum,
            "avg": self.avg,
            "min": self.min,
            "max": self.max,
        }


@dataclass
class MetricsRegistry:
    """
    Registry for all OMEN metrics.
    """
    # Episode metrics
    episodes_total: Counter = field(
        default_factory=lambda: Counter("episodes_total", "Total episodes executed")
    )
    episodes_success: Counter = field(
        default_factory=lambda: Counter("episodes_success", "Successful episodes")
    )
    episodes_failed: Counter = field(
        default_factory=lambda: Counter("episodes_failed", "Failed episodes")
    )
    
    # Duration metrics
    episode_duration_seconds: Histogram = field(
        default_factory=lambda: Histogram("episode_duration_seconds", "Episode duration")
    )
    step_duration_seconds: Histogram = field(
        default_factory=lambda: Histogram("step_duration_seconds", "Step duration")
    )
    llm_latency_seconds: Histogram = field(
        default_factory=lambda: Histogram("llm_latency_seconds", "LLM call latency")
    )
    
    # Resource metrics
    tokens_consumed: Counter = field(
        default_factory=lambda: Counter("tokens_consumed", "Total tokens consumed")
    )
    tool_calls_total: Counter = field(
        default_factory=lambda: Counter("tool_calls_total", "Total tool calls")
    )
    
    # Integrity metrics
    contract_violations: Counter = field(
        default_factory=lambda: Counter("contract_violations", "Contract violations")
    )
    budget_exceeded: Counter = field(
        default_factory=lambda: Counter("budget_exceeded", "Budget exceeded events")
    )
    safe_mode_transitions: Counter = field(
        default_factory=lambda: Counter("safe_mode_transitions", "Safe mode transitions")
    )
    
    # Active state
    active_episodes: Gauge = field(
        default_factory=lambda: Gauge("active_episodes", "Currently active episodes")
    )
    
    def to_dict(self) -> dict[str, Any]:
        """Export all metrics as dict."""
        return {
            "episodes": {
                "total": self.episodes_total.value,
                "success": self.episodes_success.value,
                "failed": self.episodes_failed.value,
                "active": self.active_episodes.value,
            },
            "duration": {
                "episode": self.episode_duration_seconds.to_dict(),
                "step": self.step_duration_seconds.to_dict(),
                "llm": self.llm_latency_seconds.to_dict(),
            },
            "resources": {
                "tokens_consumed": self.tokens_consumed.value,
                "tool_calls": self.tool_calls_total.value,
            },
            "integrity": {
                "contract_violations": self.contract_violations.value,
                "budget_exceeded": self.budget_exceeded.value,
                "safe_mode_transitions": self.safe_mode_transitions.value,
            },
        }
    
    def reset(self) -> None:
        """Reset all metrics (for testing)."""
        self.episodes_total.reset()
        self.episodes_success.reset()
        self.episodes_failed.reset()
        self.episode_duration_seconds.reset()
        self.step_duration_seconds.reset()
        self.llm_latency_seconds.reset()
        self.tokens_consumed.reset()
        self.tool_calls_total.reset()
        self.contract_violations.reset()
        self.budget_exceeded.reset()
        self.safe_mode_transitions.reset()
        self.active_episodes.reset()


# Global metrics registry
_metrics = MetricsRegistry()


def get_metrics() -> MetricsRegistry:
    """Get global metrics registry."""
    return _metrics


def reset_metrics() -> None:
    """Reset all metrics (for testing)."""
    _metrics.reset()

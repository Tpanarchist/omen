"""Tests for metrics collection."""

import pytest

from omen.observability import (
    Counter,
    Gauge,
    Histogram,
    get_metrics,
    reset_metrics,
)


class TestCounter:
    """Tests for Counter metric."""
    
    def test_starts_at_zero(self):
        """Counter starts at zero."""
        counter = Counter("test", "Test counter")
        assert counter.value == 0
    
    def test_increment(self):
        """Can increment counter."""
        counter = Counter("test", "Test counter")
        counter.inc()
        assert counter.value == 1
    
    def test_increment_by_amount(self):
        """Can increment by specific amount."""
        counter = Counter("test", "Test counter")
        counter.inc(5)
        assert counter.value == 5
    
    def test_reset(self):
        """Can reset counter."""
        counter = Counter("test", "Test counter")
        counter.inc(10)
        counter.reset()
        assert counter.value == 0


class TestGauge:
    """Tests for Gauge metric."""
    
    def test_set_value(self):
        """Can set gauge value."""
        gauge = Gauge("test", "Test gauge")
        gauge.set(42)
        assert gauge.value == 42
    
    def test_increment(self):
        """Can increment gauge."""
        gauge = Gauge("test", "Test gauge")
        gauge.set(10)
        gauge.inc(5)
        assert gauge.value == 15
    
    def test_decrement(self):
        """Can decrement gauge."""
        gauge = Gauge("test", "Test gauge")
        gauge.set(10)
        gauge.dec(3)
        assert gauge.value == 7


class TestHistogram:
    """Tests for Histogram metric."""
    
    def test_observe_values(self):
        """Can observe values."""
        hist = Histogram("test", "Test histogram")
        hist.observe(1.0)
        hist.observe(2.0)
        hist.observe(3.0)
        
        assert hist.count == 3
        assert hist.sum == 6.0
        assert hist.avg == 2.0
    
    def test_min_max(self):
        """Tracks min and max."""
        hist = Histogram("test", "Test histogram")
        hist.observe(5.0)
        hist.observe(1.0)
        hist.observe(10.0)
        
        assert hist.min == 1.0
        assert hist.max == 10.0
    
    def test_to_dict(self):
        """Exports to dict."""
        hist = Histogram("test", "Test histogram")
        hist.observe(2.0)
        
        d = hist.to_dict()
        assert d["count"] == 1
        assert d["sum"] == 2.0


class TestMetricsRegistry:
    """Tests for global metrics registry."""
    
    def setup_method(self):
        """Reset metrics before each test."""
        reset_metrics()
    
    def test_get_metrics(self):
        """Can get global metrics."""
        metrics = get_metrics()
        assert metrics is not None
    
    def test_track_episodes(self):
        """Can track episode metrics."""
        metrics = get_metrics()
        metrics.episodes_total.inc()
        metrics.episodes_success.inc()
        
        assert metrics.episodes_total.value == 1
        assert metrics.episodes_success.value == 1
    
    def test_track_durations(self):
        """Can track duration metrics."""
        metrics = get_metrics()
        metrics.episode_duration_seconds.observe(5.5)
        metrics.step_duration_seconds.observe(0.5)
        
        assert metrics.episode_duration_seconds.count == 1
        assert metrics.step_duration_seconds.avg == 0.5
    
    def test_to_dict(self):
        """Exports all metrics to dict."""
        metrics = get_metrics()
        metrics.episodes_total.inc()
        metrics.tokens_consumed.inc(100)
        
        d = metrics.to_dict()
        assert d["episodes"]["total"] == 1
        assert d["resources"]["tokens_consumed"] == 100

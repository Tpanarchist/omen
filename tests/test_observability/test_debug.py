"""Tests for debug mode."""

import pytest
from uuid import uuid4
from pathlib import Path

from omen.observability import (
    DebugCapture,
    DebugRecorder,
    enable_debug,
    disable_debug,
    get_debug_recorder,
    is_debug_enabled,
)


class TestDebugCapture:
    """Tests for debug capture."""
    
    def test_to_dict(self):
        """Converts to dict."""
        capture = DebugCapture(
            correlation_id="test-123",
            layer="5",
            raw_response="Test response",
        )
        
        d = capture.to_dict()
        assert d["correlation_id"] == "test-123"
        assert d["layer"] == "5"
    
    def test_to_json(self):
        """Converts to JSON."""
        capture = DebugCapture(
            correlation_id="test-123",
            layer="5",
            raw_response="Test response",
        )
        
        json_str = capture.to_json()
        assert "test-123" in json_str
        assert "Test response" in json_str


class TestDebugRecorder:
    """Tests for debug recorder."""
    
    def test_disabled_by_default(self):
        """Recorder is disabled by default."""
        recorder = DebugRecorder()
        assert recorder.enabled is False
    
    def test_capture_when_enabled(self):
        """Captures when enabled."""
        recorder = DebugRecorder(enabled=True, log_to_console=False)
        
        capture = recorder.capture(
            correlation_id=uuid4(),
            layer="5",
            raw_response="Test",
        )
        
        assert capture is not None
        assert len(recorder.get_captures()) == 1
    
    def test_no_capture_when_disabled(self):
        """No capture when disabled."""
        recorder = DebugRecorder(enabled=False)
        
        capture = recorder.capture(
            correlation_id=uuid4(),
            layer="5",
        )
        
        assert capture is None
    
    def test_query_by_layer(self):
        """Can query captures by layer."""
        recorder = DebugRecorder(enabled=True, log_to_console=False)
        
        recorder.capture(uuid4(), layer="5")
        recorder.capture(uuid4(), layer="6")
        recorder.capture(uuid4(), layer="5")
        
        layer5 = recorder.get_captures(layer="5")
        assert len(layer5) == 2
    
    def test_save_to_file(self, tmp_path):
        """Saves captures to file."""
        recorder = DebugRecorder(
            enabled=True,
            output_dir=tmp_path,
            log_to_console=False,
        )
        
        recorder.capture(
            correlation_id=uuid4(),
            layer="5",
            raw_response="Test response",
        )
        
        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1


class TestGlobalDebug:
    """Tests for global debug functions."""
    
    def setup_method(self):
        """Disable debug before each test."""
        disable_debug()
    
    def test_enable_disable(self):
        """Can enable and disable debug."""
        assert is_debug_enabled() is False
        
        enable_debug()
        assert is_debug_enabled() is True
        
        disable_debug()
        assert is_debug_enabled() is False
    
    def test_get_recorder(self):
        """Can get global recorder."""
        recorder = get_debug_recorder()
        assert isinstance(recorder, DebugRecorder)

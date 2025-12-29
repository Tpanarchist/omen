"""Tests for logging infrastructure."""

import pytest
import logging
import json
from io import StringIO
from uuid import uuid4

from omen.observability import (
    set_correlation_id,
    get_correlation_id,
    configure_logging,
    get_logger,
    LogContext,
)


class TestCorrelationId:
    """Tests for correlation ID management."""
    
    def setup_method(self):
        """Reset correlation ID before each test."""
        set_correlation_id(None)
    
    def test_set_and_get(self):
        """Can set and get correlation ID."""
        cid = str(uuid4())
        set_correlation_id(cid)
        assert get_correlation_id() == cid
    
    def test_none_when_not_set(self):
        """Returns None when not set."""
        set_correlation_id(None)
        assert get_correlation_id() is None
    
    def test_uuid_converted_to_string(self):
        """UUID is converted to string."""
        cid = uuid4()
        set_correlation_id(cid)
        assert get_correlation_id() == str(cid)


class TestLogContext:
    """Tests for log context manager."""
    
    def setup_method(self):
        """Reset correlation ID before each test."""
        set_correlation_id(None)
    
    def test_context_sets_correlation_id(self):
        """Context manager sets correlation ID."""
        cid = str(uuid4())
        
        with LogContext(cid):
            assert get_correlation_id() == cid
    
    def test_context_restores_previous(self):
        """Context manager restores previous ID."""
        old_cid = str(uuid4())
        new_cid = str(uuid4())
        
        set_correlation_id(old_cid)
        
        with LogContext(new_cid):
            assert get_correlation_id() == new_cid
        
        assert get_correlation_id() == old_cid


class TestConfigureLogging:
    """Tests for logging configuration."""
    
    def setup_method(self):
        """Reset correlation ID before each test."""
        set_correlation_id(None)
    
    def test_configures_omen_logger(self):
        """Configures omen logger."""
        configure_logging(level=logging.DEBUG)
        
        logger = get_logger("test")
        assert logger.name == "omen.test"
    
    def test_json_format(self):
        """JSON format produces valid JSON."""
        stream = StringIO()
        configure_logging(json_format=True, stream=stream)
        
        logger = get_logger("json_test")
        set_correlation_id("test-123")
        logger.info("Test message")
        
        output = stream.getvalue()
        log_entry = json.loads(output.strip())
        
        assert log_entry["message"] == "Test message"
        assert log_entry["correlation_id"] == "test-123"
    
    def test_readable_format(self):
        """Readable format includes correlation ID."""
        stream = StringIO()
        configure_logging(json_format=False, stream=stream)
        
        logger = get_logger("readable_test")
        set_correlation_id("abcd1234-5678")
        logger.info("Test message")
        
        output = stream.getvalue()
        assert "abcd1234" in output  # Short form
        assert "Test message" in output

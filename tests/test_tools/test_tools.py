"""Tests for the tools module — L6 tool execution infrastructure."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from omen.orchestrator.ledger import ActiveToken
from omen.tools import (
    ToolSafety,
    EvidenceRef,
    ToolResult,
    ClockTool,
    FileReadTool,
    FileWriteTool,
    HttpGetTool,
    EnvironmentTool,
    ToolRegistry,
    ToolNotFoundError,
    UnauthorizedToolError,
    create_default_registry,
)


# =============================================================================
# ToolResult Tests
# =============================================================================

def test_tool_result_ok_creates_evidence():
    """ToolResult.ok() creates evidence ref automatically."""
    result = ToolResult.ok(
        data={"value": 42},
        tool_name="test_tool",
    )
    
    assert result.success is True
    assert result.data == {"value": 42}
    assert result.evidence_ref is not None
    assert result.evidence_ref.tool_name == "test_tool"
    assert result.evidence_ref.ref_type == "tool_output"


def test_tool_result_fail_has_no_evidence():
    """ToolResult.fail() has no evidence."""
    result = ToolResult.fail("something broke")
    
    assert result.success is False
    assert result.error == "something broke"
    assert result.evidence_ref is None


def test_evidence_ref_to_dict():
    """EvidenceRef.to_dict() serializes correctly."""
    ref = EvidenceRef(
        tool_name="clock",
        reliability_score=0.99,
        raw_data={"time": "2025-12-28"},
    )
    
    d = ref.to_dict()
    assert d["ref_id"].startswith("ev_")
    assert d["tool_name"] == "clock"
    assert d["reliability_score"] == 0.99
    assert d["ref_type"] == "tool_output"
    assert "timestamp" in d


# =============================================================================
# ClockTool Tests
# =============================================================================

def test_clock_tool_returns_current_time():
    """ClockTool returns current time."""
    tool = ClockTool()
    
    assert tool.name == "clock"
    assert tool.safety == ToolSafety.READ
    
    result = tool.execute({})
    
    assert result.success is True
    assert "current_time" in result.data
    assert result.evidence_ref is not None


def test_clock_tool_supports_format():
    """ClockTool supports custom format."""
    tool = ClockTool()
    
    result = tool.execute({"format": "%Y-%m-%d"})
    
    assert result.success is True
    assert len(result.data["current_time"]) == 10  # YYYY-MM-DD


# =============================================================================
# FileReadTool Tests
# =============================================================================

def test_file_read_tool_reads_content():
    """FileReadTool reads file content."""
    tool = FileReadTool()
    
    assert tool.name == "file_read"
    assert tool.safety == ToolSafety.READ
    
    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Hello, OMEN!")
        path = f.name
    
    try:
        result = tool.execute({"path": path})
        
        assert result.success is True
        assert result.data["content"] == "Hello, OMEN!"
        assert result.data["path"] == path
        assert result.evidence_ref.raw_data == "Hello, OMEN!"
    finally:
        Path(path).unlink()


def test_file_read_tool_fails_on_missing_file():
    """FileReadTool fails gracefully on missing file."""
    tool = FileReadTool()
    
    result = tool.execute({"path": "/nonexistent/file.txt"})
    
    assert result.success is False
    assert "not found" in result.error.lower()


# =============================================================================
# FileWriteTool Tests
# =============================================================================

def test_file_write_tool_requires_authorization():
    """FileWriteTool is marked as WRITE."""
    tool = FileWriteTool()
    
    assert tool.name == "file_write"
    assert tool.safety == ToolSafety.WRITE


def test_file_write_tool_writes_content():
    """FileWriteTool writes content."""
    tool = FileWriteTool()
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        path = f.name
    
    try:
        result = tool.execute({
            "path": path,
            "content": "Test content",
        })
        
        assert result.success is True
        assert result.data["path"] == path
        
        # Verify content
        with open(path, 'r') as f:
            assert f.read() == "Test content"
    finally:
        Path(path).unlink()


# =============================================================================
# HttpGetTool Tests
# =============================================================================

def test_http_get_tool_metadata():
    """HttpGetTool has correct metadata."""
    tool = HttpGetTool()
    
    assert tool.name == "http_get"
    assert tool.safety == ToolSafety.READ


# =============================================================================
# EnvironmentTool Tests
# =============================================================================

def test_environment_tool_reads_safe_vars():
    """EnvironmentTool reads safe environment variables."""
    tool = EnvironmentTool()
    
    assert tool.name == "env_read"
    assert tool.safety == ToolSafety.READ
    
    # Read all safe vars
    result = tool.execute({})
    
    assert result.success is True
    assert isinstance(result.data, dict)


def test_environment_tool_rejects_unsafe_vars():
    """EnvironmentTool rejects unsafe variables."""
    tool = EnvironmentTool()
    
    result = tool.execute({"name": "SECRET_KEY"})
    
    assert result.success is False
    assert "not in safe list" in result.error


# =============================================================================
# ToolRegistry Tests
# =============================================================================

def test_registry_registers_and_lists_tools():
    """ToolRegistry registers and lists tools."""
    registry = ToolRegistry()
    clock = ClockTool()
    
    registry.register(clock)
    
    assert registry.get("clock") == clock
    assert "clock" in registry.list_tool_names()
    assert clock in registry.list_tools()


def test_registry_unregisters_tools():
    """ToolRegistry unregisters tools."""
    registry = ToolRegistry()
    clock = ClockTool()
    
    registry.register(clock)
    removed = registry.unregister("clock")
    
    assert removed == clock
    assert registry.get("clock") is None


def test_registry_execute_read_tool_no_token():
    """Registry executes READ tools without token."""
    registry = ToolRegistry()
    registry.register(ClockTool())
    
    result = registry.execute("clock", {})
    
    assert result.success is True


def test_registry_execute_write_tool_requires_token():
    """Registry requires token for WRITE tools."""
    registry = ToolRegistry()
    registry.register(FileWriteTool())
    
    with pytest.raises(UnauthorizedToolError):
        registry.execute("file_write", {"path": "/tmp/test.txt", "content": "data"})


def test_registry_execute_write_tool_with_valid_token():
    """Registry executes WRITE tools with valid token."""
    from datetime import timedelta
    
    registry = ToolRegistry()
    registry.register(FileWriteTool())
    
    token = ActiveToken(
        token_id="test_token",
        scope={"authorized_actions": ["file_write"]},
        issued_at=datetime.now(),
        expires_at=datetime.now() + timedelta(hours=1),
        max_uses=1,
        uses_remaining=1,
    )
    
    with tempfile.NamedTemporaryFile(delete=False) as f:
        path = f.name
    
    try:
        result = registry.execute(
            "file_write",
            {"path": path, "content": "authorized"},
            token=token,
        )
        
        assert result.success is True
        assert token.uses_remaining == 0  # Token consumed
    finally:
        Path(path).unlink()


def test_registry_execute_nonexistent_tool_raises():
    """Registry raises ToolNotFoundError for missing tools."""
    registry = ToolRegistry()
    
    with pytest.raises(ToolNotFoundError):
        registry.execute("nonexistent", {})


def test_registry_get_tool_descriptions():
    """Registry generates tool descriptions for LLM context."""
    registry = ToolRegistry()
    registry.register(ClockTool())
    registry.register(FileWriteTool())
    
    desc = registry.get_tool_descriptions()
    
    assert "clock" in desc
    assert "file_write" in desc
    assert "[WRITE]" in desc  # Safety marker for file_write


def test_create_default_registry():
    """create_default_registry() creates registry with all built-in tools."""
    registry = create_default_registry()
    
    assert registry.get("clock") is not None
    assert registry.get("file_read") is not None
    assert registry.get("file_write") is not None
    assert registry.get("http_get") is not None
    assert registry.get("env_read") is not None
    
    # Should have exactly 5 built-in tools
    assert len(registry.list_tools()) == 5

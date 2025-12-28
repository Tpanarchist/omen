"""Integration tests for L6 with tool execution."""

import tempfile
from pathlib import Path

import pytest

from omen.orchestrator.ledger import ActiveToken
from omen.orchestrator.pool import create_layer_pool
from omen.clients.openai_client import OpenAIClient
from omen.tools import create_default_registry
from omen.vocabulary import LayerSource


@pytest.mark.integration
@pytest.mark.slow
def test_l6_has_tool_registry():
    """L6 layer receives tool registry when created."""
    registry = create_default_registry()
    
    pool = create_layer_pool(
        llm_client=OpenAIClient(),
        include_layers=[LayerSource.LAYER_6],
        tool_registry=registry,
    )
    
    l6 = pool.get_layer(LayerSource.LAYER_6)
    
    assert l6 is not None
    assert l6._tool_registry is registry


@pytest.mark.integration
def test_l6_execute_tool_without_registry():
    """L6 without tool registry returns failure."""
    pool = create_layer_pool(
        include_layers=[LayerSource.LAYER_6],
    )
    
    l6 = pool.get_layer(LayerSource.LAYER_6)
    result = l6.execute_tool("clock", {})
    
    assert result.success is False
    assert "No tool registry" in result.error


@pytest.mark.integration
def test_l6_execute_read_tool():
    """L6 can execute READ tools via tool registry."""
    registry = create_default_registry()
    
    pool = create_layer_pool(
        include_layers=[LayerSource.LAYER_6],
        tool_registry=registry,
    )
    
    l6 = pool.get_layer(LayerSource.LAYER_6)
    result = l6.execute_tool("clock", {})
    
    assert result.success is True
    assert "current_time" in result.data
    assert result.evidence_ref is not None


@pytest.mark.integration
def test_l6_execute_write_tool_with_token():
    """L6 can execute WRITE tools with valid token."""
    from datetime import datetime, timedelta
    
    registry = create_default_registry()
    token = ActiveToken(
        token_id="test_token",
        scope={"authorized_actions": ["file_write"]},
        issued_at=datetime.now(),
        expires_at=datetime.now() + timedelta(hours=1),
        max_uses=1,
        uses_remaining=1,
    )
    
    pool = create_layer_pool(
        include_layers=[LayerSource.LAYER_6],
        tool_registry=registry,
    )
    
    with tempfile.NamedTemporaryFile(delete=False) as f:
        path = f.name
    
    try:
        l6 = pool.get_layer(LayerSource.LAYER_6)
        result = l6.execute_tool(
            "file_write",
            {"path": path, "content": "L6 wrote this"},
            token=token,
        )
        
        assert result.success is True
        
        # Verify content
        with open(path, 'r') as f:
            assert f.read() == "L6 wrote this"
    finally:
        Path(path).unlink()


@pytest.mark.integration
def test_l6_execute_write_tool_without_token_fails():
    """L6 cannot execute WRITE tools without token."""
    from omen.tools import UnauthorizedToolError
    
    registry = create_default_registry()
    
    pool = create_layer_pool(
        include_layers=[LayerSource.LAYER_6],
        tool_registry=registry,
    )
    
    l6 = pool.get_layer(LayerSource.LAYER_6)
    
    with pytest.raises(UnauthorizedToolError):
        l6.execute_tool("file_write", {"path": "/tmp/test.txt", "content": "data"})

"""
Integration test configuration.

These tests call real APIs and cost money.
Run with: pytest -m integration
Skip with: pytest -m "not integration"
"""

import os
import json
import pytest

from omen.clients import OPENAI_AVAILABLE, create_openai_client


def pytest_configure(config):
    """Register integration marker."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may incur API costs)"
    )


@pytest.fixture(scope="session")
def openai_client():
    """
    Session-scoped OpenAI client.
    
    Skips if API key not available.
    """
    if not OPENAI_AVAILABLE:
        pytest.skip("OpenAI package not installed")
    
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    
    return create_openai_client(model="gpt-4o-mini", max_tokens=1000)


@pytest.fixture
def integration_orchestrator(openai_client):
    """Orchestrator with real LLM client."""
    from omen.orchestrator import create_orchestrator
    return create_orchestrator(llm_client=openai_client)


@pytest.fixture
def response_log(tmp_path):
    """Log raw responses to file for offline analysis."""
    log_file = tmp_path / "responses.jsonl"
    
    def log(layer: str, response: str, context: dict | None = None):
        with open(log_file, "a") as f:
            entry = {
                "layer": layer,
                "response": response,
                "context": context or {},
            }
            f.write(json.dumps(entry) + "\n")
    
    # Return both the logger function and the path for inspection
    log.path = log_file
    return log

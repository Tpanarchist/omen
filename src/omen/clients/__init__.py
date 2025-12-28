"""
Clients — LLM client implementations.

Provides real and mock LLM clients for layer invocation.
"""

from omen.clients.openai_client import (
    OpenAIConfig,
    OpenAIClient,
    create_openai_client,
    OPENAI_AVAILABLE,
)

__all__ = [
    "OpenAIConfig",
    "OpenAIClient", 
    "create_openai_client",
    "OPENAI_AVAILABLE",
]

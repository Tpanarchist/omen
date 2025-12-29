"""
OpenAI Client — Real LLM client for OMEN layers.

Implements LLMClient protocol using OpenAI's API.
"""

import os
import time
from dataclasses import dataclass
from typing import Any, Callable

try:
    from openai import OpenAI, APIError, RateLimitError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


@dataclass
class OpenAIConfig:
    """Configuration for OpenAI client."""
    api_key: str | None = None  # Falls back to OPENAI_API_KEY env var
    model: str = "gpt-4o-mini"  # Cost-effective for testing
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: float = 60.0
    max_retries: int = 3
    retry_delay: float = 1.0


class OpenAIClient:
    """
    OpenAI API client implementing LLMClient protocol.
    
    Usage:
        client = OpenAIClient()  # Uses OPENAI_API_KEY env var
        response = client.complete(system_prompt, user_message)
    """
    
    def __init__(
        self,
        config: OpenAIConfig | None = None,
        on_usage: Callable[[dict], None] | None = None,
    ):
        """
        Initialize OpenAI client.
        
        Args:
            config: Client configuration
            on_usage: Optional callback for token usage tracking.
                     Called with dict containing prompt_tokens, completion_tokens, total_tokens.
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI package not installed. "
                "Install with: pip install openai"
            )
        
        self.config = config or OpenAIConfig()
        self._on_usage = on_usage
        
        # Get API key
        api_key = self.config.api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. "
                "Set OPENAI_API_KEY environment variable or pass api_key in config."
            )
        
        self._client = OpenAI(api_key=api_key, timeout=self.config.timeout)
        self._last_usage: dict[str, int] = {}
    
    def complete(
        self,
        system_prompt: str,
        user_message: str,
        **kwargs: Any
    ) -> str:
        """
        Generate a completion using OpenAI's API.
        
        Implements retry logic for transient failures.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                response = self._client.chat.completions.create(
                    model=kwargs.get("model", self.config.model),
                    messages=messages,
                    temperature=kwargs.get("temperature", self.config.temperature),
                    max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                )
                
                # Track usage
                if response.usage:
                    self._last_usage = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    }
                    
                    # Call usage callback if provided
                    if self._on_usage:
                        self._on_usage(self._last_usage)
                
                return response.choices[0].message.content or ""
                
            except RateLimitError as e:
                last_error = e
                wait_time = self.config.retry_delay * (2 ** attempt)
                time.sleep(wait_time)
                continue
                
            except APIError as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
                    continue
                raise
        
        raise last_error or Exception("Max retries exceeded")
    
    @property
    def last_usage(self) -> dict[str, int]:
        """Get token usage from last call."""
        return self._last_usage.copy()


def create_openai_client(
    model: str = "gpt-4o-mini",
    **kwargs: Any
) -> OpenAIClient:
    """Factory for OpenAI client."""
    config = OpenAIConfig(model=model, **kwargs)
    return OpenAIClient(config)

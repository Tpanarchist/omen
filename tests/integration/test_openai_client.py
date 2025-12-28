"""Integration tests for OpenAI client."""

import pytest

from omen.clients import OpenAIClient, create_openai_client


@pytest.mark.integration
class TestOpenAIClientConnection:
    """Tests for OpenAI API connectivity."""
    
    def test_simple_completion(self, openai_client):
        """Can complete a simple prompt."""
        response = openai_client.complete(
            system_prompt="You are a helpful assistant.",
            user_message="Say 'hello' and nothing else.",
        )
        
        assert len(response) > 0
        assert "hello" in response.lower()
    
    def test_tracks_usage(self, openai_client):
        """Tracks token usage."""
        openai_client.complete(
            system_prompt="Be brief.",
            user_message="Say 'test'.",
        )
        
        usage = openai_client.last_usage
        assert usage.get("total_tokens", 0) > 0
        assert usage.get("prompt_tokens", 0) > 0
        assert usage.get("completion_tokens", 0) > 0
    
    def test_json_output(self, openai_client):
        """Can request JSON output."""
        response = openai_client.complete(
            system_prompt="You only respond with valid JSON. No other text.",
            user_message='Return: {"status": "ok"}',
        )
        
        import json
        # Should be parseable (maybe with surrounding text)
        assert "{" in response and "}" in response
        
        # Try to extract and parse JSON
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = response[start:end]
            parsed = json.loads(json_str)
            assert "status" in parsed

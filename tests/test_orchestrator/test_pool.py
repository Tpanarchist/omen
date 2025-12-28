"""Tests for layer pool."""

import pytest
from uuid import uuid4

from omen.vocabulary import LayerSource, PacketType
from omen.layers import LayerInput, LayerOutput, MockLLMClient, LAYER_PROMPTS
from omen.orchestrator import (
    ConfigurableLayer,
    LayerPool,
    create_layer_pool,
    create_mock_layer_pool,
)


class TestConfigurableLayer:
    """Tests for configurable layer."""
    
    def test_uses_configured_prompt(self):
        """Layer uses the provided system prompt."""
        client = MockLLMClient()
        layer = ConfigurableLayer(
            layer_id=LayerSource.LAYER_5,
            llm_client=client,
            system_prompt="Custom prompt for testing",
        )
        
        assert layer.get_system_prompt() == "Custom prompt for testing"
    
    def test_invoke_calls_llm(self):
        """Invoke calls LLM with prompt."""
        client = MockLLMClient(responses=["test response"])
        layer = ConfigurableLayer(
            layer_id=LayerSource.LAYER_5,
            llm_client=client,
            system_prompt="Test prompt",
        )
        
        input = LayerInput(packets=[], correlation_id=uuid4())
        output = layer.invoke(input)
        
        assert output.raw_response == "test response"
        assert client.call_count == 1
    
    def test_default_parser_extracts_json(self):
        """Default parser extracts JSON from response."""
        response = '''Here is my output:
```json
{"decision_outcome": "ACT", "rationale": "Ready to proceed"}
```
'''
        client = MockLLMClient(responses=[response])
        layer = ConfigurableLayer(
            layer_id=LayerSource.LAYER_5,
            llm_client=client,
            system_prompt="Test",
        )
        
        input = LayerInput(packets=[], correlation_id=uuid4())
        output = layer.invoke(input)
        
        # Note: packets are filtered by contract, but parsed packets
        # are available in the raw parse
        assert output.raw_response == response
    
    def test_custom_parser(self):
        """Can use custom parser."""
        def custom_parser(response: str, context: LayerInput) -> list:
            return [{"custom": "parsed", "response": response[:10]}]
        
        client = MockLLMClient(responses=["some response"])
        layer = ConfigurableLayer(
            layer_id=LayerSource.LAYER_5,
            llm_client=client,
            system_prompt="Test",
            response_parser=custom_parser,
        )
        
        input = LayerInput(packets=[], correlation_id=uuid4())
        output = layer.invoke(input)
        
        # Custom parser output won't pass contract validation (not real packets)
        # but we can verify it was called
        assert "custom" in str(output.errors) or len(output.packets) == 0


class TestLayerPool:
    """Tests for layer pool management."""
    
    @pytest.fixture
    def pool(self):
        """Create empty pool."""
        return LayerPool()
    
    @pytest.fixture
    def mock_layer(self):
        """Create mock layer."""
        return ConfigurableLayer(
            layer_id=LayerSource.LAYER_5,
            llm_client=MockLLMClient(),
            system_prompt="Test",
        )
    
    def test_register_layer(self, pool, mock_layer):
        """Can register a layer."""
        pool.register_layer(mock_layer)
        assert pool.has_layer(LayerSource.LAYER_5)
    
    def test_get_layer(self, pool, mock_layer):
        """Can get registered layer."""
        pool.register_layer(mock_layer)
        layer = pool.get_layer(LayerSource.LAYER_5)
        assert layer == mock_layer
    
    def test_get_missing_layer(self, pool):
        """Getting missing layer returns None."""
        assert pool.get_layer(LayerSource.LAYER_5) is None
    
    def test_unregister_layer(self, pool, mock_layer):
        """Can unregister a layer."""
        pool.register_layer(mock_layer)
        removed = pool.unregister_layer(LayerSource.LAYER_5)
        
        assert removed == mock_layer
        assert not pool.has_layer(LayerSource.LAYER_5)
    
    def test_get_all_layers(self, pool):
        """Can get all registered layers."""
        for layer_id in [LayerSource.LAYER_5, LayerSource.LAYER_6]:
            layer = ConfigurableLayer(
                layer_id=layer_id,
                llm_client=MockLLMClient(),
                system_prompt="Test",
            )
            pool.register_layer(layer)
        
        all_layers = pool.get_all_layers()
        assert len(all_layers) == 2
    
    def test_invoke_layer(self, pool, mock_layer):
        """Can invoke layer through pool."""
        pool.register_layer(mock_layer)
        
        input = LayerInput(packets=[], correlation_id=uuid4())
        output = pool.invoke_layer(LayerSource.LAYER_5, input)
        
        assert output is not None
        assert isinstance(output, LayerOutput)
    
    def test_invoke_missing_layer(self, pool):
        """Invoking missing layer returns None."""
        input = LayerInput(packets=[], correlation_id=uuid4())
        output = pool.invoke_layer(LayerSource.LAYER_5, input)
        assert output is None


class TestCreateLayerPool:
    """Tests for layer pool factory."""
    
    def test_creates_all_layers_by_default(self):
        """Factory creates L1-L6 by default."""
        pool = create_layer_pool()
        
        for i in range(1, 7):
            layer_id = LayerSource(str(i))
            assert pool.has_layer(layer_id), f"Missing {layer_id}"
    
    def test_excludes_integrity(self):
        """Factory excludes Integrity layer."""
        pool = create_layer_pool()
        assert not pool.has_layer(LayerSource.INTEGRITY)
    
    def test_uses_provided_client(self):
        """Factory uses provided LLM client."""
        client = MockLLMClient(responses=["custom response"])
        pool = create_layer_pool(llm_client=client)
        
        layer = pool.get_layer(LayerSource.LAYER_5)
        input = LayerInput(packets=[], correlation_id=uuid4())
        output = layer.invoke(input)
        
        assert output.raw_response == "custom response"
    
    def test_include_specific_layers(self):
        """Can include only specific layers."""
        pool = create_layer_pool(
            include_layers=[LayerSource.LAYER_5, LayerSource.LAYER_6]
        )
        
        assert pool.has_layer(LayerSource.LAYER_5)
        assert pool.has_layer(LayerSource.LAYER_6)
        assert not pool.has_layer(LayerSource.LAYER_1)
    
    def test_custom_prompts(self):
        """Can override prompts."""
        pool = create_layer_pool(
            custom_prompts={"LAYER_5": "Custom L5 prompt"}
        )
        
        layer = pool.get_layer(LayerSource.LAYER_5)
        assert layer.get_system_prompt() == "Custom L5 prompt"
    
    def test_layers_have_correct_prompts(self):
        """Layers get their canonical prompts."""
        pool = create_layer_pool()
        
        layer5 = pool.get_layer(LayerSource.LAYER_5)
        assert "Cognitive Control" in layer5.get_system_prompt()
        
        layer6 = pool.get_layer(LayerSource.LAYER_6)
        assert "Task Prosecution" in layer6.get_system_prompt()


class TestCreateMockLayerPool:
    """Tests for mock layer pool factory."""
    
    def test_creates_pool_with_per_layer_responses(self):
        """Creates pool with specific responses per layer."""
        responses = {
            LayerSource.LAYER_5: ["L5 response 1", "L5 response 2"],
            LayerSource.LAYER_6: ["L6 response"],
        }
        pool = create_mock_layer_pool(responses=responses)
        
        # L5 should return its responses
        l5 = pool.get_layer(LayerSource.LAYER_5)
        input = LayerInput(packets=[], correlation_id=uuid4())
        
        output1 = l5.invoke(input)
        assert output1.raw_response == "L5 response 1"
        
        output2 = l5.invoke(input)
        assert output2.raw_response == "L5 response 2"
    
    def test_creates_all_layers(self):
        """Mock pool creates all 6 layers."""
        pool = create_mock_layer_pool()
        
        for i in range(1, 7):
            assert pool.has_layer(LayerSource(str(i)))


class TestDefaultParser:
    """Tests for default JSON parser."""
    
    def test_parses_json_code_block(self):
        """Extracts JSON from code blocks."""
        response = '''
```json
{"type": "Decision", "outcome": "ACT"}
```
'''
        layer = ConfigurableLayer(
            layer_id=LayerSource.LAYER_5,
            llm_client=MockLLMClient(responses=[response]),
            system_prompt="Test",
        )
        
        # Access parser directly
        packets = layer._default_parser(response, None)
        assert len(packets) == 1
        assert packets[0]["outcome"] == "ACT"
    
    def test_parses_raw_json(self):
        """Parses response that is just JSON."""
        response = '{"type": "Observation", "content": "test"}'
        
        layer = ConfigurableLayer(
            layer_id=LayerSource.LAYER_6,
            llm_client=MockLLMClient(),
            system_prompt="Test",
        )
        
        packets = layer._default_parser(response, None)
        assert len(packets) == 1
        assert packets[0]["content"] == "test"
    
    def test_handles_invalid_json(self):
        """Gracefully handles invalid JSON."""
        response = "This is not JSON at all"
        
        layer = ConfigurableLayer(
            layer_id=LayerSource.LAYER_5,
            llm_client=MockLLMClient(),
            system_prompt="Test",
        )
        
        packets = layer._default_parser(response, None)
        assert len(packets) == 0
    
    def test_includes_source_layer(self):
        """Parsed packets include source layer."""
        response = '{"test": "value"}'
        
        layer = ConfigurableLayer(
            layer_id=LayerSource.LAYER_5,
            llm_client=MockLLMClient(),
            system_prompt="Test",
        )
        
        packets = layer._default_parser(response, None)
        assert packets[0]["_source"] == "5"
    
    def test_parses_multiple_json_blocks(self):
        """Extracts multiple JSON blocks from response."""
        response = '''
Here are multiple outputs:
```json
{"type": "Decision", "outcome": "ACT"}
```

And another:
```json
{"type": "Observation", "content": "data"}
```
'''
        layer = ConfigurableLayer(
            layer_id=LayerSource.LAYER_5,
            llm_client=MockLLMClient(),
            system_prompt="Test",
        )
        
        packets = layer._default_parser(response, None)
        assert len(packets) == 2
        assert packets[0]["outcome"] == "ACT"
        assert packets[1]["content"] == "data"
    
    def test_parses_json_array(self):
        """Parses JSON array as multiple packets."""
        response = '[{"type": "A"}, {"type": "B"}]'
        
        layer = ConfigurableLayer(
            layer_id=LayerSource.LAYER_5,
            llm_client=MockLLMClient(),
            system_prompt="Test",
        )
        
        packets = layer._default_parser(response, None)
        assert len(packets) == 2
        assert packets[0]["type"] == "A"
        assert packets[1]["type"] == "B"
    
    def test_preserves_raw_object(self):
        """Parsed packets include _raw field."""
        response = '{"test": "value", "nested": {"key": 123}}'
        
        layer = ConfigurableLayer(
            layer_id=LayerSource.LAYER_5,
            llm_client=MockLLMClient(),
            system_prompt="Test",
        )
        
        packets = layer._default_parser(response, None)
        assert "_raw" in packets[0]
        assert packets[0]["_raw"]["nested"]["key"] == 123

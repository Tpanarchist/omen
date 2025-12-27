"""Tests for layer base class."""

import pytest
from uuid import uuid4
from unittest.mock import Mock

from omen.vocabulary import LayerSource, PacketType
from omen.layers import (
    Layer,
    LayerInput,
    LayerOutput,
    MockLLMClient,
    create_mock_client,
    get_contract,
    LAYER_5_CONTRACT,
    LAYER_6_CONTRACT,
    LAYER_NAMES,
)


# =============================================================================
# CONCRETE TEST LAYER
# =============================================================================

class TestLayer(Layer):
    """Concrete layer implementation for testing."""
    
    def __init__(self, layer_id: LayerSource, llm_client, **kwargs):
        super().__init__(layer_id, llm_client, **kwargs)
        self.parse_result: list = []  # What parse_response returns
    
    def get_system_prompt(self) -> str:
        return f"You are Layer {self.layer_id.value}. Process inputs and respond."
    
    def parse_response(self, response: str, context: LayerInput) -> list:
        return self.parse_result


class MockPacket:
    """Mock packet for testing."""
    def __init__(self, packet_type: PacketType):
        self.header = Mock()
        self.header.packet_type = packet_type


# =============================================================================
# TESTS
# =============================================================================

class TestMockLLMClient:
    """Tests for mock LLM client."""
    
    def test_returns_predefined_responses(self):
        """Client returns responses in order."""
        client = create_mock_client(["first", "second"])
        assert client.complete("sys", "user") == "first"
        assert client.complete("sys", "user") == "second"
    
    def test_echoes_when_exhausted(self):
        """Client echoes when responses exhausted."""
        client = create_mock_client(["only"])
        client.complete("sys", "user1")
        result = client.complete("sys", "user2")
        assert result.startswith("Echo:")
    
    def test_tracks_calls(self):
        """Client tracks all calls."""
        client = create_mock_client()
        client.complete("system1", "user1")
        client.complete("system2", "user2")
        
        assert client.call_count == 2
        assert client.last_call()["system_prompt"] == "system2"
    
    def test_empty_responses_list(self):
        """Client works with empty responses list."""
        client = create_mock_client([])
        result = client.complete("sys", "user")
        assert result.startswith("Echo:")
    
    def test_tracks_kwargs(self):
        """Client tracks additional kwargs."""
        client = create_mock_client(["response"])
        client.complete("sys", "user", temperature=0.7, max_tokens=100)
        
        call = client.last_call()
        assert call["temperature"] == 0.7
        assert call["max_tokens"] == 100


class TestLayerInput:
    """Tests for LayerInput."""
    
    def test_create_input(self):
        """Create layer input bundle."""
        cid = uuid4()
        input = LayerInput(
            packets=[MockPacket(PacketType.OBSERVATION)],
            correlation_id=cid,
        )
        assert input.correlation_id == cid
        assert len(input.packets) == 1
    
    def test_optional_fields(self):
        """Input has optional campaign_id and context."""
        input = LayerInput(
            packets=[],
            correlation_id=uuid4(),
            campaign_id="campaign-123",
            context={"key": "value"},
        )
        assert input.campaign_id == "campaign-123"
        assert input.context["key"] == "value"
    
    def test_timestamp_auto_generated(self):
        """Timestamp is auto-generated if not provided."""
        input = LayerInput(packets=[], correlation_id=uuid4())
        assert input.timestamp is not None


class TestLayerOutput:
    """Tests for LayerOutput."""
    
    def test_success_when_no_errors(self):
        """Output is success when no errors."""
        output = LayerOutput(
            packets=[],
            layer=LayerSource.LAYER_5,
            correlation_id=uuid4(),
        )
        assert output.success is True
    
    def test_not_success_with_errors(self):
        """Output is not success when errors present."""
        output = LayerOutput(
            packets=[],
            layer=LayerSource.LAYER_5,
            correlation_id=uuid4(),
            errors=["something went wrong"],
        )
        assert output.success is False
    
    def test_multiple_errors(self):
        """Output can have multiple errors."""
        output = LayerOutput(
            packets=[],
            layer=LayerSource.LAYER_5,
            correlation_id=uuid4(),
            errors=["error1", "error2"],
        )
        assert len(output.errors) == 2
        assert output.success is False


class TestLayerInitialization:
    """Tests for layer initialization."""
    
    def test_create_layer(self):
        """Create layer with defaults."""
        client = create_mock_client()
        layer = TestLayer(LayerSource.LAYER_5, client)
        
        assert layer.layer_id == LayerSource.LAYER_5
        assert layer.contract == LAYER_5_CONTRACT
    
    def test_contract_mismatch_raises(self):
        """Mismatched contract raises ValueError."""
        client = create_mock_client()
        with pytest.raises(ValueError) as exc_info:
            TestLayer(
                LayerSource.LAYER_5, 
                client, 
                contract=LAYER_6_CONTRACT  # Wrong!
            )
        assert "doesn't match" in str(exc_info.value)
    
    def test_custom_contract(self):
        """Can provide custom contract."""
        client = create_mock_client()
        layer = TestLayer(LayerSource.LAYER_5, client, contract=LAYER_5_CONTRACT)
        assert layer.contract == LAYER_5_CONTRACT
    
    def test_layer_name_property(self):
        """Layer has human-readable name."""
        client = create_mock_client()
        layer = TestLayer(LayerSource.LAYER_5, client)
        assert layer.layer_name == "Cognitive Control"
    
    def test_all_layer_names(self):
        """All layer sources have names."""
        client = create_mock_client()
        for layer_source in [
            LayerSource.LAYER_1,
            LayerSource.LAYER_2,
            LayerSource.LAYER_3,
            LayerSource.LAYER_4,
            LayerSource.LAYER_5,
            LayerSource.LAYER_6,
            LayerSource.INTEGRITY,
        ]:
            layer = TestLayer(layer_source, client)
            assert layer.layer_name in LAYER_NAMES.values()


class TestLayerInvocation:
    """Tests for layer invocation."""
    
    @pytest.fixture
    def layer5(self):
        """Layer 5 for testing."""
        client = create_mock_client(["Test response"])
        return TestLayer(LayerSource.LAYER_5, client)
    
    def test_invoke_returns_output(self, layer5):
        """Invoke returns LayerOutput."""
        input = LayerInput(
            packets=[],
            correlation_id=uuid4(),
        )
        output = layer5.invoke(input)
        
        assert isinstance(output, LayerOutput)
        assert output.layer == LayerSource.LAYER_5
        assert output.raw_response == "Test response"
    
    def test_invoke_calls_llm(self, layer5):
        """Invoke calls LLM with system prompt."""
        input = LayerInput(
            packets=[],
            correlation_id=uuid4(),
        )
        layer5.invoke(input)
        
        assert layer5.llm_client.call_count == 1
        call = layer5.llm_client.last_call()
        assert "Layer 5" in call["system_prompt"]
    
    def test_invoke_preserves_correlation_id(self, layer5):
        """Output has same correlation_id as input."""
        cid = uuid4()
        input = LayerInput(packets=[], correlation_id=cid)
        output = layer5.invoke(input)
        
        assert output.correlation_id == cid
    
    def test_invoke_with_packets(self, layer5):
        """Invoke with input packets."""
        obs = MockPacket(PacketType.OBSERVATION)
        input = LayerInput(
            packets=[obs],
            correlation_id=uuid4(),
        )
        output = layer5.invoke(input)
        
        assert output.success is True


class TestInputFiltering:
    """Tests for input packet filtering."""
    
    def test_filters_by_contract(self):
        """Layer only receives packets it can receive."""
        client = create_mock_client(["response"])
        layer = TestLayer(LayerSource.LAYER_5, client)
        
        # L5 can receive Observation, not TaskDirective
        obs = MockPacket(PacketType.OBSERVATION)
        directive = MockPacket(PacketType.TASK_DIRECTIVE)  # L5 can't receive
        
        input = LayerInput(
            packets=[obs, directive],
            correlation_id=uuid4(),
        )
        layer.invoke(input)
        
        # Check what was in the context
        call = client.last_call()
        # Only one packet should be in context (the Observation)
        assert "Packet 1" in call["user_message"]
        # Should not have "Packet 2" since directive was filtered
        assert "Packet 2" not in call["user_message"]
    
    def test_filters_none_packet_type(self):
        """Packets without type are filtered out."""
        client = create_mock_client(["response"])
        layer = TestLayer(LayerSource.LAYER_5, client)
        
        # Create packet without header
        bad_packet = Mock()
        bad_packet.header = None
        
        input = LayerInput(
            packets=[bad_packet],
            correlation_id=uuid4(),
        )
        layer.invoke(input)
        
        call = client.last_call()
        assert "No input packets" in call["user_message"]
    
    def test_all_packets_filtered(self):
        """Works when all packets are filtered."""
        client = create_mock_client(["response"])
        layer = TestLayer(LayerSource.LAYER_5, client)
        
        # L5 can't receive TaskDirective
        directive = MockPacket(PacketType.TASK_DIRECTIVE)
        
        input = LayerInput(
            packets=[directive],
            correlation_id=uuid4(),
        )
        layer.invoke(input)
        
        call = client.last_call()
        assert "No input packets" in call["user_message"]


class TestOutputValidation:
    """Tests for output packet validation."""
    
    def test_valid_packets_emitted(self):
        """Valid packets are included in output."""
        client = create_mock_client(["response"])
        layer = TestLayer(LayerSource.LAYER_5, client)
        
        # L5 can emit Decision
        decision = MockPacket(PacketType.DECISION)
        layer.parse_result = [decision]
        
        output = layer.invoke(LayerInput(packets=[], correlation_id=uuid4()))
        
        assert len(output.packets) == 1
        assert output.success is True
    
    def test_invalid_packets_rejected(self):
        """Invalid packets are rejected with error."""
        client = create_mock_client(["response"])
        layer = TestLayer(LayerSource.LAYER_5, client)
        
        # L5 cannot emit Observation
        obs = MockPacket(PacketType.OBSERVATION)
        layer.parse_result = [obs]
        
        output = layer.invoke(LayerInput(packets=[], correlation_id=uuid4()))
        
        assert len(output.packets) == 0
        assert len(output.errors) > 0
        assert "cannot emit" in output.errors[0]
    
    def test_mixed_valid_invalid(self):
        """Mix of valid and invalid packets."""
        client = create_mock_client(["response"])
        layer = TestLayer(LayerSource.LAYER_5, client)
        
        # L5 can emit Decision but not Observation
        decision = MockPacket(PacketType.DECISION)
        obs = MockPacket(PacketType.OBSERVATION)
        layer.parse_result = [decision, obs]
        
        output = layer.invoke(LayerInput(packets=[], correlation_id=uuid4()))
        
        assert len(output.packets) == 1  # Only decision
        assert len(output.errors) == 1  # Error for observation
    
    def test_packet_without_type_rejected(self):
        """Packet without type is rejected."""
        client = create_mock_client(["response"])
        layer = TestLayer(LayerSource.LAYER_5, client)
        
        bad_packet = Mock()
        bad_packet.header = None
        layer.parse_result = [bad_packet]
        
        output = layer.invoke(LayerInput(packets=[], correlation_id=uuid4()))
        
        assert len(output.packets) == 0
        assert len(output.errors) > 0
        assert "missing type" in output.errors[0]


class TestContextBuilding:
    """Tests for LLM context building."""
    
    def test_includes_correlation_id(self):
        """Context includes correlation ID."""
        client = create_mock_client(["response"])
        layer = TestLayer(LayerSource.LAYER_5, client)
        
        cid = uuid4()
        input = LayerInput(packets=[], correlation_id=cid)
        layer.invoke(input)
        
        call = client.last_call()
        assert str(cid) in call["user_message"]
    
    def test_includes_packets(self):
        """Context includes packet information."""
        client = create_mock_client(["response"])
        layer = TestLayer(LayerSource.LAYER_5, client)
        
        obs = MockPacket(PacketType.OBSERVATION)
        input = LayerInput(packets=[obs], correlation_id=uuid4())
        layer.invoke(input)
        
        call = client.last_call()
        assert "Packet" in call["user_message"]
    
    def test_includes_additional_context(self):
        """Context includes additional context dict."""
        client = create_mock_client(["response"])
        layer = TestLayer(LayerSource.LAYER_5, client)
        
        input = LayerInput(
            packets=[],
            correlation_id=uuid4(),
            context={"budget": 100, "priority": "high"},
        )
        layer.invoke(input)
        
        call = client.last_call()
        assert "budget" in call["user_message"]
        assert "priority" in call["user_message"]
    
    def test_empty_packets_message(self):
        """Shows message when no packets."""
        client = create_mock_client(["response"])
        layer = TestLayer(LayerSource.LAYER_5, client)
        
        input = LayerInput(packets=[], correlation_id=uuid4())
        layer.invoke(input)
        
        call = client.last_call()
        assert "No input packets" in call["user_message"]


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_llm_error_captured(self):
        """LLM errors are captured in output."""
        client = create_mock_client()
        client.complete = Mock(side_effect=Exception("API error"))
        
        layer = TestLayer(LayerSource.LAYER_5, client)
        output = layer.invoke(LayerInput(packets=[], correlation_id=uuid4()))
        
        assert output.success is False
        assert any("LLM error" in e for e in output.errors)
    
    def test_parse_error_captured(self):
        """Parse errors are captured in output."""
        client = create_mock_client(["response"])
        layer = TestLayer(LayerSource.LAYER_5, client)
        
        # Make parse_response raise
        def bad_parse(response, context):
            raise ValueError("Parse failed")
        layer.parse_response = bad_parse
        
        output = layer.invoke(LayerInput(packets=[], correlation_id=uuid4()))
        
        assert output.success is False
        assert any("Parse error" in e for e in output.errors)
    
    def test_llm_error_includes_raw_response(self):
        """LLM error returns empty raw_response."""
        client = create_mock_client()
        client.complete = Mock(side_effect=Exception("API error"))
        
        layer = TestLayer(LayerSource.LAYER_5, client)
        output = layer.invoke(LayerInput(packets=[], correlation_id=uuid4()))
        
        assert output.raw_response == ""
    
    def test_parse_error_includes_raw_response(self):
        """Parse error includes raw LLM response."""
        client = create_mock_client(["test response"])
        layer = TestLayer(LayerSource.LAYER_5, client)
        
        def bad_parse(response, context):
            raise ValueError("Parse failed")
        layer.parse_response = bad_parse
        
        output = layer.invoke(LayerInput(packets=[], correlation_id=uuid4()))
        
        assert output.raw_response == "test response"


class TestPacketFormatting:
    """Tests for packet formatting in context."""
    
    def test_formats_pydantic_model(self):
        """Formats Pydantic models with model_dump_json."""
        client = create_mock_client(["response"])
        layer = TestLayer(LayerSource.LAYER_5, client)
        
        # Mock Pydantic model
        packet = Mock()
        packet.header = Mock()
        packet.header.packet_type = PacketType.OBSERVATION
        packet.model_dump_json = Mock(return_value='{"test": "data"}')
        
        input = LayerInput(packets=[packet], correlation_id=uuid4())
        layer.invoke(input)
        
        packet.model_dump_json.assert_called_once()
    
    def test_formats_with_model_dump(self):
        """Formats objects with model_dump method."""
        client = create_mock_client(["response"])
        layer = TestLayer(LayerSource.LAYER_5, client)
        
        # Mock object with model_dump
        packet = Mock()
        packet.header = Mock()
        packet.header.packet_type = PacketType.OBSERVATION
        packet.model_dump = Mock(return_value={"test": "data"})
        del packet.model_dump_json  # Ensure this doesn't exist
        
        input = LayerInput(packets=[packet], correlation_id=uuid4())
        layer.invoke(input)
        
        packet.model_dump.assert_called_once()
    
    def test_fallback_to_str(self):
        """Falls back to str() for other objects."""
        client = create_mock_client(["response"])
        layer = TestLayer(LayerSource.LAYER_5, client)
        
        # Simple object
        packet = MockPacket(PacketType.OBSERVATION)
        
        input = LayerInput(packets=[packet], correlation_id=uuid4())
        context = layer.build_context(input)
        
        assert "MockPacket" in context or "Mock" in context

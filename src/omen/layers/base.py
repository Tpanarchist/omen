"""
Layer Base Class — Common infrastructure for ACE layers.

Each layer is an LLM instance that receives packets, reasons, and emits packets.
The base class handles mechanics; subclasses provide prompts and parsing.

Spec: OMEN.md §6, §11.1, ACE_Framework.md
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

from omen.vocabulary import LayerSource, PacketType
from omen.layers.contracts import LayerContract, ContractEnforcer, get_contract


# =============================================================================
# LAYER NAME MAPPING
# =============================================================================

LAYER_NAMES = {
    LayerSource.LAYER_1: "Aspirational",
    LayerSource.LAYER_2: "Global Strategy",
    LayerSource.LAYER_3: "Agent Model",
    LayerSource.LAYER_4: "Executive Function",
    LayerSource.LAYER_5: "Cognitive Control",
    LayerSource.LAYER_6: "Task Prosecution",
    LayerSource.INTEGRITY: "Integrity",
}


# =============================================================================
# LLM CLIENT PROTOCOL
# =============================================================================

@runtime_checkable
class LLMClient(Protocol):
    """
    Protocol for LLM clients.
    
    Allows swapping implementations (OpenAI, Anthropic, mock, etc.)
    """
    
    def complete(
        self,
        system_prompt: str,
        user_message: str,
        **kwargs
    ) -> str:
        """
        Generate a completion.
        
        Args:
            system_prompt: The system/instruction prompt
            user_message: The user/context message
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
        
        Returns:
            The model's response text
        """
        ...


# =============================================================================
# LAYER INPUT/OUTPUT
# =============================================================================

@dataclass
class LayerInput:
    """
    Input bundle for layer invocation.
    
    Contains packets and context for the layer to process.
    """
    packets: list[Any]  # Incoming packets
    correlation_id: UUID
    campaign_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LayerOutput:
    """
    Output bundle from layer invocation.
    
    Contains emitted packets and metadata.
    """
    packets: list[Any]  # Emitted packets
    layer: LayerSource
    correlation_id: UUID
    raw_response: str = ""  # Original LLM response
    timestamp: datetime = field(default_factory=datetime.now)
    errors: list[str] = field(default_factory=list)
    
    @property
    def success(self) -> bool:
        """True if no errors occurred."""
        return len(self.errors) == 0


# =============================================================================
# LAYER BASE CLASS
# =============================================================================

class Layer(ABC):
    """
    Abstract base class for ACE cognitive layers.
    
    Subclasses must implement:
    - get_system_prompt(): Returns the layer's system prompt
    - parse_response(): Converts LLM response to packets
    
    May override:
    - build_context(): Customize how packets become LLM context
    - validate_output(): Add layer-specific validation
    """
    
    def __init__(
        self,
        layer_id: LayerSource,
        llm_client: LLMClient,
        contract: LayerContract | None = None,
        enforcer: ContractEnforcer | None = None,
    ):
        """
        Initialize layer.
        
        Args:
            layer_id: Which layer this is (LAYER_1 through LAYER_6)
            llm_client: Client for LLM completions
            contract: Layer contract (defaults to canonical contract)
            enforcer: Contract enforcer (defaults to new enforcer)
        """
        self.layer_id = layer_id
        self.llm_client = llm_client
        self.contract = contract or get_contract(layer_id)
        self.enforcer = enforcer or ContractEnforcer()
        
        # Verify layer_id matches contract
        if self.contract.layer != layer_id:
            raise ValueError(
                f"Contract layer {self.contract.layer} doesn't match "
                f"layer_id {layer_id}"
            )
    
    @property
    def layer_name(self) -> str:
        """Human-readable layer name for logging/debugging."""
        return LAYER_NAMES.get(self.layer_id, str(self.layer_id))
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Return the system prompt for this layer.
        
        Defines the layer's role, responsibilities, and constraints.
        """
        pass
    
    @abstractmethod
    def parse_response(
        self,
        response: str,
        context: LayerInput,
    ) -> list[Any]:
        """
        Parse LLM response into packets.
        
        Args:
            response: Raw LLM response text
            context: Original input context
        
        Returns:
            List of packets to emit
        """
        pass
    
    def invoke(self, input: LayerInput) -> LayerOutput:
        """
        Invoke the layer with input packets.
        
        1. Filter input by contract (can we receive these?)
        2. Build context from packets
        3. Call LLM with system prompt + context
        4. Parse response into packets
        5. Validate output against contract
        6. Return output bundle
        """
        errors: list[str] = []
        
        # 1. Filter input packets by reception contract
        filtered_packets = self._filter_input(input.packets)
        filtered_input = LayerInput(
            packets=filtered_packets,
            correlation_id=input.correlation_id,
            campaign_id=input.campaign_id,
            context=input.context,
            timestamp=input.timestamp,
        )
        
        # 2. Build context for LLM
        user_message = self.build_context(filtered_input)
        
        # 3. Call LLM
        try:
            response = self.llm_client.complete(
                system_prompt=self.get_system_prompt(),
                user_message=user_message,
            )
        except Exception as e:
            errors.append(f"LLM error: {str(e)}")
            return LayerOutput(
                packets=[],
                layer=self.layer_id,
                correlation_id=input.correlation_id,
                raw_response="",
                errors=errors,
            )
        
        # 4. Parse response into packets
        try:
            packets = self.parse_response(response, filtered_input)
        except Exception as e:
            errors.append(f"Parse error: {str(e)}")
            return LayerOutput(
                packets=[],
                layer=self.layer_id,
                correlation_id=input.correlation_id,
                raw_response=response,
                errors=errors,
            )
        
        # 5. Validate output packets against contract
        validated_packets, validation_errors = self._validate_output(packets)
        errors.extend(validation_errors)
        
        # 6. Return output bundle
        return LayerOutput(
            packets=validated_packets,
            layer=self.layer_id,
            correlation_id=input.correlation_id,
            raw_response=response,
            errors=errors,
        )
    
    def build_context(self, input: LayerInput) -> str:
        """
        Build LLM context from input packets.
        
        Default implementation creates a structured summary.
        Override for layer-specific context building.
        """
        lines = [
            f"# Layer {self.layer_id.value} Context",
            f"Correlation ID: {input.correlation_id}",
            f"Timestamp: {input.timestamp.isoformat()}",
            "",
            "## Input Packets",
        ]
        
        if not input.packets:
            lines.append("No input packets.")
        else:
            for i, packet in enumerate(input.packets):
                lines.append(f"\n### Packet {i + 1}")
                lines.append(self._format_packet(packet))
        
        if input.context:
            lines.append("\n## Additional Context")
            for key, value in input.context.items():
                lines.append(f"- {key}: {value}")
        
        return "\n".join(lines)
    
    def _filter_input(self, packets: list[Any]) -> list[Any]:
        """Filter packets to only those this layer can receive."""
        filtered = []
        for packet in packets:
            packet_type = self._get_packet_type(packet)
            if packet_type is None:
                continue
            if self.contract.allows_receive(packet_type):
                filtered.append(packet)
        return filtered
    
    def _validate_output(
        self, 
        packets: list[Any]
    ) -> tuple[list[Any], list[str]]:
        """Validate output packets against emission contract."""
        valid = []
        errors = []
        
        for packet in packets:
            packet_type = self._get_packet_type(packet)
            if packet_type is None:
                errors.append(f"Packet missing type: {packet}")
                continue
            
            violation = self.enforcer.check_emit(self.layer_id, packet_type)
            if violation:
                errors.append(violation.message)
            else:
                valid.append(packet)
        
        return valid, errors
    
    def _get_packet_type(self, packet: Any) -> PacketType | None:
        """Extract packet type from a packet."""
        try:
            return packet.header.packet_type
        except AttributeError:
            return None
    
    def _format_packet(self, packet: Any) -> str:
        """Format a packet for LLM context."""
        try:
            # Try model_dump_json for Pydantic models
            if hasattr(packet, 'model_dump_json'):
                return packet.model_dump_json(indent=2)
            # Try model_dump for dict conversion
            elif hasattr(packet, 'model_dump'):
                import json
                return json.dumps(packet.model_dump(), indent=2, default=str)
            return str(packet)
        except Exception:
            return str(packet)


# =============================================================================
# MOCK LLM CLIENT (for testing)
# =============================================================================

class MockLLMClient:
    """
    Mock LLM client for testing.
    
    Returns predefined responses or echoes input.
    """
    
    def __init__(self, responses: list[str] | None = None):
        """
        Initialize mock client.
        
        Args:
            responses: List of responses to return in order.
                      If exhausted, returns echo of user message.
        """
        self.responses = list(responses) if responses else []
        self.calls: list[dict[str, Any]] = []
    
    def complete(
        self,
        system_prompt: str,
        user_message: str,
        **kwargs
    ) -> str:
        """Return next response or echo."""
        self.calls.append({
            "system_prompt": system_prompt,
            "user_message": user_message,
            **kwargs,
        })
        
        if self.responses:
            return self.responses.pop(0)
        return f"Echo: {user_message[:100]}"
    
    @property
    def call_count(self) -> int:
        """Number of calls made."""
        return len(self.calls)
    
    def last_call(self) -> dict[str, Any] | None:
        """Get the last call made."""
        return self.calls[-1] if self.calls else None


def create_mock_client(responses: list[str] | None = None) -> MockLLMClient:
    """Factory for mock LLM client."""
    return MockLLMClient(responses)

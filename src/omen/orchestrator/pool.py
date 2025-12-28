"""
Layer Pool — Manages layer instances for orchestration.

Provides access to configured ACE layers with LLM clients and prompts.

Spec: OMEN.md §6, §11.1
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from omen.vocabulary import LayerSource, PacketType
from omen.layers import (
    Layer,
    LayerInput,
    LayerOutput,
    LLMClient,
    MockLLMClient,
    get_contract,
    LAYER_PROMPTS,
    LAYER_NAMES,
)


# =============================================================================
# CONFIGURABLE LAYER
# =============================================================================

class ConfigurableLayer(Layer):
    """
    A layer configured with a system prompt and optional custom parser.
    
    Uses the Layer base class infrastructure with configurable behavior.
    """
    
    def __init__(
        self,
        layer_id: LayerSource,
        llm_client: LLMClient,
        system_prompt: str,
        response_parser: Callable[[str, LayerInput], list[Any]] | None = None,
        **kwargs
    ):
        """
        Initialize configurable layer.
        
        Args:
            layer_id: Which layer this is
            llm_client: Client for LLM calls
            system_prompt: The system prompt for this layer
            response_parser: Optional custom parser for LLM responses
        """
        super().__init__(layer_id, llm_client, **kwargs)
        self._system_prompt = system_prompt
        self._response_parser = response_parser or self._default_parser
    
    def get_system_prompt(self) -> str:
        """Return the configured system prompt."""
        return self._system_prompt
    
    def parse_response(
        self, 
        response: str, 
        context: LayerInput
    ) -> list[Any]:
        """Parse response using configured parser."""
        return self._response_parser(response, context)
    
    def _default_parser(
        self, 
        response: str, 
        context: LayerInput
    ) -> list[Any]:
        """
        Default parser that extracts JSON objects from response.
        
        Looks for JSON blocks in the response and returns them as dicts.
        Infers packet type from payload fields.
        """
        packets = []
        
        # Try to find JSON blocks (```json ... ``` or raw JSON)
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        matches = re.findall(json_pattern, response)
        
        for match in matches:
            try:
                obj = json.loads(match)
                packet = self._infer_packet_type(obj)
                packets.append(packet)
            except json.JSONDecodeError:
                continue
        
        # If no code blocks, try parsing the whole response as JSON
        if not packets:
            try:
                obj = json.loads(response)
                if isinstance(obj, list):
                    packets.extend([self._infer_packet_type(item) for item in obj])
                else:
                    packets.append(self._infer_packet_type(obj))
            except json.JSONDecodeError:
                # Response isn't JSON, return empty
                pass
        
        return packets
    
    def _infer_packet_type(self, obj: dict) -> dict:
        """
        Infer packet type from payload fields.
        
        LLMs return payload JSON without headers. We infer the type
        from field signatures and add a 'type' field for validation.
        Uses PacketType enum values.
        """
        # Signature-based type inference (order matters - most specific first)
        if "task_id" in obj and "action" in obj:
            obj["type"] = "TaskDirectivePacket"
        elif "task_id" in obj and "status" in obj:
            obj["type"] = "TaskResultPacket"
        elif "decision_outcome" in obj:
            obj["type"] = "DecisionPacket"
        elif "verification_target" in obj:
            obj["type"] = "VerificationPlanPacket"
        elif "observation_type" in obj:
            obj["type"] = "ObservationPacket"
        elif "update_type" in obj:
            obj["type"] = "BeliefUpdatePacket"
        elif "escalation_reason" in obj:
            obj["type"] = "EscalationPacket"
        elif "token_id" in obj and "authorized_actions" in obj:
            obj["type"] = "ToolAuthorizationToken"
        elif "alert_type" in obj:
            obj["type"] = "IntegrityAlertPacket"
        
        # Track source and raw for debugging
        obj["_source"] = self.layer_id.value
        obj["_raw"] = obj.copy()
        
        return obj


# =============================================================================
# LAYER POOL
# =============================================================================

@dataclass
class LayerPool:
    """
    Manages layer instances for the orchestrator.
    
    Provides access to configured layers and handles lifecycle.
    """
    layers: dict[LayerSource, Layer] = field(default_factory=dict)
    
    def get_layer(self, layer_id: LayerSource) -> Layer | None:
        """Get a layer by ID."""
        return self.layers.get(layer_id)
    
    def has_layer(self, layer_id: LayerSource) -> bool:
        """Check if a layer is registered."""
        return layer_id in self.layers
    
    def register_layer(self, layer: Layer) -> None:
        """Register a layer instance."""
        self.layers[layer.layer_id] = layer
    
    def unregister_layer(self, layer_id: LayerSource) -> Layer | None:
        """Unregister and return a layer."""
        return self.layers.pop(layer_id, None)
    
    def get_all_layers(self) -> list[Layer]:
        """Get all registered layers."""
        return list(self.layers.values())
    
    def invoke_layer(
        self,
        layer_id: LayerSource,
        input: LayerInput,
    ) -> LayerOutput | None:
        """
        Invoke a layer with input.
        
        Returns None if layer not found.
        """
        layer = self.get_layer(layer_id)
        if layer is None:
            return None
        return layer.invoke(input)


# =============================================================================
# POOL FACTORY
# =============================================================================

def create_layer_pool(
    llm_client: LLMClient | None = None,
    include_layers: list[LayerSource] | None = None,
    custom_prompts: dict[str, str] | None = None,
    custom_parsers: dict[LayerSource, Callable] | None = None,
) -> LayerPool:
    """
    Factory for creating a configured layer pool.
    
    Args:
        llm_client: LLM client for all layers (defaults to MockLLMClient)
        include_layers: Which layers to include (defaults to L1-L6, no Integrity)
        custom_prompts: Override prompts by layer key (e.g., "LAYER_1")
        custom_parsers: Custom response parsers by LayerSource
    
    Returns:
        Configured LayerPool with layers registered
    """
    client = llm_client or MockLLMClient()
    
    # Default to L1-L6 (not Integrity - that's infrastructure, not LLM)
    if include_layers is None:
        include_layers = [
            LayerSource.LAYER_1,
            LayerSource.LAYER_2,
            LayerSource.LAYER_3,
            LayerSource.LAYER_4,
            LayerSource.LAYER_5,
            LayerSource.LAYER_6,
        ]
    
    custom_prompts = custom_prompts or {}
    custom_parsers = custom_parsers or {}
    
    pool = LayerPool()
    
    for layer_id in include_layers:
        # Skip Integrity - it's not an LLM layer
        if layer_id == LayerSource.INTEGRITY:
            continue
        
        # Get prompt (custom or default)
        prompt_key = f"LAYER_{layer_id.value}"
        prompt = custom_prompts.get(prompt_key) or LAYER_PROMPTS.get(prompt_key, "")
        
        if not prompt:
            continue  # Skip if no prompt available
        
        # Get parser (custom or default)
        parser = custom_parsers.get(layer_id)
        
        # Create and register layer
        layer = ConfigurableLayer(
            layer_id=layer_id,
            llm_client=client,
            system_prompt=prompt,
            response_parser=parser,
        )
        pool.register_layer(layer)
    
    return pool


def create_mock_layer_pool(
    responses: dict[LayerSource, list[str]] | None = None,
) -> LayerPool:
    """
    Create a layer pool with mock LLM responses for testing.
    
    Args:
        responses: Dict of layer_id -> list of responses to return
    
    Returns:
        LayerPool with MockLLMClient per layer
    """
    responses = responses or {}
    pool = LayerPool()
    
    for layer_id in [
        LayerSource.LAYER_1,
        LayerSource.LAYER_2,
        LayerSource.LAYER_3,
        LayerSource.LAYER_4,
        LayerSource.LAYER_5,
        LayerSource.LAYER_6,
    ]:
        # Create per-layer mock client with specific responses
        layer_responses = responses.get(layer_id, [])
        client = MockLLMClient(responses=layer_responses)
        
        prompt_key = f"LAYER_{layer_id.value}"
        prompt = LAYER_PROMPTS.get(prompt_key, "")
        
        if prompt:
            layer = ConfigurableLayer(
                layer_id=layer_id,
                llm_client=client,
                system_prompt=prompt,
            )
            pool.register_layer(layer)
    
    return pool

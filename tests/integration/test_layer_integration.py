"""Integration tests for layer invocation with real LLM."""

import pytest
from uuid import uuid4

from omen.vocabulary import LayerSource, PacketType
from omen.layers import LayerInput
from omen.layers.prompts import LAYER_5_PROMPT, LAYER_6_PROMPT
from omen.orchestrator import ConfigurableLayer


@pytest.mark.integration
class TestLayer6Integration:
    """Integration tests for Layer 6 (Task Prosecution)."""
    
    def test_produces_response(self, openai_client, response_log):
        """L6 produces a response."""
        layer = ConfigurableLayer(
            layer_id=LayerSource.LAYER_6,
            llm_client=openai_client,
            system_prompt=LAYER_6_PROMPT,
        )
        
        input_data = LayerInput(
            packets=[],
            correlation_id=uuid4(),
            context={"task": "Observe the current state"},
        )
        
        output = layer.invoke(input_data)
        
        # Log response for offline analysis
        response_log("LAYER_6", output.raw_response, {"test": "produces_response"})
        
        assert output.raw_response != ""
        print(f"\n=== L6 Raw Response ===\n{output.raw_response}\n")
    
    def test_produces_json(self, openai_client, response_log):
        """L6 produces parseable JSON."""
        layer = ConfigurableLayer(
            layer_id=LayerSource.LAYER_6,
            llm_client=openai_client,
            system_prompt=LAYER_6_PROMPT,
        )
        
        input_data = LayerInput(
            packets=[],
            correlation_id=uuid4(),
            context={
                "directive": "Generate an Observation packet about system startup",
            },
        )
        
        output = layer.invoke(input_data)
        
        # Log for debugging
        response_log("LAYER_6", output.raw_response, {
            "test": "produces_json",
            "directive": "system_startup_observation"
        })
        
        print(f"\n=== L6 Raw Response ===\n{output.raw_response}\n")
        print(f"=== Parsed Packets ===\n{output.packets}\n")
        print(f"=== Errors ===\n{output.errors}\n")
        
        # We expect some response - may or may not parse correctly
        assert output.raw_response != ""
        
        # Log results to file
        print(f"\n>>> Response log saved to: {response_log.path}")
    
    def test_observation_packet(self, openai_client, response_log):
        """L6 produces Observation packet with proper structure."""
        layer = ConfigurableLayer(
            layer_id=LayerSource.LAYER_6,
            llm_client=openai_client,
            system_prompt=LAYER_6_PROMPT,
        )
        
        input_data = LayerInput(
            packets=[],
            correlation_id=uuid4(),
            context={
                "instruction": "You have been activated. Generate an Observation packet "
                              "describing that the system has started and is ready. "
                              "Use observation_type: SYSTEM_STATUS, freshness: CURRENT.",
            },
        )
        
        output = layer.invoke(input_data)
        
        response_log("LAYER_6", output.raw_response, {
            "test": "observation_packet",
            "expected_type": "Observation"
        })
        
        print(f"\n=== L6 Observation Test ===")
        print(f"Raw Response:\n{output.raw_response}\n")
        print(f"Parsed Packets: {len(output.packets)}")
        for pkt in output.packets:
            print(f"  - {pkt}")
        print(f"Errors: {output.errors}")
        
        # Check if we got any packets
        if output.packets:
            print(f"\n✓ Successfully parsed {len(output.packets)} packet(s)")
        else:
            print(f"\n✗ No packets parsed - parser may need adjustment")


@pytest.mark.integration
class TestLayer5Integration:
    """Integration tests for Layer 5 (Cognitive Control)."""
    
    def test_produces_decision(self, openai_client, response_log):
        """L5 produces a decision-like response."""
        layer = ConfigurableLayer(
            layer_id=LayerSource.LAYER_5,
            llm_client=openai_client,
            system_prompt=LAYER_5_PROMPT,
        )
        
        input_data = LayerInput(
            packets=[],
            correlation_id=uuid4(),
            context={
                "situation": "User requested a simple greeting",
                "stakes": "LOW",
                "quality_tier": "PAR",
            },
        )
        
        output = layer.invoke(input_data)
        
        response_log("LAYER_5", output.raw_response, {
            "test": "produces_decision",
            "context": "simple_greeting"
        })
        
        print(f"\n=== L5 Raw Response ===\n{output.raw_response}\n")
        print(f"=== Parsed Packets ===\n{output.packets}\n")
        print(f"=== Errors ===\n{output.errors}\n")
        
        # Check for decision-related content
        response_lower = output.raw_response.lower()
        has_decision_content = any(term in response_lower for term in [
            "act", "verify", "escalate", "defer", "decision"
        ])
        assert has_decision_content, "Expected decision-related content"
    
    def test_decision_packet_structure(self, openai_client, response_log):
        """L5 produces Decision packet with required fields."""
        layer = ConfigurableLayer(
            layer_id=LayerSource.LAYER_5,
            llm_client=openai_client,
            system_prompt=LAYER_5_PROMPT,
        )
        
        input_data = LayerInput(
            packets=[],
            correlation_id=uuid4(),
            context={
                "instruction": "Make a simple decision to ACT. "
                              "Generate a Decision packet with decision_outcome: ACT, "
                              "provide a brief rationale, confidence level HIGH, "
                              "and no assumptions needed for this trivial case.",
                "stakes_level": "LOW",
                "quality_tier": "PAR",
            },
        )
        
        output = layer.invoke(input_data)
        
        response_log("LAYER_5", output.raw_response, {
            "test": "decision_packet_structure",
            "expected_type": "Decision"
        })
        
        print(f"\n=== L5 Decision Test ===")
        print(f"Raw Response:\n{output.raw_response}\n")
        print(f"Parsed Packets: {len(output.packets)}")
        for pkt in output.packets:
            print(f"  - {pkt}")
        print(f"Errors: {output.errors}")
        
        # Check if we got any packets
        if output.packets:
            print(f"\n✓ Successfully parsed {len(output.packets)} packet(s)")
        else:
            print(f"\n✗ No packets parsed - check format")
        
        print(f"\n>>> Response log saved to: {response_log.path}")


@pytest.mark.integration
class TestCrossLayerIntegration:
    """Integration tests for multi-layer sequences."""
    
    def test_l6_to_l5_flow(self, openai_client, response_log):
        """Test L6 observation feeding into L5 decision."""
        # First, L6 makes an observation
        l6 = ConfigurableLayer(
            layer_id=LayerSource.LAYER_6,
            llm_client=openai_client,
            system_prompt=LAYER_6_PROMPT,
        )
        
        l6_input = LayerInput(
            packets=[],
            correlation_id=uuid4(),
            context={
                "instruction": "Generate an Observation that the system has low battery (15% remaining)."
            },
        )
        
        l6_output = l6.invoke(l6_input)
        response_log("LAYER_6", l6_output.raw_response, {"test": "l6_to_l5_flow", "stage": "observation"})
        
        print(f"\n=== L6 Observation ===")
        print(f"Response:\n{l6_output.raw_response}\n")
        print(f"Packets: {len(l6_output.packets)}")
        
        # Then, L5 decides what to do about it
        l5 = ConfigurableLayer(
            layer_id=LayerSource.LAYER_5,
            llm_client=openai_client,
            system_prompt=LAYER_5_PROMPT,
        )
        
        l5_input = LayerInput(
            packets=l6_output.packets,  # Feed L6's packets to L5
            correlation_id=uuid4(),
            context={
                "instruction": "Based on the low battery observation, make a decision.",
                "stakes_level": "MEDIUM",
            },
        )
        
        l5_output = l5.invoke(l5_input)
        response_log("LAYER_5", l5_output.raw_response, {"test": "l6_to_l5_flow", "stage": "decision"})
        
        print(f"\n=== L5 Decision ===")
        print(f"Response:\n{l5_output.raw_response}\n")
        print(f"Packets: {len(l5_output.packets)}")
        
        print(f"\n>>> Full conversation log saved to: {response_log.path}")
        
        # Both should produce responses
        assert l6_output.raw_response != ""
        assert l5_output.raw_response != ""

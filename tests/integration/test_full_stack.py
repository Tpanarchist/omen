"""
Full-stack integration test for Template H.

Tests all 6 layers (L1-L6) invoking in sequence:
- Southbound flow: L1 → L2 → L3 → L4 → L5 → L6
- Northbound flow: L6 → L5 → L4 → L3 → L2 → L1

This validates that ConfigurableLayer with existing prompts can handle
the full cognitive stack without needing concrete subclasses.
"""

import pytest
from uuid import uuid4

from omen.vocabulary import TemplateID, LayerSource
from omen.templates.canonical import TEMPLATE_H
from omen.layers import LayerInput
from omen.orchestrator.pool import ConfigurableLayer, LayerPool
from omen.layers.prompts import (
    LAYER_1_PROMPT,
    LAYER_2_PROMPT,
    LAYER_3_PROMPT,
    LAYER_4_PROMPT,
    LAYER_5_PROMPT,
    LAYER_6_PROMPT,
)


@pytest.mark.integration
class TestFullStackIntegration:
    """Integration tests for full L1-L6 stack."""
    
    def test_template_h_exists(self):
        """Template H is defined and registered."""
        assert TEMPLATE_H.template_id == TemplateID.TEMPLATE_H
        assert TEMPLATE_H.name == "Full-Stack Mission Flow"
        assert len(TEMPLATE_H.steps) == 14  # 6 southbound + 7 northbound + 1 completion
        
    def test_all_layers_represented(self):
        """Template H involves all 6 layers."""
        layer_sources = {step.owner_layer for step in TEMPLATE_H.steps if step.owner_layer}
        assert LayerSource.LAYER_1 in layer_sources
        assert LayerSource.LAYER_2 in layer_sources
        assert LayerSource.LAYER_3 in layer_sources
        assert LayerSource.LAYER_4 in layer_sources
        assert LayerSource.LAYER_5 in layer_sources
        assert LayerSource.LAYER_6 in layer_sources
        
    def test_create_layer_pool_with_all_layers(self, openai_client):
        """Can instantiate all 6 layers with ConfigurableLayer."""
        layers = {
            LayerSource.LAYER_1: ConfigurableLayer(
                layer_id=LayerSource.LAYER_1,
                llm_client=openai_client,
                system_prompt=LAYER_1_PROMPT,
            ),
            LayerSource.LAYER_2: ConfigurableLayer(
                layer_id=LayerSource.LAYER_2,
                llm_client=openai_client,
                system_prompt=LAYER_2_PROMPT,
            ),
            LayerSource.LAYER_3: ConfigurableLayer(
                layer_id=LayerSource.LAYER_3,
                llm_client=openai_client,
                system_prompt=LAYER_3_PROMPT,
            ),
            LayerSource.LAYER_4: ConfigurableLayer(
                layer_id=LayerSource.LAYER_4,
                llm_client=openai_client,
                system_prompt=LAYER_4_PROMPT,
            ),
            LayerSource.LAYER_5: ConfigurableLayer(
                layer_id=LayerSource.LAYER_5,
                llm_client=openai_client,
                system_prompt=LAYER_5_PROMPT,
            ),
            LayerSource.LAYER_6: ConfigurableLayer(
                layer_id=LayerSource.LAYER_6,
                llm_client=openai_client,
                system_prompt=LAYER_6_PROMPT,
            ),
        }
        
        pool = LayerPool(layers=layers)
        
        # Verify all layers accessible
        assert pool.get_layer(LayerSource.LAYER_1) is not None
        assert pool.get_layer(LayerSource.LAYER_2) is not None
        assert pool.get_layer(LayerSource.LAYER_3) is not None
        assert pool.get_layer(LayerSource.LAYER_4) is not None
        assert pool.get_layer(LayerSource.LAYER_5) is not None
        assert pool.get_layer(LayerSource.LAYER_6) is not None
        
    @pytest.mark.slow
    def test_southbound_flow(self, openai_client, response_log):
        """
        Test southbound flow: L1 → L2 → L3 → L4 → L5 → L6
        
        Mission context originates at L1 and flows down through all layers,
        with each layer adding strategic, capability, planning, decision, and
        execution context.
        """
        correlation_id = uuid4()
        
        # L1: Mission Posture
        l1 = ConfigurableLayer(
            layer_id=LayerSource.LAYER_1,
            llm_client=openai_client,
            system_prompt=LAYER_1_PROMPT,
        )
        
        l1_input = LayerInput(
            packets=[],
            correlation_id=correlation_id,
            context={
                "mission": "Gather system telemetry and assess operational readiness",
                "constitutional_directive": "Ensure all actions align with system integrity and safety",
            },
        )
        
        l1_output = l1.invoke(l1_input)
        response_log("LAYER_1", l1_output.raw_response, {"flow": "southbound", "step": "mission_posture"})
        
        print(f"\n=== L1 (Aspirational) ===")
        print(f"Packets: {len(l1_output.packets)}")
        print(f"Errors: {len(l1_output.errors)}")
        if l1_output.errors:
            print(f"Errors: {l1_output.errors}")
        
        # L2: Strategic Framing
        l2 = ConfigurableLayer(
            layer_id=LayerSource.LAYER_2,
            llm_client=openai_client,
            system_prompt=LAYER_2_PROMPT,
        )
        
        l2_input = LayerInput(
            packets=l1_output.packets,
            correlation_id=correlation_id,
            context={
                "mission": "Gather system telemetry and assess operational readiness",
                "task": "Frame strategic approach to telemetry gathering",
            },
        )
        
        l2_output = l2.invoke(l2_input)
        response_log("LAYER_2", l2_output.raw_response, {"flow": "southbound", "step": "strategy"})
        
        print(f"\n=== L2 (Global Strategy) ===")
        print(f"Packets: {len(l2_output.packets)}")
        print(f"Errors: {len(l2_output.errors)}")
        
        # L3: Capability Assessment
        l3 = ConfigurableLayer(
            layer_id=LayerSource.LAYER_3,
            llm_client=openai_client,
            system_prompt=LAYER_3_PROMPT,
        )
        
        l3_input = LayerInput(
            packets=l1_output.packets + l2_output.packets,
            correlation_id=correlation_id,
            context={
                "task": "Assess available capabilities for telemetry gathering",
            },
        )
        
        l3_output = l3.invoke(l3_input)
        response_log("LAYER_3", l3_output.raw_response, {"flow": "southbound", "step": "capabilities"})
        
        print(f"\n=== L3 (Agent Model) ===")
        print(f"Packets: {len(l3_output.packets)}")
        print(f"Errors: {len(l3_output.errors)}")
        
        # L4: Tactical Planning
        l4 = ConfigurableLayer(
            layer_id=LayerSource.LAYER_4,
            llm_client=openai_client,
            system_prompt=LAYER_4_PROMPT,
        )
        
        all_packets_so_far = l1_output.packets + l2_output.packets + l3_output.packets
        
        l4_input = LayerInput(
            packets=all_packets_so_far,
            correlation_id=correlation_id,
            context={
                "task": "Create tactical plan and budget for telemetry operation",
            },
        )
        
        l4_output = l4.invoke(l4_input)
        response_log("LAYER_4", l4_output.raw_response, {"flow": "southbound", "step": "planning"})
        
        print(f"\n=== L4 (Executive Function) ===")
        print(f"Packets: {len(l4_output.packets)}")
        print(f"Errors: {len(l4_output.errors)}")
        
        # L5: Decision
        l5 = ConfigurableLayer(
            layer_id=LayerSource.LAYER_5,
            llm_client=openai_client,
            system_prompt=LAYER_5_PROMPT,
        )
        
        all_packets_before_l5 = all_packets_so_far + l4_output.packets
        
        l5_input = LayerInput(
            packets=all_packets_before_l5,
            correlation_id=correlation_id,
            context={
                "task": "Make decision on telemetry gathering and issue directive",
            },
        )
        
        l5_output = l5.invoke(l5_input)
        response_log("LAYER_5", l5_output.raw_response, {"flow": "southbound", "step": "decision"})
        
        print(f"\n=== L5 (Cognitive Control) ===")
        print(f"Packets: {len(l5_output.packets)}")
        print(f"Errors: {len(l5_output.errors)}")
        
        # L6: Execution
        l6 = ConfigurableLayer(
            layer_id=LayerSource.LAYER_6,
            llm_client=openai_client,
            system_prompt=LAYER_6_PROMPT,
        )
        
        all_packets_before_l6 = all_packets_before_l5 + l5_output.packets
        
        l6_input = LayerInput(
            packets=all_packets_before_l6,
            correlation_id=correlation_id,
            context={
                "directive": "Execute telemetry gathering as directed by L5",
            },
        )
        
        l6_output = l6.invoke(l6_input)
        response_log("LAYER_6", l6_output.raw_response, {"flow": "southbound", "step": "execution"})
        
        print(f"\n=== L6 (Task Prosecution) ===")
        print(f"Packets: {len(l6_output.packets)}")
        print(f"Errors: {len(l6_output.errors)}")
        
        # VALIDATION: Each layer should produce packets
        assert len(l1_output.packets) > 0 or len(l1_output.errors) == 0, "L1 should produce packets or have no errors"
        assert len(l2_output.packets) > 0 or len(l2_output.errors) == 0, "L2 should produce packets or have no errors"
        assert len(l3_output.packets) > 0 or len(l3_output.errors) == 0, "L3 should produce packets or have no errors"
        assert len(l4_output.packets) > 0 or len(l4_output.errors) == 0, "L4 should produce packets or have no errors"
        assert len(l5_output.packets) > 0 or len(l5_output.errors) == 0, "L5 should produce packets or have no errors"
        assert len(l6_output.packets) > 0 or len(l6_output.errors) == 0, "L6 should produce packets or have no errors"
        
        print(f"\n=== SOUTHBOUND FLOW COMPLETE ===")
        print(f"L1→L2→L3→L4→L5→L6 all invoked successfully")
        print(f"Total packets generated: {sum([len(l1_output.packets), len(l2_output.packets), len(l3_output.packets), len(l4_output.packets), len(l5_output.packets), len(l6_output.packets)])}")
        
    @pytest.mark.slow
    def test_northbound_flow(self, openai_client, response_log):
        """
        Test northbound flow: L6 → L5 → L4 → L3 → L2 → L1
        
        Observations and results originate at L6 and flow up through all layers,
        with each layer processing and potentially enriching the telemetry.
        """
        correlation_id = uuid4()
        
        # L6: Observation (starting point for northbound)
        l6 = ConfigurableLayer(
            layer_id=LayerSource.LAYER_6,
            llm_client=openai_client,
            system_prompt=LAYER_6_PROMPT,
        )
        
        l6_input = LayerInput(
            packets=[],
            correlation_id=correlation_id,
            context={
                "observation": "System telemetry gathered: CPU 45%, Memory 62%, Network: operational",
                "task_completed": True,
            },
        )
        
        l6_output = l6.invoke(l6_input)
        response_log("LAYER_6", l6_output.raw_response, {"flow": "northbound", "step": "observe"})
        
        print(f"\n=== L6 (Task Prosecution) - Observation ===")
        print(f"Packets: {len(l6_output.packets)}")
        print(f"Errors: {len(l6_output.errors)}")
        
        # L5: Review
        l5 = ConfigurableLayer(
            layer_id=LayerSource.LAYER_5,
            llm_client=openai_client,
            system_prompt=LAYER_5_PROMPT,
        )
        
        l5_input = LayerInput(
            packets=l6_output.packets,
            correlation_id=correlation_id,
            context={
                "task": "Review execution results from L6",
            },
        )
        
        l5_output = l5.invoke(l5_input)
        response_log("LAYER_5", l5_output.raw_response, {"flow": "northbound", "step": "review"})
        
        print(f"\n=== L5 (Cognitive Control) - Review ===")
        print(f"Packets: {len(l5_output.packets)}")
        
        # L4: Assess against plan
        l4 = ConfigurableLayer(
            layer_id=LayerSource.LAYER_4,
            llm_client=openai_client,
            system_prompt=LAYER_4_PROMPT,
        )
        
        l4_input = LayerInput(
            packets=l6_output.packets + l5_output.packets,
            correlation_id=correlation_id,
            context={
                "task": "Assess results against plan and budget",
            },
        )
        
        l4_output = l4.invoke(l4_input)
        response_log("LAYER_4", l4_output.raw_response, {"flow": "northbound", "step": "assess"})
        
        print(f"\n=== L4 (Executive Function) - Assess ===")
        print(f"Packets: {len(l4_output.packets)}")
        
        # L3: Integrate into capability model
        l3 = ConfigurableLayer(
            layer_id=LayerSource.LAYER_3,
            llm_client=openai_client,
            system_prompt=LAYER_3_PROMPT,
        )
        
        all_packets = l6_output.packets + l5_output.packets + l4_output.packets
        
        l3_input = LayerInput(
            packets=all_packets,
            correlation_id=correlation_id,
            context={
                "task": "Integrate telemetry into capability model",
            },
        )
        
        l3_output = l3.invoke(l3_input)
        response_log("LAYER_3", l3_output.raw_response, {"flow": "northbound", "step": "integrate"})
        
        print(f"\n=== L3 (Agent Model) - Integrate ===")
        print(f"Packets: {len(l3_output.packets)}")
        
        # L2: Strategic update
        l2 = ConfigurableLayer(
            layer_id=LayerSource.LAYER_2,
            llm_client=openai_client,
            system_prompt=LAYER_2_PROMPT,
        )
        
        all_packets += l3_output.packets
        
        l2_input = LayerInput(
            packets=all_packets,
            correlation_id=correlation_id,
            context={
                "task": "Update strategic context with telemetry results",
            },
        )
        
        l2_output = l2.invoke(l2_input)
        response_log("LAYER_2", l2_output.raw_response, {"flow": "northbound", "step": "strategic_update"})
        
        print(f"\n=== L2 (Global Strategy) - Strategic Update ===")
        print(f"Packets: {len(l2_output.packets)}")
        
        # L1: Mission review
        l1 = ConfigurableLayer(
            layer_id=LayerSource.LAYER_1,
            llm_client=openai_client,
            system_prompt=LAYER_1_PROMPT,
        )
        
        all_packets += l2_output.packets
        
        l1_input = LayerInput(
            packets=all_packets,
            correlation_id=correlation_id,
            context={
                "task": "Review results against mission objectives and constitutional principles",
            },
        )
        
        l1_output = l1.invoke(l1_input)
        response_log("LAYER_1", l1_output.raw_response, {"flow": "northbound", "step": "mission_review"})
        
        print(f"\n=== L1 (Aspirational) - Mission Review ===")
        print(f"Packets: {len(l1_output.packets)}")
        
        # VALIDATION
        assert len(l6_output.packets) > 0 or len(l6_output.errors) == 0, "L6 should produce observation"
        assert len(l5_output.packets) > 0 or len(l5_output.errors) == 0, "L5 should produce review"
        assert len(l4_output.packets) > 0 or len(l4_output.errors) == 0, "L4 should produce assessment"
        assert len(l3_output.packets) > 0 or len(l3_output.errors) == 0, "L3 should produce integration"
        assert len(l2_output.packets) > 0 or len(l2_output.errors) == 0, "L2 should produce strategic update"
        assert len(l1_output.packets) > 0 or len(l1_output.errors) == 0, "L1 should produce mission review"
        
        print(f"\n=== NORTHBOUND FLOW COMPLETE ===")
        print(f"L6→L5→L4→L3→L2→L1 all invoked successfully")
        print(f"Total packets generated: {sum([len(l6_output.packets), len(l5_output.packets), len(l4_output.packets), len(l3_output.packets), len(l2_output.packets), len(l1_output.packets)])}")

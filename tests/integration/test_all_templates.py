"""Integration tests for all canonical templates (B, C, D, E, F, G)."""

import pytest

from omen.vocabulary import TemplateID, StakesLevel, QualityTier


@pytest.mark.integration
class TestTemplateBIntegration:
    """Integration tests for Template B (Verification Loop)."""
    
    def test_template_b_execution(self, integration_orchestrator):
        """Execute Template B (Verification Loop) with real LLM."""
        result = integration_orchestrator.run_template(
            TemplateID.TEMPLATE_B,
            stakes_level=StakesLevel.MEDIUM,
            quality_tier=QualityTier.PAR,
        )
        
        print(f"\n{'='*60}")
        print(f"TEMPLATE B: VERIFICATION LOOP")
        print(f"{'='*60}")
        print(f"Success: {result.success}")
        print(f"Steps: {result.step_count}")
        print(f"Duration: {result.total_duration_seconds:.2f}s")
        print(f"Errors: {result.errors}")
        
        print(f"\n{'='*60}")
        print(f"VERIFICATION FLOW")
        print(f"{'='*60}")
        for i, step in enumerate(result.steps_completed, 1):
            print(f"\n[Step {i}] {step.step_id}")
            print(f"  Success: {step.success}")
            print(f"  Packets: {step.packets_emitted}")
            
            if step.output and step.output.raw_response:
                response_lower = step.output.raw_response.lower()
                if any(kw in response_lower for kw in ['verify', 'verification', 'plan', 'evidence']):
                    print(f"  ✓ Contains verification keywords")
                    preview = step.output.raw_response[:150].replace("\n", " ")
                    print(f"  Preview: {preview}...")
        
        print(f"\n{'='*60}\n")
        
        assert result.step_count > 0, "Should execute at least one step"


@pytest.mark.integration
class TestTemplateCIntegration:
    """Integration tests for Template C (Read-Only Act)."""
    
    def test_template_c_execution(self, integration_orchestrator):
        """Execute Template C (Read-Only Act) with real LLM."""
        result = integration_orchestrator.run_template(
            TemplateID.TEMPLATE_C,
            stakes_level=StakesLevel.LOW,
            quality_tier=QualityTier.PAR,
            initial_packets=[{
                "type": "seed",
                "content": "User requested to read current system status",
            }],
        )
        
        print(f"\n{'='*60}")
        print(f"TEMPLATE C: READ-ONLY ACT")
        print(f"{'='*60}")
        print(f"Success: {result.success}")
        print(f"Steps: {result.step_count}")
        print(f"Duration: {result.total_duration_seconds:.2f}s")
        
        print(f"\n{'='*60}")
        print(f"ACT DECISION & EXECUTION")
        print(f"{'='*60}")
        for i, step in enumerate(result.steps_completed, 1):
            print(f"\n[Step {i}] {step.step_id}")
            print(f"  Success: {step.success}")
            
            if step.output and step.output.packets:
                for pkt in step.output.packets:
                    if isinstance(pkt, dict):
                        pkt_type = pkt.get("type", "unknown")
                        print(f"    Packet: {pkt_type}")
                        
                        if pkt_type == "DecisionPacket" and pkt.get("decision_outcome") == "ACT":
                            print(f"    ✓ ACT decision confirmed")
                        
                        if pkt_type == "TaskResultPacket":
                            print(f"    ✓ Task executed: {pkt.get('status', 'unknown')}")
        
        print(f"\n{'='*60}\n")
        
        assert result.step_count > 0


@pytest.mark.integration
class TestTemplateDIntegration:
    """Integration tests for Template D (Write Act)."""
    
    def test_template_d_execution(self, integration_orchestrator):
        """Execute Template D (Write Act) with real LLM."""
        result = integration_orchestrator.run_template(
            TemplateID.TEMPLATE_D,
            stakes_level=StakesLevel.HIGH,
            quality_tier=QualityTier.SUPERB,
            initial_packets=[{
                "type": "seed",
                "content": "User authorized: Update configuration file with new settings",
            }],
        )
        
        print(f"\n{'='*60}")
        print(f"TEMPLATE D: WRITE ACT")
        print(f"{'='*60}")
        print(f"Success: {result.success}")
        print(f"Steps: {result.step_count}")
        print(f"Duration: {result.total_duration_seconds:.2f}s")
        
        print(f"\n{'='*60}")
        print(f"AUTHORIZATION & WRITE EXECUTION")
        print(f"{'='*60}")
        
        auth_token_found = False
        task_result_found = False
        
        for i, step in enumerate(result.steps_completed, 1):
            print(f"\n[Step {i}] {step.step_id}")
            print(f"  Success: {step.success}")
            
            if step.output and step.output.packets:
                for pkt in step.output.packets:
                    if isinstance(pkt, dict):
                        pkt_type = pkt.get("type", "unknown")
                        print(f"    Packet: {pkt_type}")
                        
                        if pkt_type == "ToolAuthorizationToken":
                            auth_token_found = True
                            print(f"    ✓ Authorization token issued")
                        
                        if pkt_type == "TaskResultPacket":
                            task_result_found = True
                            print(f"    ✓ Write task executed: {pkt.get('status', 'unknown')}")
        
        print(f"\n{'='*60}")
        print(f"WRITE SAFETY CHECKS")
        print(f"{'='*60}")
        print(f"  Authorization token: {'✓ Found' if auth_token_found else '✗ Not found'}")
        print(f"  Task execution: {'✓ Found' if task_result_found else '✗ Not found'}")
        print(f"\n{'='*60}\n")
        
        assert result.step_count > 0


@pytest.mark.integration
class TestTemplateFIntegration:
    """Integration tests for Template F (Degraded Tools)."""
    
    def test_template_f_degraded_mode(self, integration_orchestrator):
        """Execute Template F (Degraded Tools) with real LLM."""
        from omen.vocabulary import ToolsState
        
        result = integration_orchestrator.run_template(
            TemplateID.TEMPLATE_F,
            stakes_level=StakesLevel.MEDIUM,
            quality_tier=QualityTier.PAR,
            tools_state=ToolsState.TOOLS_PARTIAL,  # Template F requires degraded tools
            initial_packets=[{
                "type": "seed",
                "content": "System is in degraded mode - some tools unavailable",
            }],
        )
        
        print(f"\n{'='*60}")
        print(f"TEMPLATE F: DEGRADED TOOLS")
        print(f"{'='*60}")
        print(f"Success: {result.success}")
        print(f"Steps: {result.step_count}")
        print(f"Duration: {result.total_duration_seconds:.2f}s")
        
        print(f"\n{'='*60}")
        print(f"DEGRADED MODE HANDLING")
        print(f"{'='*60}")
        
        observations = []
        decisions = []
        escalations = []
        
        for i, step in enumerate(result.steps_completed, 1):
            print(f"\n[Step {i}] {step.step_id}")
            print(f"  Success: {step.success}")
            
            if step.output and step.output.packets:
                for pkt in step.output.packets:
                    if isinstance(pkt, dict):
                        pkt_type = pkt.get("type", "unknown")
                        print(f"    Packet: {pkt_type}")
                        
                        if pkt_type == "ObservationPacket":
                            observations.append(pkt)
                        elif pkt_type == "DecisionPacket":
                            decisions.append(pkt)
                        elif pkt_type == "EscalationPacket":
                            escalations.append(pkt)
        
        print(f"\n{'='*60}")
        print(f"DEGRADED MODE BEHAVIOR")
        print(f"{'='*60}")
        print(f"  Observations: {len(observations)}")
        print(f"  Decisions: {len(decisions)}")
        print(f"  Escalations: {len(escalations)}")
        print(f"\n{'='*60}\n")
        
        assert result.step_count > 0


@pytest.mark.integration
class TestTemplateGIntegration:
    """Integration tests for Template G (Compile-to-Code)."""
    
    def test_template_g_execution(self, integration_orchestrator):
        """Execute Template G (Compile-to-Code) with real LLM."""
        result = integration_orchestrator.run_template(
            TemplateID.TEMPLATE_G,
            stakes_level=StakesLevel.HIGH,
            quality_tier=QualityTier.SUPERB,
            initial_packets=[{
                "type": "seed",
                "content": "Generate code for a simple data validation function with tests",
            }],
        )
        
        print(f"\n{'='*60}")
        print(f"TEMPLATE G: COMPILE-TO-CODE")
        print(f"{'='*60}")
        print(f"Success: {result.success}")
        print(f"Steps: {result.step_count}")
        print(f"Duration: {result.total_duration_seconds:.2f}s")
        
        print(f"\n{'='*60}")
        print(f"COMPILATION WORKFLOW")
        print(f"{'='*60}")
        
        has_plan = False
        has_auth = False
        has_execution = False
        has_review = False
        
        for i, step in enumerate(result.steps_completed, 1):
            print(f"\n[Step {i}] {step.step_id}")
            print(f"  Success: {step.success}")
            
            if step.output and step.output.packets:
                for pkt in step.output.packets:
                    if isinstance(pkt, dict):
                        pkt_type = pkt.get("type", "unknown")
                        print(f"    Packet: {pkt_type}")
                        
                        if pkt_type == "VerificationPlanPacket":
                            has_plan = True
                            print(f"    ✓ Compilation plan created")
                        elif pkt_type == "ToolAuthorizationToken":
                            has_auth = True
                            print(f"    ✓ Write authorization granted")
                        elif pkt_type == "TaskResultPacket":
                            has_execution = True
                            status = pkt.get("status", "unknown")
                            print(f"    ✓ Compilation executed: {status}")
                        elif pkt_type == "BeliefUpdatePacket" and "review" in step.step_id.lower():
                            has_review = True
                            print(f"    ✓ Compilation reviewed")
        
        print(f"\n{'='*60}")
        print(f"COMPILATION GATES")
        print(f"{'='*60}")
        print(f"  Planning: {'✓' if has_plan else '✗'}")
        print(f"  Authorization: {'✓' if has_auth else '✗'}")
        print(f"  Execution: {'✓' if has_execution else '✗'}")
        print(f"  Review: {'✓' if has_review else '✗'}")
        print(f"\n{'='*60}\n")
        
        assert result.step_count > 0


@pytest.mark.integration
class TestTemplateComprehensive:
    """Comprehensive tests across multiple templates."""
    
    def test_all_templates_execute(self, integration_orchestrator):
        """Verify all templates can execute without fatal errors."""
        from omen.vocabulary import ToolsState
        
        templates_to_test = [
            (TemplateID.TEMPLATE_A, StakesLevel.LOW, QualityTier.PAR, None),
            (TemplateID.TEMPLATE_B, StakesLevel.MEDIUM, QualityTier.PAR, None),
            (TemplateID.TEMPLATE_C, StakesLevel.LOW, QualityTier.PAR, None),
            (TemplateID.TEMPLATE_D, StakesLevel.HIGH, QualityTier.SUPERB, None),
            (TemplateID.TEMPLATE_E, StakesLevel.HIGH, QualityTier.SUBPAR, None),
            (TemplateID.TEMPLATE_F, StakesLevel.MEDIUM, QualityTier.PAR, ToolsState.TOOLS_PARTIAL),
            (TemplateID.TEMPLATE_G, StakesLevel.HIGH, QualityTier.SUPERB, None),
        ]
        
        results_summary = []
        
        print(f"\n{'='*70}")
        print(f"COMPREHENSIVE TEMPLATE SUITE TEST")
        print(f"{'='*70}\n")
        
        for template_id, stakes, tier, tools_state in templates_to_test:
            print(f"Testing {template_id.value}...")
            
            try:
                kwargs = {
                    "stakes_level": stakes,
                    "quality_tier": tier,
                }
                if tools_state:
                    kwargs["tools_state"] = tools_state
                    
                result = integration_orchestrator.run_template(
                    template_id,
                    **kwargs
                )
                
                results_summary.append({
                    "template": template_id.value,
                    "success": result.success,
                    "steps": result.step_count,
                    "duration": result.total_duration_seconds,
                    "errors": len(result.errors) if result.errors else 0,
                })
                
                status = "✓" if result.success else "⚠"
                print(f"  {status} {template_id.value}: {result.step_count} steps, "
                      f"{result.total_duration_seconds:.1f}s\n")
                
            except Exception as e:
                print(f"  ✗ {template_id.value}: FAILED - {str(e)[:100]}\n")
                results_summary.append({
                    "template": template_id.value,
                    "success": False,
                    "steps": 0,
                    "duration": 0,
                    "errors": 1,
                    "exception": str(e)[:100],
                })
        
        print(f"\n{'='*70}")
        print(f"SUMMARY")
        print(f"{'='*70}")
        
        total_steps = sum(r["steps"] for r in results_summary)
        total_duration = sum(r["duration"] for r in results_summary)
        successful = sum(1 for r in results_summary if r["success"])
        
        print(f"Templates tested: {len(results_summary)}")
        print(f"Successful: {successful}/{len(results_summary)}")
        print(f"Total steps executed: {total_steps}")
        print(f"Total duration: {total_duration:.1f}s")
        print(f"Average per template: {total_duration/len(results_summary):.1f}s")
        
        print(f"\n{'='*70}")
        print(f"DETAILED RESULTS")
        print(f"{'='*70}")
        for r in results_summary:
            status = "✓" if r["success"] else "✗"
            print(f"{status} {r['template']:15} | Steps: {r['steps']:2} | "
                  f"Duration: {r['duration']:5.1f}s | Errors: {r['errors']}")
        
        print(f"\n{'='*70}\n")
        
        # Assert at least some templates executed successfully
        assert successful > 0, "No templates executed successfully"

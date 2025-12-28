"""Integration tests for end-to-end episode execution."""

import pytest
from uuid import uuid4

from omen.vocabulary import TemplateID, StakesLevel, QualityTier


@pytest.mark.integration
class TestTemplateAIntegration:
    """End-to-end tests for Template A (Grounding Loop)."""
    
    def test_template_a_execution(self, integration_orchestrator):
        """Execute Template A with real LLM."""
        result = integration_orchestrator.run_template(
            TemplateID.TEMPLATE_A,
            stakes_level=StakesLevel.LOW,
            quality_tier=QualityTier.PAR,
        )
        
        print(f"\n{'='*60}")
        print(f"TEMPLATE A INTEGRATION TEST RESULTS")
        print(f"{'='*60}")
        print(f"Success: {result.success}")
        print(f"Steps: {result.step_count}")
        print(f"Duration: {result.total_duration_seconds:.2f}s")
        print(f"Errors: {result.errors}")
        
        print(f"\n{'='*60}")
        print(f"STEP DETAILS")
        print(f"{'='*60}")
        for i, step in enumerate(result.steps_completed, 1):
            print(f"\n[Step {i}] {step.step_id}")
            print(f"  Success: {step.success}")
            print(f"  Packets emitted: {step.packets_emitted}")
            print(f"  Duration: {step.duration_seconds:.2f}s")
            
            if step.output and step.output.raw_response:
                preview = step.output.raw_response[:200].replace("\n", " ")
                print(f"  Response preview: {preview}...")
            
            if step.output and step.output.errors:
                print(f"  Errors: {step.output.errors}")
        
        print(f"\n{'='*60}")
        print(f"LEDGER SUMMARY")
        print(f"{'='*60}")
        for k, v in result.ledger_summary.items():
            print(f"  {k}: {v}")
        
        print(f"\n{'='*60}\n")
        
        # Basic assertions
        assert result.step_count > 0, "Should execute at least one step"
    
    def test_template_a_with_initial_context(self, integration_orchestrator):
        """Execute Template A with initial context."""
        result = integration_orchestrator.run_template(
            TemplateID.TEMPLATE_A,
            initial_packets=[{
                "type": "seed",
                "content": "System is initializing for EVE Online market analysis",
            }],
        )
        
        print(f"\n{'='*60}")
        print(f"TEMPLATE A WITH CONTEXT")
        print(f"{'='*60}")
        print(f"Success: {result.success}")
        print(f"Steps: {result.step_count}")
        print(f"Duration: {result.total_duration_seconds:.2f}s")
        
        if result.steps_completed:
            print(f"\nFirst step response preview:")
            first_step = result.steps_completed[0]
            if first_step.output and first_step.output.raw_response:
                preview = first_step.output.raw_response[:300]
                print(f"{preview}...")
        
        print(f"\n{'='*60}\n")
        
        assert result.step_count > 0
    
    def test_template_a_token_usage(self, integration_orchestrator):
        """Track token usage during Template A execution."""
        result = integration_orchestrator.run_template(
            TemplateID.TEMPLATE_A,
            stakes_level=StakesLevel.LOW,
            quality_tier=QualityTier.PAR,
        )
        
        print(f"\n{'='*60}")
        print(f"TOKEN USAGE ANALYSIS")
        print(f"{'='*60}")
        
        total_prompt_tokens = 0
        total_completion_tokens = 0
        
        for i, step in enumerate(result.steps_completed, 1):
            print(f"\n[Step {i}] {step.step_id}")
            if hasattr(step, 'token_usage'):
                print(f"  Token usage: {step.token_usage}")
                if isinstance(step.token_usage, dict):
                    total_prompt_tokens += step.token_usage.get('prompt_tokens', 0)
                    total_completion_tokens += step.token_usage.get('completion_tokens', 0)
        
        total_tokens = total_prompt_tokens + total_completion_tokens
        print(f"\n{'='*60}")
        print(f"TOTAL TOKEN USAGE")
        print(f"{'='*60}")
        print(f"  Prompt tokens: {total_prompt_tokens}")
        print(f"  Completion tokens: {total_completion_tokens}")
        print(f"  Total tokens: {total_tokens}")
        
        # Rough cost estimate for gpt-4o-mini
        # $0.15/1M input, $0.60/1M output
        cost = (total_prompt_tokens * 0.15 / 1_000_000) + (total_completion_tokens * 0.60 / 1_000_000)
        print(f"  Estimated cost: ${cost:.6f}")
        
        print(f"\n{'='*60}\n")
        
        assert result.step_count > 0


@pytest.mark.integration  
class TestTemplateEIntegration:
    """Integration tests for Template E (Escalation)."""
    
    def test_template_e_execution(self, integration_orchestrator):
        """Execute Template E (Escalation) with real LLM."""
        result = integration_orchestrator.run_template(
            TemplateID.TEMPLATE_E,
            stakes_level=StakesLevel.HIGH,
            quality_tier=QualityTier.SUBPAR,  # E allows SUBPAR
        )
        
        print(f"\n{'='*60}")
        print(f"TEMPLATE E ESCALATION TEST")
        print(f"{'='*60}")
        print(f"Success: {result.success}")
        print(f"Steps: {result.step_count}")
        print(f"Duration: {result.total_duration_seconds:.2f}s")
        print(f"Errors: {result.errors}")
        
        print(f"\n{'='*60}")
        print(f"ESCALATION FLOW")
        print(f"{'='*60}")
        for i, step in enumerate(result.steps_completed, 1):
            print(f"\n[Step {i}] {step.step_id}")
            print(f"  Success: {step.success}")
            print(f"  Packets: {step.packets_emitted}")
            
            if step.output and step.output.raw_response:
                # Look for escalation keywords
                response_lower = step.output.raw_response.lower()
                if any(kw in response_lower for kw in ['escalate', 'escalation', 'human', 'layer_1']):
                    print(f"  ⚠️  Contains escalation keywords")
        
        print(f"\n{'='*60}\n")
        
        assert result.step_count > 0


@pytest.mark.integration
class TestEpisodeErrorHandling:
    """Integration tests for error scenarios."""
    
    def test_handles_unparseable_response(self, integration_orchestrator):
        """System gracefully handles when LLM produces unparseable output."""
        # This is a meta-test: we execute and observe what happens
        # We expect the system to log errors but continue
        result = integration_orchestrator.run_template(
            TemplateID.TEMPLATE_A,
            stakes_level=StakesLevel.LOW,
            quality_tier=QualityTier.PAR,
        )
        
        print(f"\n{'='*60}")
        print(f"ERROR HANDLING TEST")
        print(f"{'='*60}")
        print(f"Success: {result.success}")
        print(f"Steps attempted: {result.step_count}")
        
        error_count = 0
        for i, step in enumerate(result.steps_completed, 1):
            if step.output and step.output.errors:
                error_count += len(step.output.errors)
                print(f"\n[Step {i}] {step.step_id}")
                print(f"  Errors encountered:")
                for err in step.output.errors:
                    print(f"    - {err}")
        
        print(f"\nTotal errors across all steps: {error_count}")
        print(f"\n{'='*60}\n")
        
        # System should complete even if some parsing fails
        assert result.step_count > 0
        
        if error_count > 0:
            print(f"⚠️  Found {error_count} errors - this is valuable data for prompt refinement")
        else:
            print(f"✓ No errors detected - prompts may be working well")

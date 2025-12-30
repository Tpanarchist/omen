#!/usr/bin/env python3
"""
OMEN Cognitive Transcript Generator - All Templates Demo
Demonstrates all 8 canonical episode templates:
- Template A: Grounding Loop (Sense → Model → Decide)
- Template B: Verification Loop (VERIFY_FIRST handling)
- Template C: Read-Only Act (safe read operations)
- Template D: Write Act (consequential actions with authorization)
- Template E: Escalation (human handoff)
- Template F: Degraded Tools (partial tool availability)
- Template G: Compile-to-Code (code generation)
- Template H: Full-Stack Mission (all 6 layers)

Each template shows different cognitive patterns under HIGH stakes and SUPERB quality.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from omen.clients.openai_client import OpenAIClient
from omen.orchestrator.orchestrator import create_orchestrator
from omen.demo.transcript_generator import CognitiveTranscriptGenerator
from omen.vocabulary.enums import StakesLevel, QualityTier, TemplateID
from datetime import datetime, timezone


def print_step(step_num: int, total: int, message: str, status: str = "..."):
    """Print a formatted step message."""
    print(f"\n[{step_num}/{total}] {message}")
    if status != "...":
        print(f"      {status}")


def main():
    print("=" * 80)
    print("OMEN COGNITIVE TRANSCRIPT - ALL TEMPLATES DEMONSTRATION")
    print("=" * 80)
    print("\nThis demo runs all 8 canonical episode templates to show")
    print("different cognitive patterns under HIGH stakes and SUPERB quality.\n")

    # Check for API key
    print_step(1, 5, "Checking OpenAI API key...", "...")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("      ✗ Error: OPENAI_API_KEY not set")
        print("\n💡 Set your API key: $env:OPENAI_API_KEY='your-key-here'")
        sys.exit(1)
    print_step(1, 5, "Checking OpenAI API key...", "✓ API key found")

    # Create LLM client
    print_step(2, 5, "Initializing OpenAI client...", "...")
    llm_client = OpenAIClient()
    print_step(2, 5, "Initializing OpenAI client...", "✓ Client initialized")

    # Create orchestrator
    print_step(3, 5, "Creating orchestrator...", "...")
    orchestrator = create_orchestrator(llm_client=llm_client)
    print_step(3, 5, "Creating orchestrator...", "✓ Orchestrator ready")

    # Configure generator
    print_step(4, 5, "Configuring transcript generator...", "...")
    generator = CognitiveTranscriptGenerator(
        include_llm_reasoning=True,
        include_raw_prompts=False,
        max_content_length=800
    )
    print_step(4, 5, "Configuring transcript generator...", 
              "✓ Generator configured for detailed output")

    # Define all templates with descriptions
    templates = [
        (TemplateID.TEMPLATE_A, "Grounding Loop", "Sense → Model → Decide"),
        (TemplateID.TEMPLATE_B, "Verification Loop", "VERIFY_FIRST handling"),
        (TemplateID.TEMPLATE_C, "Read-Only Act", "Safe read operations"),
        (TemplateID.TEMPLATE_D, "Write Act", "Consequential actions + auth"),
        (TemplateID.TEMPLATE_E, "Escalation", "Human handoff flow"),
        (TemplateID.TEMPLATE_F, "Degraded Tools", "Partial tool availability"),
        (TemplateID.TEMPLATE_G, "Compile-to-Code", "Code generation"),
        (TemplateID.TEMPLATE_H, "Full-Stack Mission", "All 6 layers"),
    ]
    
    # Budget settings
    token_budget = 5000
    tool_call_budget = 12
    time_budget = 90
    
    print_step(5, 5, "Executing all 8 templates...", "...")
    print(f"      Common settings:")
    print(f"        - Stakes: HIGH")
    print(f"        - Quality: SUPERB")
    print(f"        - Token budget: {token_budget}")
    print(f"        - Tool call budget: {tool_call_budget}")
    print(f"        - Time budget: {time_budget}s")
    print()
    print("      ⚠️  This will make real API calls for all 8 templates!")
    print()

    output_dir = Path("transcripts")
    output_dir.mkdir(exist_ok=True)
    
    results_summary = []
    
    # Run all templates
    for idx, (template_id, name, pattern) in enumerate(templates, 1):
        print(f"\n{'─' * 80}")
        print(f"[{idx}/8] Running Template {template_id.value}: {name}")
        print(f"{'─' * 80}")
        print(f"Pattern: {pattern}")
        print()
        
        start_time = datetime.now(timezone.utc)
        
        try:
            result = orchestrator.run_template(
                template_id=template_id,
                stakes_level=StakesLevel.HIGH,
                quality_tier=QualityTier.SUPERB,
                token_budget=token_budget,
                tool_call_budget=tool_call_budget,
                time_budget_seconds=time_budget
            )
            
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            # Calculate resource consumption
            total_tokens = sum(
                step.tokens_consumed or 0 
                for step in result.steps_completed
            )
            total_tools = sum(
                step.tool_calls_consumed or 0 
                for step in result.steps_completed
            )
            
            print(f"✓ Success: {result.success}")
            print(f"✓ Steps: {len(result.steps_completed)}")
            print(f"✓ Duration: {duration:.2f}s")
            print(f"✓ Tokens: {total_tokens}/{token_budget} ({total_tokens/token_budget*100:.1f}%)")
            print(f"✓ Tool calls: {total_tools}/{tool_call_budget}")
            
            # Generate transcript
            generator.from_episode_result(result)
            transcript = generator.generate_transcript()
            
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"template_{template_id.value}_{name.replace(' ', '_').lower()}_{timestamp}.txt"
            filepath = output_dir / filename
            generator.save(filepath)
            
            file_size = filepath.stat().st_size
            print(f"✓ Transcript saved: {filepath.name} ({file_size:,} bytes)")
            
            # Save summary
            results_summary.append({
                'template': template_id.value,
                'name': name,
                'pattern': pattern,
                'success': result.success,
                'steps': len(result.steps_completed),
                'duration': duration,
                'tokens': total_tokens,
                'tools': total_tools,
                'file': filepath.name,
                'size': file_size
            })
            
        except Exception as e:
            print(f"✗ Error: {e}")
            results_summary.append({
                'template': template_id.value,
                'name': name,
                'pattern': pattern,
                'error': str(e)
            })
    
    # Final summary
    print("\n" + "=" * 80)
    print("ALL TEMPLATES DEMONSTRATION COMPLETE")
    print("=" * 80)
    
    # Summary table
    print("\nResults Summary:")
    print()
    print(f"{'Template':<12} {'Name':<20} {'Steps':<7} {'Tokens':<10} {'Duration':<10} {'Status':<8}")
    print(f"{'-'*12} {'-'*20} {'-'*7} {'-'*10} {'-'*10} {'-'*8}")
    
    for r in results_summary:
        if 'error' not in r:
            status = "✓" if r['success'] else "✗"
            print(f"{r['template']:<12} {r['name']:<20} {r['steps']:<7} "
                  f"{r['tokens']:<10} {r['duration']:<10.1f}s {status:<8}")
        else:
            print(f"{r['template']:<12} {r['name']:<20} {'ERROR':<7} {'-':<10} {'-':<10} ✗")
    
    # Total statistics
    successful = [r for r in results_summary if 'error' not in r and r['success']]
    if successful:
        total_tokens = sum(r['tokens'] for r in successful)
        total_duration = sum(r['duration'] for r in successful)
        total_steps = sum(r['steps'] for r in successful)
        
        print()
        print(f"Total Statistics:")
        print(f"  Templates executed: {len(successful)}/{len(templates)}")
        print(f"  Total steps: {total_steps}")
        print(f"  Total tokens consumed: {total_tokens:,}")
        print(f"  Total duration: {total_duration:.1f}s")
        print(f"  Average tokens per template: {total_tokens/len(successful):.0f}")
    
    print()
    print("Template Characteristics Demonstrated:")
    print("  A - Grounding Loop: Basic sense-model-decide cycle")
    print("  B - Verification Loop: VERIFY_FIRST before acting")
    print("  C - Read-Only Act: Safe read operations without side effects")
    print("  D - Write Act: Consequential actions with authorization")
    print("  E - Escalation: Human handoff when needed")
    print("  F - Degraded Tools: Handling partial tool availability")
    print("  G - Compile-to-Code: Multi-step code generation")
    print("  H - Full-Stack Mission: Complete 6-layer cognitive cycle")
    print()
    print(f"All transcripts saved to: {output_dir}/")
    print()
    print("💡 Tips:")
    print("   - Compare transcripts to see cognitive pattern differences")
    print("   - Look for VERIFY_FIRST vs ACT decision patterns")
    print("   - Notice budget consumption varies by template complexity")
    print("   - Template H shows all 6 layers in action")


if __name__ == "__main__":
    main()

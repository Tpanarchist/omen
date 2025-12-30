"""
Cognitive Transcript Demo — Demonstrates transcript generation.

Runs a simple episode and generates a detailed transcript showing
all cognitive processes, budget consumption, and epistemic tracking.

This demonstrates how OMEN's invisible cognitive processes can be
made transparent for debugging, auditing, and stakeholder presentations.

NOTE: This demo uses a MOCK orchestrator (no real LLM calls).
      For real LLM reasoning with OpenAI, use:
      python demos/cognitive_transcript_demo_real.py

Usage:
    python demos/cognitive_transcript_demo.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from omen.orchestrator import create_mock_orchestrator
from omen.vocabulary import TemplateID, StakesLevel, QualityTier
from omen.demo import CognitiveTranscriptGenerator


def main():
    """
    Run demonstration of cognitive transcript generation.
    
    This creates a mock episode execution and generates a transcript
    showing all seven sections of the cognitive process visualization.
    """
    print("=" * 80)
    print("OMEN COGNITIVE TRANSCRIPT GENERATOR - DEMONSTRATION")
    print("=" * 80)
    print()
    
    # Set up mock orchestrator (no real LLM calls)
    print("[1/5] Initializing orchestrator...")
    orchestrator = create_mock_orchestrator()
    print("      ✓ Mock orchestrator created (no real LLM calls)")
    print("      💡 For real LLM: Use cognitive_transcript_demo_real.py")
    print()
    
    # Set up transcript generator
    print("[2/5] Configuring transcript generator...")
    generator = CognitiveTranscriptGenerator(
        include_llm_reasoning=True,
        include_raw_prompts=False,  # Too verbose for demo
        max_content_length=200,
    )
    print("      ✓ Generator configured with:")
    print("        - LLM reasoning: Enabled")
    print("        - Raw prompts: Disabled")
    print("        - Max content: 200 chars")
    print()
    
    # Run episode
    print("[3/5] Running cognitive episode...")
    print("      Template: A (Grounding Loop)")
    print("      Stakes: MEDIUM")
    print("      Quality: PAR")
    print()
    
    try:
        result = orchestrator.run_template(
            template_id=TemplateID.TEMPLATE_A,
        )
        
        print(f"      ✓ Episode completed: {result.success}")
        print(f"      ✓ Steps executed: {result.step_count}")
        print(f"      ✓ Duration: {result.total_duration_seconds:.2f}s")
        print()
    except Exception as e:
        print(f"      ✗ Episode failed: {e}")
        print()
        return 1
    
    # Generate transcript
    print("[4/5] Generating transcript...")
    try:
        generator.from_episode_result(result)
        transcript = generator.generate_transcript()
        print(f"      ✓ Transcript generated ({len(transcript)} characters)")
        print()
    except Exception as e:
        print(f"      ✗ Transcript generation failed: {e}")
        print()
        return 1
    
    # Save to file
    print("[5/5] Saving transcript...")
    output_dir = Path("transcripts")
    output_dir.mkdir(exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"episode_{result.correlation_id}_{timestamp}.txt"
    
    try:
        generator.save(output_file)
        print(f"      ✓ Transcript saved to: {output_file}")
        print(f"      ✓ File size: {len(transcript)} bytes")
        print()
    except Exception as e:
        print(f"      ✗ Save failed: {e}")
        print()
        return 1
    
    # Display preview
    print("=" * 80)
    print("TRANSCRIPT PREVIEW (First 2000 characters)")
    print("=" * 80)
    print()
    print(transcript[:2000])
    if len(transcript) > 2000:
        print()
        print(f"\n[...truncated {len(transcript) - 2000} characters, see full transcript in file...]")
    print()
    
    # Summary
    print("=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print()
    print("Key Features Demonstrated:")
    print("  ✓ Episode execution tracking")
    print("  ✓ Seven-section transcript format:")
    print("    1. Episode Header (metadata, budgets, policy)")
    print("    2. Cognitive Flow (step-by-step reasoning)")
    print("    3. Packet Flow Trace (causation chains)")
    print("    4. Budget Timeline (resource consumption)")
    print("    5. Epistemic Hygiene (beliefs, evidence, assumptions)")
    print("    6. Integrity Events (alerts, safe mode)")
    print("    7. Summary (outcome, efficiency, lessons)")
    print()
    print("  ✓ Human-readable format for:")
    print("    - Debugging cognitive processes")
    print("    - Auditing decision rationale")
    print("    - Stakeholder presentations")
    print("    - Documentation and examples")
    print()
    print(f"View full transcript: {output_file}")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

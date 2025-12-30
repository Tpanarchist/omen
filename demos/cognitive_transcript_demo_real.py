"""
Cognitive Transcript Demo (Real LLM) — Demonstrates transcript generation with OpenAI.

Runs a real episode with OpenAI GPT models and generates a detailed transcript
showing actual LLM reasoning, token consumption, and decision-making processes.

This demonstrates the full value of cognitive transcript generation:
- Real reasoning from GPT-4
- Actual token consumption tracking
- Genuine tool execution results
- Authentic decision-making processes

Requirements:
    - OpenAI API key in environment variable OPENAI_API_KEY
    - Or in .env file: OPENAI_API_KEY=sk-...

Usage:
    python demos/cognitive_transcript_demo_real.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from omen.orchestrator import create_orchestrator
from omen.vocabulary import TemplateID, StakesLevel, QualityTier
from omen.demo import CognitiveTranscriptGenerator
from omen.clients import OpenAIClient, OPENAI_AVAILABLE


def check_openai_key() -> bool:
    """Check if OpenAI API key is configured."""
    # Try environment variable
    if os.getenv("OPENAI_API_KEY"):
        return True
    
    # Try .env file
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("OPENAI_API_KEY=") and len(line.split("=", 1)[1].strip()) > 0:
                return True
    
    return False


def main():
    """
    Run demonstration of cognitive transcript generation with real LLM.
    
    This creates a real episode execution using OpenAI GPT models and generates
    a transcript showing actual reasoning, token consumption, and decision-making.
    """
    print("=" * 80)
    print("OMEN COGNITIVE TRANSCRIPT GENERATOR - REAL LLM DEMONSTRATION")
    print("=" * 80)
    print()
    
    # Check for OpenAI API key
    print("[1/6] Checking OpenAI API key...")
    
    if not OPENAI_AVAILABLE:
        print("      ✗ OpenAI package not installed!")
        print()
        print("      Please install it:")
        print("      pip install openai")
        print()
        return 1
    
    if not check_openai_key():
        print("      ✗ OpenAI API key not found!")
        print()
        print("      Please set your OpenAI API key:")
        print("      1. Set environment variable: OPENAI_API_KEY=sk-...")
        print("      2. Or create .env file with: OPENAI_API_KEY=sk-...")
        print()
        print("      Then run this script again.")
        return 1
    
    print("      ✓ OpenAI API key found")
    print()
    
    # Set up real orchestrator with OpenAI client
    print("[2/6] Initializing orchestrator with OpenAI client...")
    try:
        # Create real OpenAI client
        llm_client = OpenAIClient()
        orchestrator = create_orchestrator(llm_client=llm_client)
        print("      ✓ Real orchestrator created (using OpenAI GPT models)")
        print()
    except Exception as e:
        print(f"      ✗ Failed to create orchestrator: {e}")
        return 1
    
    # Set up transcript generator
    print("[3/6] Configuring transcript generator...")
    generator = CognitiveTranscriptGenerator(
        include_llm_reasoning=True,
        include_raw_prompts=False,  # Set to True to see full prompts
        max_content_length=500,
    )
    print("      ✓ Generator configured with:")
    print("        - LLM reasoning: Enabled")
    print("        - Raw prompts: Disabled (set to True for full prompts)")
    print("        - Max content: 500 chars")
    print()
    
    # Run episode
    print("[4/6] Running cognitive episode with real LLM...")
    print("      Template: A (Grounding Loop)")
    print("      Stakes: MEDIUM")
    print("      Quality: PAR")
    print("      Budget: 2000 tokens, 5 tool calls, 120s")
    print()
    print("      ⚠️  This will make real API calls and consume tokens!")
    print("      ⏳ Please wait while the LLM processes the episode...")
    print()
    
    try:
        result = orchestrator.run_template(
            template_id=TemplateID.TEMPLATE_A,
            stakes_level=StakesLevel.MEDIUM,
            quality_tier=QualityTier.PAR,
        )
        
        print(f"      ✓ Episode completed: {result.success}")
        print(f"      ✓ Steps executed: {result.step_count}")
        print(f"      ✓ Duration: {result.total_duration_seconds:.2f}s")
        
        # Show budget consumption
        ledger = result.ledger_summary.get("budget", {})
        tokens_consumed = ledger.get("tokens_consumed", 0)
        tool_calls_consumed = ledger.get("tool_calls_consumed", 0)
        
        print(f"      ✓ Tokens consumed: {tokens_consumed}")
        print(f"      ✓ Tool calls made: {tool_calls_consumed}")
        print()
        
    except Exception as e:
        print(f"      ✗ Episode failed: {e}")
        print()
        import traceback
        traceback.print_exc()
        return 1
    
    # Generate transcript
    print("[5/6] Generating transcript...")
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
    print("[6/6] Saving transcript...")
    output_dir = Path("transcripts")
    output_dir.mkdir(exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"episode_real_{result.correlation_id}_{timestamp}.txt"
    
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
    print("TRANSCRIPT PREVIEW (First 3000 characters)")
    print("=" * 80)
    print()
    print(transcript[:3000])
    if len(transcript) > 3000:
        print()
        print(f"\n[...truncated {len(transcript) - 3000} characters, see full transcript in file...]")
    print()
    
    # Summary
    print("=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print()
    print("Key Features Demonstrated:")
    print("  ✓ Real LLM reasoning captured from GPT models")
    print("  ✓ Actual token consumption tracked")
    print("  ✓ Genuine tool execution results")
    print("  ✓ Authentic decision-making processes")
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
    print("💡 Tip: Set include_raw_prompts=True to see full system prompts")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

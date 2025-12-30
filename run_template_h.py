"""Run Template H individually to generate its transcript."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from omen.orchestrator.orchestrator import create_orchestrator
from omen.demo.transcript_generator import CognitiveTranscriptGenerator
from omen.vocabulary.enums import StakesLevel, QualityTier, TemplateID
from datetime import datetime, timezone

print("Creating orchestrator...")
orchestrator = create_orchestrator()

print("Running Template H (Full-Stack Mission)...")
print("This is the most complex template with all 6 layers engaged.\n")

try:
    result = orchestrator.run_template(
        template_id=TemplateID.TEMPLATE_H,
        stakes_level=StakesLevel.HIGH,
        quality_tier=QualityTier.SUPERB,
        token_budget=5000,
        tool_call_budget=12,
        time_budget_seconds=90
    )
    
    print(f"[OK] Episode completed: {result.success}")
    print(f"[OK] Steps: {result.step_count}")
    print(f"[OK] Duration: {result.total_duration_seconds:.2f}s\n")
    
    # Generate transcript
    print("Generating transcript...")
    generator = CognitiveTranscriptGenerator(
        include_llm_reasoning=True,
        include_raw_prompts=False,
        max_content_length=400
    )
    
    # Build capture from result
    generator.from_episode_result(result)
    
    # Generate transcript text
    transcript = generator.generate_transcript()
    
    # Save transcript
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"template_TEMPLATE_H_full-stack_mission_{timestamp}.txt"
    filepath = Path("transcripts") / filename
    filepath.parent.mkdir(exist_ok=True)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(transcript)
    
    print(f"[OK] Transcript saved: {filepath}")
    print(f"[OK] Size: {len(transcript):,} bytes")
    print(f"\nFirst 200 lines:\n")
    print("\n".join(transcript.split("\n")[:200]))
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()

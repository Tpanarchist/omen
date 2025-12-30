#!/usr/bin/env python3
"""Quick test of transcript generator fixes."""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent / "src"))

from omen.clients.openai_client import OpenAIClient
from omen.orchestrator.orchestrator import create_orchestrator
from omen.demo.transcript_generator import CognitiveTranscriptGenerator
from omen.vocabulary.enums import StakesLevel, QualityTier, TemplateID

# Create LLM client
print("Creating orchestrator...")
llm_client = OpenAIClient()
orchestrator = create_orchestrator(llm_client=llm_client)

# Run a quick episode
print("Running Template A...")
result = orchestrator.run_template(
    template_id=TemplateID.TEMPLATE_A,
    stakes_level=StakesLevel.HIGH,
    quality_tier=QualityTier.SUPERB,
    token_budget=5000,
    tool_call_budget=12,
    time_budget_seconds=90
)

print(f"Episode completed: {result.success}, {len(result.steps_completed)} steps")

# Generate transcript
print("Generating transcript...")
generator = CognitiveTranscriptGenerator(
    include_llm_reasoning=True,
    max_content_length=800
)
generator.from_episode_result(result)
transcript = generator.generate_transcript()

# Save
timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
filepath = Path("transcripts") / f"test_fixes_{timestamp}.txt"
filepath.parent.mkdir(exist_ok=True)
generator.save(filepath)

print(f"\nSaved to: {filepath}")
print(f"Size: {filepath.stat().st_size:,} bytes")

# Show first 150 lines
print("\n" + "="*80)
print("PREVIEW (first 150 lines):")
print("="*80)
lines = transcript.split("\n")
for line in lines[:150]:
    print(line)

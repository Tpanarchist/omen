"""Debug script to inspect packet structure."""
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from omen.orchestrator.orchestrator import create_orchestrator
from omen.vocabulary.enums import StakesLevel, QualityTier, TemplateID

# Create orchestrator
orchestrator = create_orchestrator()

# Run short template
result = orchestrator.run_template(
    template_id=TemplateID.TEMPLATE_A,
    stakes_level=StakesLevel.HIGH,
    quality_tier=QualityTier.SUPERB
)

print(f"\nEpisode completed: {result.success}")
print(f"Total steps: {len(result.steps_completed)}")

# Check all steps for packets
packet_count = 0
for i, step in enumerate(result.steps_completed, 1):
    print(f"\nStep {i} ({step.step_id}):")
    print(f"  packets_emitted (count): {step.packets_emitted}")
    print(f"  packets_emitted_list (len): {len(step.packets_emitted_list)}")
    if step.packets_emitted_list:
        packet_count += 1
        print(f"  Has {len(step.packets_emitted_list)} packets!")
        for j, packet in enumerate(step.packets_emitted_list, 1):
            print(f"\n  Packet {j} type: {type(packet)}")
            if isinstance(packet, dict):
                print(f"  Keys: {list(packet.keys())}")
                print(f"  Full structure:")
                print(json.dumps(packet, indent=4, default=str))
            else:
                print(f"  Object class: {packet.__class__.__name__}")
                print(f"  Attributes: {dir(packet)[:10]}...")
                if hasattr(packet, "header"):
                    print(f"  Has header: {type(packet.header)}")
                    if hasattr(packet.header, "packet_type"):
                        print(f"  packet_type: {packet.header.packet_type}")
        break

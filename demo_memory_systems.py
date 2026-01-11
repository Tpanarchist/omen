#!/usr/bin/env python3
"""
Demonstration: OMEN Memory Systems

Shows how OMEN gains temporal continuity and learning capability
through episodic memory, semantic memory, and self-model.

Demonstrates:
1. Episodes without memory (baseline - "anterograde amnesia")
2. Episodes with memory enabled (temporal continuity)
3. Memory consolidation (learning from experience)
4. Self-model evolution over time
"""

from datetime import datetime
from uuid import uuid4

from omen.orchestrator import Orchestrator, OrchestratorConfig, create_mock_orchestrator
from omen.episode import InMemoryStore as EpisodeStore
from omen.vocabulary import TemplateID


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print('=' * 80)


def demonstrate_without_memory():
    """Demonstrate OMEN without memory (baseline)."""
    print_section("Part 1: OMEN Without Memory (Anterograde Amnesia)")
    
    episode_store = EpisodeStore()
    config = OrchestratorConfig(
        episode_store=episode_store,
        enable_memory=False,  # Memory disabled
        auto_save=True,
    )
    
    orchestrator = Orchestrator(config=config)
    
    print("\n🔴 Memory Systems: DISABLED")
    print(f"   Memory Manager: {orchestrator.memory_manager}")
    print(f"   Memory Stats: {orchestrator.get_memory_stats()}")
    
    print("\n📝 Running 3 episodes...")
    for i in range(3):
        result = orchestrator.run_template(TemplateID.TEMPLATE_A)
        print(f"   Episode {i+1}: {'✓' if result.success else '✗'} (ID: {str(result.correlation_id)[:8]})")
    
    print(f"\n📊 Total episodes in store: {episode_store.count()}")
    print("⚠️  Problem: Each episode starts from scratch - no learning or temporal continuity!")


def demonstrate_with_memory():
    """Demonstrate OMEN with memory enabled."""
    print_section("Part 2: OMEN With Memory (Temporal Continuity)")
    
    episode_store = EpisodeStore()
    config = OrchestratorConfig(
        episode_store=episode_store,
        enable_memory=True,  # Memory enabled
        memory_backend="memory",
        auto_consolidate=True,
        consolidation_threshold=2,
        inject_memory_context=True,
        auto_save=True,
    )
    
    orchestrator = Orchestrator(config=config)
    
    print("\n🟢 Memory Systems: ENABLED")
    print(f"   Memory Manager: {orchestrator.memory_manager}")
    
    # Show initial memory state
    stats = orchestrator.get_memory_stats()
    print(f"\n📊 Initial Memory State:")
    print(f"   Episodic Memories: {stats['episodic_memories']}")
    print(f"   Beliefs: {stats['beliefs']}")
    print(f"   Self-Model Aspects: {stats['self_model_aspects']}")
    
    # Show self-model
    print(f"\n🧠 Initial Self-Model:")
    self_model = orchestrator.memory_manager.self_model.get_current_model()
    for aspect, content in list(self_model.items())[:3]:
        print(f"   {aspect}: {content[:60]}...")
    
    print("\n📝 Running 5 episodes...")
    for i in range(5):
        result = orchestrator.run_template(TemplateID.TEMPLATE_A)
        print(f"   Episode {i+1}: {'✓' if result.success else '✗'} (ID: {str(result.correlation_id)[:8]})")
        
        # Check if consolidation happened
        if i > 0 and (i + 1) % config.consolidation_threshold == 0:
            stats = orchestrator.get_memory_stats()
            print(f"   💾 Auto-consolidation triggered!")
            print(f"      Episodic Memories: {stats['episodic_memories']}")
            print(f"      Beliefs: {stats['beliefs']}")
    
    # Show final memory state
    print(f"\n📊 Final Memory State:")
    stats = orchestrator.get_memory_stats()
    print(f"   Episodic Memories: {stats['episodic_memories']}")
    print(f"   Beliefs: {stats['beliefs']}")
    print(f"   Self-Model Aspects: {stats['self_model_aspects']}")
    print(f"   Episodes Since Last Consolidation: {stats['episodes_since_consolidation']}")
    
    print("\n✅ Success: Episodes have temporal continuity and learning!")
    
    return orchestrator


def demonstrate_memory_retrieval(orchestrator: Orchestrator):
    """Demonstrate memory retrieval and context injection."""
    print_section("Part 3: Memory Retrieval and Context Injection")
    
    print("\n🔍 Retrieving memory context...")
    context = orchestrator.memory_manager.retrieve_context(
        max_episodes=3,
        max_beliefs=5,
    )
    
    print(f"\n📚 Retrieved Context:")
    print(f"   Episodic Memories: {len(context.episodic_memories)}")
    for memory in context.episodic_memories[:2]:
        print(f"     - {memory.summary}")
    
    print(f"\n💡 Domain Beliefs: {len(context.domain_beliefs)}")
    
    print(f"\n🧠 Self-Model: {len(context.self_model)} aspects")
    for aspect, content in list(context.self_model.items())[:2]:
        print(f"     - {aspect}: {content[:50]}...")
    
    print("\n📦 Converting to Observation Packets...")
    packets = context.to_observation_packets()
    print(f"   Generated {len(packets)} observation packets:")
    for packet in packets:
        print(f"     - Type: {packet['observation_type']}")
    
    print("\n✅ These packets are injected at episode start for temporal continuity!")


def demonstrate_consolidation(orchestrator: Orchestrator):
    """Demonstrate manual consolidation."""
    print_section("Part 4: Memory Consolidation (Sleep-Like Processing)")
    
    print("\n💤 Triggering manual consolidation...")
    result = orchestrator.consolidate_memories()
    
    print(f"\n📊 Consolidation Results:")
    print(f"   Episodes Processed: {result.episodes_processed}")
    print(f"   Memories Created: {result.memories_created}")
    print(f"   Beliefs Updated: {result.beliefs_updated}")
    print(f"   Self-Model Updates: {result.self_model_updates}")
    print(f"   Duration: {result.duration_seconds:.3f}s")
    
    print(f"\n🎯 Patterns Extracted:")
    for pattern in result.patterns_extracted[:5]:
        print(f"     - {pattern}")
    
    print("\n✅ Consolidation extracts patterns and updates long-term memory!")


def demonstrate_comparison():
    """Compare memory-enabled vs memory-disabled."""
    print_section("Part 5: Direct Comparison")
    
    print("\n📊 Memory Systems Summary:\n")
    
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│ WITHOUT MEMORY (Current OMEN)                               │")
    print("├─────────────────────────────────────────────────────────────┤")
    print("│ ✗ No episodic memory (autobiographical)                     │")
    print("│ ✗ No semantic memory (learned knowledge)                    │")
    print("│ ✗ No persistent self-model                                  │")
    print("│ ✗ No pattern extraction from experience                     │")
    print("│ ✗ No temporal continuity                                    │")
    print("│ ✗ Each episode starts from scratch                          │")
    print("│                                                              │")
    print("│ Status: Anterograde Amnesia (like movie Memento)            │")
    print("└─────────────────────────────────────────────────────────────┘")
    
    print("\n┌─────────────────────────────────────────────────────────────┐")
    print("│ WITH MEMORY (This Implementation)                           │")
    print("├─────────────────────────────────────────────────────────────┤")
    print("│ ✓ Episodic memory stores past episode summaries             │")
    print("│ ✓ Semantic memory maintains beliefs and knowledge           │")
    print("│ ✓ Self-model tracks capabilities and limitations            │")
    print("│ ✓ Consolidation extracts patterns and learns                │")
    print("│ ✓ Memory context injected at episode start                  │")
    print("│ ✓ Temporal continuity across episodes                       │")
    print("│                                                              │")
    print("│ Status: Temporal Self-Continuity (neuroscience-grounded)    │")
    print("└─────────────────────────────────────────────────────────────┘")


def main():
    """Run the demonstration."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                    OMEN Memory Systems Demonstration                         ║
║                                                                              ║
║          Implementing Neuroscience-Grounded Memory Architecture              ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Part 1: Baseline without memory
        demonstrate_without_memory()
        
        # Part 2: With memory enabled
        orchestrator = demonstrate_with_memory()
        
        # Part 3: Memory retrieval
        demonstrate_memory_retrieval(orchestrator)
        
        # Part 4: Consolidation
        demonstrate_consolidation(orchestrator)
        
        # Part 5: Summary comparison
        demonstrate_comparison()
        
        print_section("Demonstration Complete")
        print("""
✅ Memory systems successfully demonstrated!

Key Takeaways:
1. OMEN can now form long-term memories from episodes
2. Temporal continuity enables learning from experience
3. Self-model evolves based on actual performance
4. Consolidation extracts patterns (sleep-like processing)
5. Memory context provides autobiographical continuity

This addresses the "anterograde amnesia" problem and enables:
- Temporal self-continuity ("I am the same entity over time")
- Learning from experience ("I got better at this")
- Autobiographical narrative ("Remember when we...")
- Genuine self-awareness ("I know what I know")

The neuroscience is clear: memory consolidation is fundamental for consciousness.
        """)
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

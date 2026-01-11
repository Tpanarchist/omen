"""
Memory — Long-term memory systems for OMEN.

Provides:
- Episodic memory: Autobiographical episode summaries
- Semantic memory: Learned beliefs and knowledge
- Self-model: Persistent sense of self and capabilities
- Consolidation: Pattern extraction and belief updates

Addresses the "anterograde amnesia" problem where OMEN lacks
temporal continuity and cannot form long-term memories.

Based on neuroscience principles:
- Working memory (episodes) → Long-term memory (storage)
- Hippocampal-like consolidation
- Context-dependent retrieval
"""

from omen.memory.episodic import (
    EpisodicMemory,
    EpisodicMemoryStore,
    InMemoryEpisodicStore,
    SQLiteEpisodicStore,
    create_episodic_store,
)
from omen.memory.semantic import (
    Belief,
    SemanticMemory,
    SemanticMemoryStore,
    InMemorySemanticStore,
    SQLiteSemanticStore,
    create_semantic_store,
)
from omen.memory.self_model import (
    SelfModelAspect,
    SelfModel,
    SelfModelStore,
    InMemorySelfModelStore,
    SQLiteSelfModelStore,
    create_self_model_store,
)
from omen.memory.consolidation import (
    ConsolidationCycle,
    create_consolidation_cycle,
)
from omen.memory.manager import (
    MemoryContext,
    MemoryManager,
    create_memory_manager,
)

__all__ = [
    # Episodic memory
    "EpisodicMemory",
    "EpisodicMemoryStore",
    "InMemoryEpisodicStore",
    "SQLiteEpisodicStore",
    "create_episodic_store",
    # Semantic memory
    "Belief",
    "SemanticMemory",
    "SemanticMemoryStore",
    "InMemorySemanticStore",
    "SQLiteSemanticStore",
    "create_semantic_store",
    # Self-model
    "SelfModelAspect",
    "SelfModel",
    "SelfModelStore",
    "InMemorySelfModelStore",
    "SQLiteSelfModelStore",
    "create_self_model_store",
    # Consolidation
    "ConsolidationCycle",
    "create_consolidation_cycle",
    # Memory Manager
    "MemoryContext",
    "MemoryManager",
    "create_memory_manager",
]

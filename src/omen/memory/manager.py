"""
Memory Manager — Orchestrates memory operations for episodes.

Coordinates memory retrieval, injection, and consolidation to give
OMEN temporal continuity and learning capability.

Spec: Based on problem statement requirements for memory-aware episodes.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from omen.episode import EpisodeStore, EpisodeRecord
from omen.memory.episodic import EpisodicMemoryStore, EpisodicMemory, create_episodic_store
from omen.memory.semantic import SemanticMemoryStore, SemanticMemory, create_semantic_store
from omen.memory.self_model import SelfModelStore, SelfModel, create_self_model_store
from omen.memory.consolidation import ConsolidationCycle, create_consolidation_cycle


@dataclass
class MemoryContext:
    """
    Memory context to inject into episode.
    
    Contains relevant memories retrieved from long-term storage.
    """
    episodic_memories: list[EpisodicMemory]
    domain_beliefs: list[Any]  # Beliefs from semantic memory
    self_model: dict[str, str]  # Current self-model aspects
    
    def to_observation_packets(self) -> list[dict[str, Any]]:
        """
        Convert memory context to observation packets.
        
        These packets will be injected at episode start to provide
        temporal continuity and learned knowledge.
        """
        packets = []
        
        # Add episodic memories as autobiographical context
        if self.episodic_memories:
            packets.append({
                "observation_type": "autobiographical_memory",
                "content": {
                    "recent_episodes": [
                        {
                            "episode_id": str(mem.episode_id),
                            "timestamp": mem.timestamp.isoformat(),
                            "summary": mem.summary,
                            "outcome": mem.outcome,
                            "lessons_learned": mem.lessons_learned,
                        }
                        for mem in self.episodic_memories
                    ]
                }
            })
        
        # Add beliefs as domain knowledge
        if self.domain_beliefs:
            packets.append({
                "observation_type": "belief_state",
                "content": {
                    "beliefs": [
                        {
                            "domain": b.domain,
                            "claim": b.claim,
                            "confidence": b.confidence,
                        }
                        for b in self.domain_beliefs
                    ]
                }
            })
        
        # Add self-model as self-awareness
        if self.self_model:
            packets.append({
                "observation_type": "self_model",
                "content": {
                    "aspects": self.self_model
                }
            })
        
        return packets


class MemoryManager:
    """
    Manages memory operations for OMEN episodes.
    
    Provides:
    - Memory retrieval before episode execution
    - Memory consolidation after episode execution
    - Automatic background consolidation
    """
    
    def __init__(
        self,
        episode_store: EpisodeStore,
        episodic_store: EpisodicMemoryStore | None = None,
        semantic_store: SemanticMemoryStore | None = None,
        self_model_store: SelfModelStore | None = None,
        auto_consolidate: bool = True,
        consolidation_threshold: int = 5,  # Consolidate after N episodes
    ):
        """
        Initialize memory manager.
        
        Args:
            episode_store: Store for episode records (working memory)
            episodic_store: Store for episodic memories (optional, created if None)
            semantic_store: Store for semantic memories (optional, created if None)
            self_model_store: Store for self-model (optional, created if None)
            auto_consolidate: Automatically consolidate after threshold
            consolidation_threshold: Number of episodes before auto-consolidation
        """
        self.episode_store = episode_store
        self.episodic_store = episodic_store or create_episodic_store("memory")
        self.semantic_store = semantic_store or create_semantic_store("memory")
        self.self_model_store = self_model_store or create_self_model_store("memory")
        
        self.auto_consolidate = auto_consolidate
        self.consolidation_threshold = consolidation_threshold
        self._episodes_since_consolidation = 0
        
        # Create high-level memory interfaces
        self.semantic_memory = SemanticMemory(self.semantic_store)
        self.self_model = SelfModel(self.self_model_store)
        
        # Create consolidation cycle
        self.consolidation = create_consolidation_cycle(
            episode_store=self.episode_store,
            episodic_store=self.episodic_store,
            semantic_store=self.semantic_store,
            self_model_store=self.self_model_store,
        )
        
        # Bootstrap self-model if empty
        if self.self_model_store.count() == 0:
            self.bootstrap_self_model()
    
    def retrieve_context(
        self,
        domain: str | None = None,
        query: str | None = None,
        max_episodes: int = 5,
        max_beliefs: int = 10,
    ) -> MemoryContext:
        """
        Retrieve relevant memory context for episode initialization.
        
        Args:
            domain: Domain to filter memories (optional)
            query: Text query for episode search (optional)
            max_episodes: Maximum episodic memories to retrieve
            max_beliefs: Maximum beliefs to retrieve
        
        Returns:
            MemoryContext with relevant memories
        """
        # Search for relevant episodic memories
        episodic_memories = self.episodic_store.search(
            query=query,
            domain=domain,
            limit=max_episodes,
        )
        
        # Query domain beliefs
        domain_beliefs = []
        if domain:
            domain_beliefs = self.semantic_memory.get_domain_beliefs(
                domain=domain,
                min_confidence=0.5,
            )[:max_beliefs]
        
        # Get current self-model
        self_model = self.self_model.get_current_model()
        
        return MemoryContext(
            episodic_memories=episodic_memories,
            domain_beliefs=domain_beliefs,
            self_model=self_model,
        )
    
    def after_episode(self, episode: EpisodeRecord) -> None:
        """
        Called after episode completion.
        
        Triggers auto-consolidation if threshold reached.
        
        Args:
            episode: The completed episode record
        """
        self._episodes_since_consolidation += 1
        
        if self.auto_consolidate and self._episodes_since_consolidation >= self.consolidation_threshold:
            self.consolidate()
    
    def consolidate(self, since: datetime | None = None) -> Any:
        """
        Run memory consolidation cycle.
        
        Converts working memory (episodes) into long-term memory
        (episodic memories, beliefs, self-model updates).
        
        Args:
            since: Only consolidate episodes since this time (default: last hour)
        
        Returns:
            ConsolidationResult with metrics
        """
        result = self.consolidation.consolidate(since=since)
        self._episodes_since_consolidation = 0
        return result
    
    def get_memory_stats(self) -> dict[str, Any]:
        """
        Get statistics about memory stores.
        
        Returns:
            Dictionary with memory statistics
        """
        return {
            "episodic_memories": self.episodic_store.count(),
            "beliefs": self.semantic_store.count(),
            "self_model_aspects": self.self_model_store.count(),
            "episodes_total": self.episode_store.count(),
            "episodes_since_consolidation": self._episodes_since_consolidation,
        }
    
    def bootstrap_self_model(self, initial_aspects: dict[str, str] | None = None) -> None:
        """
        Bootstrap the self-model with initial aspects.
        
        Args:
            initial_aspects: Dictionary of aspect -> content mappings
        """
        if initial_aspects is None:
            # Default bootstrap
            initial_aspects = {
                "purpose": "To assist, learn, and improve over time through experience",
                "capabilities": "Can execute episode templates, use tools, and process information",
                "limitations": "Learning from experience, temporal continuity being established",
                "preferences": "Prefers clear objectives, incremental learning, and evidence-based updates",
            }
        
        for aspect, content in initial_aspects.items():
            self.self_model.update_aspect(
                aspect=aspect,
                content=content,
                confidence=0.5,  # Initial bootstrap confidence
            )


def create_memory_manager(
    episode_store: EpisodeStore,
    backend: str = "memory",
    db_path: str | None = None,
    auto_consolidate: bool = True,
    consolidation_threshold: int = 5,
) -> MemoryManager:
    """
    Factory for creating memory manager.
    
    Args:
        episode_store: Store for episode records
        backend: "memory" or "sqlite" for memory stores
        db_path: Path to SQLite database (only for sqlite backend)
        auto_consolidate: Enable automatic consolidation
        consolidation_threshold: Episodes before auto-consolidation
    
    Returns:
        MemoryManager instance
    """
    episodic_store = create_episodic_store(backend, db_path)
    semantic_store = create_semantic_store(backend, db_path)
    self_model_store = create_self_model_store(backend, db_path)
    
    manager = MemoryManager(
        episode_store=episode_store,
        episodic_store=episodic_store,
        semantic_store=semantic_store,
        self_model_store=self_model_store,
        auto_consolidate=auto_consolidate,
        consolidation_threshold=consolidation_threshold,
    )
    
    # Bootstrap self-model with defaults
    if self_model_store.count() == 0:
        manager.bootstrap_self_model()
    
    return manager

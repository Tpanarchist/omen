"""
Consolidation — Memory consolidation and pattern extraction.

Implements the "sleep-like" consolidation process that:
- Extracts patterns from recent episodes
- Updates beliefs based on patterns
- Integrates learning into self-model
- Prunes episodic memory details

Analogous to sleep-dependent memory consolidation in neuroscience.

Spec: Based on problem statement requirements for consolidation.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from omen.episode import EpisodeRecord, EpisodeStore
from omen.memory.episodic import EpisodicMemory, EpisodicMemoryStore
from omen.memory.semantic import SemanticMemory, SemanticMemoryStore
from omen.memory.self_model import SelfModel, SelfModelStore


@dataclass
class ConsolidationResult:
    """Result of a consolidation cycle."""
    episodes_processed: int
    memories_created: int
    beliefs_updated: int
    self_model_updates: int
    patterns_extracted: list[str]
    duration_seconds: float


class ConsolidationCycle:
    """
    Memory consolidation processor.
    
    Converts working memory (episodes) into long-term memory
    (episodic memories, beliefs, self-model updates).
    """
    
    def __init__(
        self,
        episode_store: EpisodeStore,
        episodic_store: EpisodicMemoryStore,
        semantic_store: SemanticMemoryStore,
        self_model_store: SelfModelStore,
    ):
        self.episode_store = episode_store
        self.episodic_store = episodic_store
        self.semantic_memory = SemanticMemory(semantic_store)
        self.self_model = SelfModel(self_model_store)
    
    def consolidate(
        self,
        since: datetime | None = None,
        max_episodes: int = 10,
    ) -> ConsolidationResult:
        """
        Run a consolidation cycle.
        
        Args:
            since: Only consolidate episodes since this time (default: last hour)
            max_episodes: Maximum episodes to process
        
        Returns:
            ConsolidationResult with metrics
        """
        start_time = datetime.now()
        
        # Default to last hour if not specified
        if since is None:
            since = datetime.now() - timedelta(hours=1)
        
        # Get recent episodes
        episodes = self.episode_store.query(
            since=since,
            limit=max_episodes,
        )
        
        patterns_extracted = []
        memories_created = 0
        beliefs_updated = 0
        self_model_updates = 0
        
        for episode in episodes:
            # Check if already consolidated
            existing_memory = self.episodic_store.load(episode.correlation_id)
            if existing_memory:
                continue
            
            # Create episodic memory
            memory = self._create_episodic_memory(episode)
            self.episodic_store.save(memory)
            memories_created += 1
            
            # Extract patterns and update beliefs
            patterns = self._extract_patterns(episode)
            patterns_extracted.extend(patterns)
            
            for pattern in patterns:
                self._update_beliefs_from_pattern(pattern, episode)
                beliefs_updated += 1
            
            # Update self-model based on episode outcome
            if self._should_update_self_model(episode):
                self._update_self_model(episode)
                self_model_updates += 1
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return ConsolidationResult(
            episodes_processed=len(episodes),
            memories_created=memories_created,
            beliefs_updated=beliefs_updated,
            self_model_updates=self_model_updates,
            patterns_extracted=patterns_extracted,
            duration_seconds=duration,
        )
    
    def _create_episodic_memory(self, episode: EpisodeRecord) -> EpisodicMemory:
        """Convert episode record to episodic memory."""
        # Extract key events from steps
        key_events = []
        for step in episode.steps[:5]:  # Keep first 5 steps
            if step.packet_type:
                key_events.append(f"L{step.layer}: {step.packet_type}")
        
        # Determine outcome
        outcome = "success" if episode.success else "failure"
        if episode.errors:
            outcome = "failure"
        
        # Extract lessons learned from errors
        lessons_learned = []
        for error in episode.errors[:3]:  # Keep first 3 errors
            lessons_learned.append(f"Error: {error[:100]}")
        
        # Generate context tags
        context_tags = [episode.template_id, episode.stakes_level]
        if episode.tools_state != "TOOLS_OK":
            context_tags.append(episode.tools_state)
        
        # Create summary
        summary = f"Executed {episode.template_id} with {len(episode.steps)} steps"
        if episode.success:
            summary += " (succeeded)"
        else:
            summary += " (failed)"
        
        return EpisodicMemory(
            episode_id=episode.correlation_id,
            timestamp=episode.started_at,
            template_id=episode.template_id,
            summary=summary,
            key_events=key_events,
            outcome=outcome,
            lessons_learned=lessons_learned,
            context_tags=context_tags,
            domain=None,  # Could be extracted from campaign_id
            duration_seconds=episode.duration_seconds,
            success=episode.success,
        )
    
    def _extract_patterns(self, episode: EpisodeRecord) -> list[str]:
        """Extract patterns from episode."""
        patterns = []
        
        # Pattern: Successful template usage
        if episode.success:
            patterns.append(f"successful_{episode.template_id}")
        
        # Pattern: Budget management
        if episode.budget_consumed:
            token_budget = episode.budget_allocated.get("token_budget", 0)
            tokens_used = episode.budget_consumed.get("tokens", 0)
            if token_budget > 0 and tokens_used > 0:
                usage_ratio = tokens_used / token_budget
                if usage_ratio < 0.5:
                    patterns.append("efficient_token_usage")
                elif usage_ratio > 0.9:
                    patterns.append("high_token_usage")
        
        # Pattern: Error types
        for error in episode.errors:
            if "timeout" in error.lower():
                patterns.append("timeout_error")
            elif "validation" in error.lower():
                patterns.append("validation_error")
        
        return patterns
    
    def _update_beliefs_from_pattern(self, pattern: str, episode: EpisodeRecord) -> None:
        """Update beliefs based on observed pattern."""
        domain = "system_performance"
        
        if pattern.startswith("successful_"):
            template = pattern.replace("successful_", "")
            claim = f"Template {template} generally succeeds"
            self.semantic_memory.add_belief(
                domain=domain,
                claim=claim,
                confidence=0.7,
                formed_from=[str(episode.correlation_id)],
            )
        
        elif pattern == "efficient_token_usage":
            claim = "Token usage is generally efficient"
            self.semantic_memory.add_belief(
                domain=domain,
                claim=claim,
                confidence=0.6,
                formed_from=[str(episode.correlation_id)],
            )
    
    def _should_update_self_model(self, episode: EpisodeRecord) -> bool:
        """Determine if episode warrants self-model update."""
        # Update on significant successes or failures
        return episode.success or len(episode.errors) > 0
    
    def _update_self_model(self, episode: EpisodeRecord) -> None:
        """Update self-model based on episode."""
        if episode.success:
            # Update capabilities
            capability = f"Can execute {episode.template_id}"
            self.self_model.update_aspect(
                aspect="capabilities",
                content=capability,
                confidence=0.8,
                episode_id=str(episode.correlation_id),
            )
        else:
            # Update limitations
            limitation = f"Encountered difficulties with {episode.template_id}"
            if episode.errors:
                limitation += f": {episode.errors[0][:100]}"
            self.self_model.update_aspect(
                aspect="limitations",
                content=limitation,
                confidence=0.7,
                episode_id=str(episode.correlation_id),
            )


def create_consolidation_cycle(
    episode_store: EpisodeStore,
    episodic_store: EpisodicMemoryStore,
    semantic_store: SemanticMemoryStore,
    self_model_store: SelfModelStore,
) -> ConsolidationCycle:
    """
    Factory for creating consolidation cycle.
    
    Args:
        episode_store: Store for episode records
        episodic_store: Store for episodic memories
        semantic_store: Store for semantic memories (beliefs)
        self_model_store: Store for self-model
    
    Returns:
        ConsolidationCycle instance
    """
    return ConsolidationCycle(
        episode_store=episode_store,
        episodic_store=episodic_store,
        semantic_store=semantic_store,
        self_model_store=self_model_store,
    )

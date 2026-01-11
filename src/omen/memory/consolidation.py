"""
Memory Consolidation — Summarize recent episodes and update memory stores.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Sequence
from uuid import UUID

from omen.episode.record import EpisodeRecord
from omen.memory.belief_store import BeliefEntry, BeliefStore
from omen.memory.self_model_store import SelfModelEntry, SelfModelStore


@dataclass
class ConsolidationResult:
    """Captures consolidation outputs for telemetry or inspection."""
    summary: str
    patterns: list[str]
    belief_ids_updated: list[str]
    self_model_entry_id: str | None


def consolidate_episodes(
    episodes: Sequence[EpisodeRecord],
    belief_store: BeliefStore,
    self_model_store: SelfModelStore,
    *,
    max_episodes: int = 5,
) -> ConsolidationResult | None:
    """Run consolidation over recent episodes."""
    if not episodes:
        return None

    recent = _select_recent_episodes(episodes, max_episodes=max_episodes)
    summary = _summarize_episodes(recent)
    patterns = _extract_patterns(recent)
    belief_ids = _update_beliefs(recent, belief_store)
    entry_id = _write_self_model(recent, summary, patterns, self_model_store)

    return ConsolidationResult(
        summary=summary,
        patterns=patterns,
        belief_ids_updated=belief_ids,
        self_model_entry_id=entry_id,
    )


def _select_recent_episodes(
    episodes: Sequence[EpisodeRecord],
    *,
    max_episodes: int,
) -> list[EpisodeRecord]:
    return sorted(
        episodes,
        key=lambda episode: episode.completed_at or episode.started_at,
        reverse=True,
    )[:max_episodes]


def _summarize_episodes(episodes: Sequence[EpisodeRecord]) -> str:
    total = len(episodes)
    successes = sum(1 for episode in episodes if episode.success)
    avg_duration = _average_duration_seconds(episodes)
    templates = Counter(episode.template_id for episode in episodes)
    template_summary = ", ".join(
        f"{template_id} x{count}" for template_id, count in templates.most_common()
    )
    return (
        f"Processed {total} episode(s), success rate {successes / total:.0%}. "
        f"Avg duration {avg_duration:.1f}s. Templates: {template_summary}."
    )


def _extract_patterns(episodes: Sequence[EpisodeRecord]) -> list[str]:
    if not episodes:
        return []

    patterns: list[str] = []
    total = len(episodes)
    successes = sum(1 for episode in episodes if episode.success)
    failure_rate = 1 - (successes / total)

    if failure_rate >= 0.5:
        patterns.append("Recent failure rate exceeds 50%.")
    elif successes == total:
        patterns.append("Recent episodes all succeeded.")

    avg_duration = _average_duration_seconds(episodes)
    if avg_duration > 120:
        patterns.append("Average episode duration is above 2 minutes.")

    template_counts = Counter(episode.template_id for episode in episodes)
    for template_id, count in template_counts.items():
        if count > 1:
            patterns.append(f"Template {template_id} executed {count} times recently.")

    error_messages = [
        error
        for episode in episodes
        for error in episode.errors
        if error
    ]
    if error_messages:
        most_common = Counter(error_messages).most_common(1)[0][0]
        patterns.append(f"Most common error observed: {most_common}.")

    return patterns


def _update_beliefs(
    episodes: Sequence[EpisodeRecord],
    belief_store: BeliefStore,
) -> list[str]:
    belief_ids: list[str] = []
    episode_ids = [episode.correlation_id for episode in episodes]

    total = len(episodes)
    successes = sum(1 for episode in episodes if episode.success)
    success_rate = successes / total if total else 0.0

    success_entry = BeliefEntry(
        belief_id="performance.recent_success_rate",
        domain="performance",
        statement=f"Recent success rate is {success_rate:.0%} across {total} episodes.",
        confidence=success_rate,
        episode_ids=episode_ids,
        metadata={"count": total, "successes": successes},
        updated_at=datetime.now(),
    )
    belief_store.upsert(success_entry)
    belief_ids.append(success_entry.belief_id)

    templates = Counter(episode.template_id for episode in episodes)
    for template_id, count in templates.items():
        template_successes = sum(
            1 for episode in episodes
            if episode.template_id == template_id and episode.success
        )
        template_rate = template_successes / count if count else 0.0
        belief_id = f"performance.template.{template_id}.success_rate"
        entry = BeliefEntry(
            belief_id=belief_id,
            domain="performance",
            statement=(
                f"Template {template_id} success rate is {template_rate:.0%} "
                f"across {count} episode(s)."
            ),
            confidence=template_rate,
            episode_ids=[
                episode.correlation_id
                for episode in episodes
                if episode.template_id == template_id
            ],
            metadata={"count": count, "successes": template_successes},
            updated_at=datetime.now(),
        )
        belief_store.upsert(entry)
        belief_ids.append(entry.belief_id)

    return belief_ids


def _write_self_model(
    episodes: Sequence[EpisodeRecord],
    summary: str,
    patterns: list[str],
    self_model_store: SelfModelStore,
) -> str:
    entry_id = f"self-model-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    entry = SelfModelEntry(
        entry_id=entry_id,
        summary=summary,
        patterns=patterns,
        episode_ids=[episode.correlation_id for episode in episodes],
        metadata={
            "episode_count": len(episodes),
            "template_ids": list({episode.template_id for episode in episodes}),
        },
        created_at=datetime.now(),
    )
    self_model_store.add_entry(entry)
    return entry_id


def _average_duration_seconds(episodes: Iterable[EpisodeRecord]) -> float:
    durations = [episode.duration_seconds for episode in episodes]
    return sum(durations) / len(durations) if durations else 0.0

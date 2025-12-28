"""
Episode Ledger — Tracks per-episode state.

Maintains running state for a single episode:
- Budget consumption
- Active tokens
- Evidence refs collected
- Open directives
- Contradiction flags

Spec: OMEN.md §10.5, §11.5
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import Any

from omen.vocabulary import StakesLevel, QualityTier, ToolsState


@dataclass
class BudgetState:
    """
    Tracks budget allocation and consumption.
    """
    # Allocated budgets
    token_budget: int = 0
    tool_call_budget: int = 0
    time_budget_seconds: int = 0
    
    # Consumed amounts
    tokens_consumed: int = 0
    tool_calls_consumed: int = 0
    time_consumed_seconds: float = 0.0
    
    # Overrun tracking
    overrun_approved: bool = False
    overrun_approved_by: str | None = None
    
    @property
    def tokens_remaining(self) -> int:
        return max(0, self.token_budget - self.tokens_consumed)
    
    @property
    def tool_calls_remaining(self) -> int:
        return max(0, self.tool_call_budget - self.tool_calls_consumed)
    
    @property
    def time_remaining_seconds(self) -> float:
        return max(0.0, self.time_budget_seconds - self.time_consumed_seconds)
    
    @property
    def is_over_budget(self) -> bool:
        return (
            self.tokens_consumed > self.token_budget or
            self.tool_calls_consumed > self.tool_call_budget or
            self.time_consumed_seconds > self.time_budget_seconds
        )
    
    def consume(
        self,
        tokens: int = 0,
        tool_calls: int = 0,
        time_seconds: float = 0.0,
    ) -> None:
        """Record resource consumption."""
        self.tokens_consumed += tokens
        self.tool_calls_consumed += tool_calls
        self.time_consumed_seconds += time_seconds


@dataclass
class ActiveToken:
    """
    Tracks an active tool authorization token.
    """
    token_id: str
    scope: dict[str, Any]
    issued_at: datetime
    expires_at: datetime
    max_uses: int
    uses_remaining: int
    revoked: bool = False
    
    @property
    def is_valid(self) -> bool:
        """Check if token is still valid."""
        if self.revoked:
            return False
        if datetime.now() > self.expires_at:
            return False
        if self.uses_remaining <= 0:
            return False
        return True
    
    def use(self) -> bool:
        """Use the token once. Returns False if invalid."""
        if not self.is_valid:
            return False
        self.uses_remaining -= 1
        return True


@dataclass
class OpenDirective:
    """
    Tracks an open (not yet completed) task directive.
    """
    directive_id: str
    task_id: str
    issued_at: datetime
    timeout_at: datetime
    status: str = "PENDING"  # PENDING, EXECUTING, COMPLETED, FAILED, CANCELLED


@dataclass
class EpisodeLedger:
    """
    Complete state tracking for an episode.
    
    Maintains all running state that persists across layer invocations
    within a single episode.
    """
    # Identity
    correlation_id: UUID
    campaign_id: str | None = None
    template_id: str | None = None
    
    # Episode metadata
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    
    # Policy state
    stakes_level: StakesLevel = StakesLevel.LOW
    quality_tier: QualityTier = QualityTier.PAR
    tools_state: ToolsState = ToolsState.TOOLS_OK
    
    # Budget tracking
    budget: BudgetState = field(default_factory=BudgetState)
    
    # Token tracking
    active_tokens: dict[str, ActiveToken] = field(default_factory=dict)
    
    # Directive tracking
    open_directives: dict[str, OpenDirective] = field(default_factory=dict)
    
    # Evidence tracking
    evidence_refs: list[dict[str, Any]] = field(default_factory=list)
    
    # Assumption tracking
    assumptions: list[dict[str, Any]] = field(default_factory=list)
    load_bearing_assumptions: list[dict[str, Any]] = field(default_factory=list)
    
    # Integrity flags
    contradiction_detected: bool = False
    contradiction_details: list[str] = field(default_factory=list)
    
    # Episode state
    current_step: str | None = None
    completed_steps: list[str] = field(default_factory=list)
    
    # Error tracking
    errors: list[str] = field(default_factory=list)
    
    @property
    def is_complete(self) -> bool:
        """Check if episode is complete."""
        return self.completed_at is not None
    
    @property
    def has_errors(self) -> bool:
        """Check if episode has errors."""
        return len(self.errors) > 0
    
    def add_token(self, token: ActiveToken) -> None:
        """Register a new active token."""
        self.active_tokens[token.token_id] = token
    
    def get_token(self, token_id: str) -> ActiveToken | None:
        """Get an active token by ID."""
        return self.active_tokens.get(token_id)
    
    def revoke_token(self, token_id: str) -> bool:
        """Revoke a token. Returns True if found."""
        token = self.active_tokens.get(token_id)
        if token:
            token.revoked = True
            return True
        return False
    
    def add_directive(self, directive: OpenDirective) -> None:
        """Register an open directive."""
        self.open_directives[directive.directive_id] = directive
    
    def close_directive(self, directive_id: str, status: str) -> bool:
        """Close a directive with status. Returns True if found."""
        directive = self.open_directives.get(directive_id)
        if directive:
            directive.status = status
            return True
        return False
    
    def add_evidence(self, evidence_ref: dict[str, Any]) -> None:
        """Add an evidence reference."""
        self.evidence_refs.append(evidence_ref)
    
    def add_assumption(
        self, 
        assumption: str, 
        load_bearing: bool = False
    ) -> None:
        """Track an assumption."""
        entry = {
            "assumption": assumption,
            "added_at": datetime.now().isoformat(),
            "load_bearing": load_bearing,
        }
        self.assumptions.append(entry)
        if load_bearing:
            self.load_bearing_assumptions.append(entry)
    
    def flag_contradiction(self, detail: str) -> None:
        """Flag a detected contradiction."""
        self.contradiction_detected = True
        self.contradiction_details.append(detail)
    
    def complete_step(self, step_id: str) -> None:
        """Mark a step as completed."""
        self.completed_steps.append(step_id)
        self.current_step = None
    
    def start_step(self, step_id: str) -> None:
        """Start executing a step."""
        self.current_step = step_id
    
    def complete_episode(self) -> None:
        """Mark the episode as complete."""
        self.completed_at = datetime.now()
    
    def add_error(self, error: str) -> None:
        """Record an error."""
        self.errors.append(error)
    
    def to_summary(self) -> dict[str, Any]:
        """Generate a summary for logging/debugging."""
        return {
            "correlation_id": str(self.correlation_id),
            "template_id": self.template_id,
            "stakes_level": self.stakes_level.value,
            "quality_tier": self.quality_tier.value,
            "budget": {
                "tokens": f"{self.budget.tokens_consumed}/{self.budget.token_budget}",
                "tool_calls": f"{self.budget.tool_calls_consumed}/{self.budget.tool_call_budget}",
                "is_over_budget": self.budget.is_over_budget,
            },
            "active_tokens": len(self.active_tokens),
            "open_directives": len([d for d in self.open_directives.values() if d.status == "PENDING"]),
            "evidence_refs": len(self.evidence_refs),
            "completed_steps": len(self.completed_steps),
            "is_complete": self.is_complete,
            "has_errors": self.has_errors,
        }


def create_ledger(
    correlation_id: UUID,
    stakes_level: StakesLevel = StakesLevel.LOW,
    quality_tier: QualityTier = QualityTier.PAR,
    budget: BudgetState | None = None,
    **kwargs
) -> EpisodeLedger:
    """Factory for episode ledger."""
    return EpisodeLedger(
        correlation_id=correlation_id,
        stakes_level=stakes_level,
        quality_tier=quality_tier,
        budget=budget or BudgetState(),
        **kwargs
    )

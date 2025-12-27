"""
Compilation Context — Runtime bindings for template compilation.

Provides the values that populate MCP fields during packet generation.
Spec: OMEN.md §11.4
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4
from typing import Any

from omen.vocabulary import (
    StakesLevel,
    QualityTier,
    ToolsState,
    VerificationRequirement,
    FreshnessClass,
)


@dataclass
class StakesContext:
    """Stakes assessment for the episode."""
    impact: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    irreversibility: str = "REVERSIBLE"
    uncertainty: str = "LOW"
    adversariality: str = "BENIGN"
    stakes_level: StakesLevel = StakesLevel.LOW


@dataclass
class QualityContext:
    """Quality requirements for the episode."""
    quality_tier: QualityTier = QualityTier.PAR
    satisficing_mode: bool = True
    verification_requirement: VerificationRequirement = VerificationRequirement.OPTIONAL
    definition_of_done: dict[str, Any] = field(default_factory=lambda: {
        "text": "Episode completed successfully",
        "checks": []
    })


@dataclass
class BudgetContext:
    """Resource budgets for the episode."""
    token_budget: int = 1000
    tool_call_budget: int = 5
    time_budget_seconds: int = 120
    risk_budget: dict[str, Any] = field(default_factory=lambda: {
        "envelope": "low",
        "max_loss": "minimal"
    })


@dataclass
class CompilationContext:
    """
    Complete context for template compilation.
    
    Provides all values needed to populate MCP fields in generated packets.
    """
    # Episode identity
    correlation_id: UUID = field(default_factory=uuid4)
    campaign_id: str | None = None
    
    # Policy contexts
    stakes: StakesContext = field(default_factory=StakesContext)
    quality: QualityContext = field(default_factory=QualityContext)
    budgets: BudgetContext = field(default_factory=BudgetContext)
    
    # Runtime state
    tools_state: ToolsState = ToolsState.TOOLS_OK
    freshness_class: FreshnessClass = FreshnessClass.OPERATIONAL
    
    # Timestamp for packet generation
    created_at: datetime = field(default_factory=datetime.now)
    
    def with_correlation_id(self, cid: UUID) -> "CompilationContext":
        """Return copy with new correlation_id."""
        return CompilationContext(
            correlation_id=cid,
            campaign_id=self.campaign_id,
            stakes=self.stakes,
            quality=self.quality,
            budgets=self.budgets,
            tools_state=self.tools_state,
            freshness_class=self.freshness_class,
            created_at=self.created_at,
        )


def create_context(
    stakes_level: StakesLevel = StakesLevel.LOW,
    quality_tier: QualityTier = QualityTier.PAR,
    tools_state: ToolsState = ToolsState.TOOLS_OK,
    **kwargs
) -> CompilationContext:
    """Factory for common compilation contexts."""
    return CompilationContext(
        stakes=StakesContext(stakes_level=stakes_level),
        quality=QualityContext(quality_tier=quality_tier),
        tools_state=tools_state,
        **kwargs
    )

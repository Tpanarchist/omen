"""
Invariant Validator — Cross-policy rules enforcement.

Third validation gate. Enforces the 6 invariants from OMEN.md §8.4:
1. Consequential directives include all required fields (enforced by schema layer)
2. SUBPAR never authorizes external action
3. HIGH/CRITICAL require verification or escalation
4. No live truth claims without tool evidence
5. Budget overruns require approval
6. Drive arbitration follows 3-stage gate (enforced by layer contracts, not packet validation)

Spec: OMEN.md §8.4, §15.4
"""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from omen.vocabulary import (
    PacketType,
    QualityTier,
    StakesLevel,
    EpistemicStatus,
    ToolSafety,
    DecisionOutcome,
)
from omen.validation.schema_validator import ValidationResult, Packet
from omen.schemas.packets import (
    DecisionPacket,
    TaskDirectivePacket,
    ToolAuthorizationToken,
)


# =============================================================================
# EPISODE BUDGET TRACKING
# =============================================================================

@dataclass
class BudgetLedger:
    """
    Tracks budget consumption for an episode.
    
    Used to detect budget overruns per invariant #5.
    """
    episode_id: UUID
    
    # Allocated budgets (from first directive)
    token_budget: int = 0
    tool_call_budget: int = 0
    time_budget_seconds: int = 0
    
    # Consumed
    tokens_consumed: int = 0
    tool_calls_consumed: int = 0
    time_elapsed_seconds: int = 0
    
    # Approval tracking
    budget_overrun_approved: bool = False
    overrun_approved_by: str | None = None  # Layer that approved
    
    def is_overrun(self) -> tuple[bool, list[str]]:
        """Check if any budget is exceeded."""
        overruns = []
        if self.token_budget > 0 and self.tokens_consumed > self.token_budget:
            overruns.append(f"tokens: {self.tokens_consumed}/{self.token_budget}")
        if self.tool_call_budget > 0 and self.tool_calls_consumed > self.tool_call_budget:
            overruns.append(f"tool_calls: {self.tool_calls_consumed}/{self.tool_call_budget}")
        if self.time_budget_seconds > 0 and self.time_elapsed_seconds > self.time_budget_seconds:
            overruns.append(f"time: {self.time_elapsed_seconds}s/{self.time_budget_seconds}s")
        return len(overruns) > 0, overruns


# =============================================================================
# INVARIANT VALIDATOR
# =============================================================================

class InvariantValidator:
    """
    Validates cross-policy invariants.
    
    Enforces the 6 rules from OMEN.md §8.4 that span multiple policies.
    Invariants 1 and 6 are enforced elsewhere (schema layer and layer contracts).
    
    Spec: OMEN.md §8.4, §15.4
    """
    
    def __init__(self):
        self._budget_ledgers: dict[UUID, BudgetLedger] = {}
    
    def get_or_create_ledger(self, episode_id: UUID) -> BudgetLedger:
        """Get existing budget ledger or create new one."""
        if episode_id not in self._budget_ledgers:
            self._budget_ledgers[episode_id] = BudgetLedger(episode_id=episode_id)
        return self._budget_ledgers[episode_id]
    
    def validate(self, packet: Packet) -> ValidationResult:
        """
        Validate all cross-policy invariants for a packet.
        
        Checks invariants 2-5 from §8.4:
        - Invariant 1 (MCP completeness) enforced by schema layer
        - Invariant 2: SUBPAR never authorizes external action
        - Invariant 3: HIGH/CRITICAL require verification or escalation
        - Invariant 4: No live truth without tool evidence
        - Invariant 5: Budget overruns require approval
        - Invariant 6 (drive arbitration) enforced by layer contracts, not packet validation
        """
        result = ValidationResult.success()
        
        # Invariant 2: SUBPAR never authorizes external action
        result = result.merge(self._check_subpar_no_action(packet))
        
        # Invariant 3: HIGH/CRITICAL require verification or escalation
        result = result.merge(self._check_high_stakes_verification(packet))
        
        # Invariant 4: No live truth without tool evidence
        result = result.merge(self._check_live_truth_grounding(packet))
        
        # Invariant 5: Budget overruns require approval
        result = result.merge(self._check_budget_approval(packet))
        
        return result
    
    def _check_subpar_no_action(self, packet: Packet) -> ValidationResult:
        """
        Invariant 2: SUBPAR outputs MUST NOT authorize external action.
        
        SUBPAR quality tier can only be used for speculative/informational
        outputs, never for directives that cause external effects.
        
        Spec: OMEN.md §8.4 bullet 2, §8.2.2
        """
        errors = []
        warnings = []
        
        # Check if this is an action-authorizing packet
        is_action_packet = isinstance(packet, (TaskDirectivePacket, ToolAuthorizationToken))
        
        if is_action_packet:
            tier = packet.mcp.quality.quality_tier
            if tier == QualityTier.SUBPAR:
                errors.append(
                    "SUBPAR quality tier cannot authorize external action. "
                    "Upgrade to PAR or SUPERB."
                )
        
        # Also check Decision packets with ACT outcome
        if isinstance(packet, DecisionPacket):
            if packet.payload.decision_outcome == DecisionOutcome.ACT:
                tier = packet.mcp.quality.quality_tier
                if tier == QualityTier.SUBPAR:
                    errors.append(
                        "SUBPAR quality tier cannot issue ACT decision. "
                        "Use VERIFY_FIRST, ESCALATE, or DEFER instead."
                    )
        
        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _check_high_stakes_verification(self, packet: Packet) -> ValidationResult:
        """
        Invariant 3: HIGH/CRITICAL require verification loops or escalation/refusal.
        
        High-stakes decisions cannot proceed with ACT unless verification
        has been completed or escalation is chosen.
        
        Spec: OMEN.md §8.4 bullet 3, §8.2.2
        """
        errors = []
        warnings = []
        
        stakes_level = packet.mcp.stakes.stakes_level
        
        # Only applies to Decision packets with ACT outcome
        if isinstance(packet, DecisionPacket):
            outcome = packet.payload.decision_outcome
            
            if stakes_level in (StakesLevel.HIGH, StakesLevel.CRITICAL):
                if outcome == DecisionOutcome.ACT:
                    # ACT at HIGH/CRITICAL requires SUPERB tier
                    tier = packet.mcp.quality.quality_tier
                    if tier != QualityTier.SUPERB:
                        errors.append(
                            f"HIGH/CRITICAL stakes with ACT outcome requires SUPERB tier, "
                            f"got {tier.value}. Use VERIFY_FIRST or ESCALATE instead."
                        )
                    
                    # Should have evidence refs (verification completed)
                    if not packet.mcp.evidence.evidence_refs:
                        warnings.append(
                            "HIGH/CRITICAL ACT decision has no evidence refs. "
                            "Verify load-bearing assumptions were checked."
                        )
        
        # Task directives at HIGH/CRITICAL should have strong evidence
        if isinstance(packet, TaskDirectivePacket):
            if stakes_level in (StakesLevel.HIGH, StakesLevel.CRITICAL):
                if not packet.mcp.evidence.evidence_refs:
                    warnings.append(
                        "HIGH/CRITICAL TaskDirective has no evidence refs. "
                        "Ensure verification was completed."
                    )
        
        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _check_live_truth_grounding(self, packet: Packet) -> ValidationResult:
        """
        Invariant 4: LLM cannot claim live truth without tool evidence refs.
        
        Claims about current reality (OBSERVED status, high confidence)
        must be backed by tool evidence, not inference.
        
        Spec: OMEN.md §8.4 bullet 4, §8.1
        """
        errors = []
        warnings = []
        
        epistemics = packet.mcp.epistemics
        evidence = packet.mcp.evidence
        
        # OBSERVED status requires evidence refs
        if epistemics.status == EpistemicStatus.OBSERVED:
            if not evidence.evidence_refs:
                errors.append(
                    "OBSERVED epistemic status requires tool/sensor evidence refs. "
                    "Use INFERRED or HYPOTHESIZED if no direct observation."
                )
        
        # High confidence DERIVED should reference inputs
        if epistemics.status == EpistemicStatus.DERIVED:
            if epistemics.confidence > 0.9 and not evidence.evidence_refs:
                warnings.append(
                    "High confidence DERIVED claim has no evidence refs. "
                    "Consider adding refs to input observations."
                )
        
        # INFERRED/HYPOTHESIZED with high confidence is suspicious
        if epistemics.status in (EpistemicStatus.INFERRED, EpistemicStatus.HYPOTHESIZED):
            if epistemics.confidence > 0.8:
                warnings.append(
                    f"{epistemics.status.value} with confidence {epistemics.confidence} "
                    "may be overconfident. Consider verification or lower confidence."
                )
        
        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _check_budget_approval(self, packet: Packet) -> ValidationResult:
        """
        Invariant 5: Budget overruns require explicit approval.
        
        At HIGH/CRITICAL stakes, Layer 1 must approve budget overruns.
        
        Spec: OMEN.md §8.4 bullet 5, §8.2.4
        """
        errors = []
        warnings = []
        
        episode_id = packet.header.correlation_id
        ledger = self.get_or_create_ledger(episode_id)
        
        # Update budgets from first directive we see
        if ledger.token_budget == 0:
            ledger.token_budget = packet.mcp.budgets.token_budget
            ledger.tool_call_budget = packet.mcp.budgets.tool_call_budget
            ledger.time_budget_seconds = packet.mcp.budgets.time_budget_seconds
        
        # Check for overruns
        is_overrun, overrun_details = ledger.is_overrun()
        
        if is_overrun and not ledger.budget_overrun_approved:
            stakes_level = packet.mcp.stakes.stakes_level
            
            if stakes_level in (StakesLevel.HIGH, StakesLevel.CRITICAL):
                errors.append(
                    f"Budget overrun at {stakes_level.value} stakes requires Layer 1 approval. "
                    f"Overruns: {', '.join(overrun_details)}"
                )
            else:
                warnings.append(
                    f"Budget overrun detected: {', '.join(overrun_details)}. "
                    "Consider escalation or scope reduction."
                )
        
        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def update_budget_consumption(
        self,
        episode_id: UUID,
        tokens: int = 0,
        tool_calls: int = 0,
        time_seconds: int = 0,
    ) -> None:
        """Update budget consumption for an episode."""
        ledger = self.get_or_create_ledger(episode_id)
        ledger.tokens_consumed += tokens
        ledger.tool_calls_consumed += tool_calls
        ledger.time_elapsed_seconds += time_seconds
    
    def approve_budget_overrun(
        self,
        episode_id: UUID,
        approving_layer: str,
    ) -> None:
        """Record budget overrun approval."""
        ledger = self.get_or_create_ledger(episode_id)
        ledger.budget_overrun_approved = True
        ledger.overrun_approved_by = approving_layer
    
    def reset_episode(self, episode_id: UUID) -> None:
        """Reset budget ledger for an episode."""
        if episode_id in self._budget_ledgers:
            del self._budget_ledgers[episode_id]


# Convenience function
def create_invariant_validator() -> InvariantValidator:
    """Create a new invariant validator instance."""
    return InvariantValidator()

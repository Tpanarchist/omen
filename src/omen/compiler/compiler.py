"""
Template Compiler — Transforms templates into executable packet sequences.

Spec: OMEN.md §11.4 "Template compilation rules"
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
from typing import Any

from omen.vocabulary import TemplateID, QualityTier, ToolsState
from omen.templates import EpisodeTemplate, TemplateStep, TemplateValidator
from omen.compiler.context import CompilationContext
from omen.compiler.compiled import CompiledStep, CompiledEpisode


@dataclass
class CompilationError:
    """Error during compilation."""
    step_id: str | None
    message: str


@dataclass
class CompilationResult:
    """Result of template compilation."""
    success: bool
    episode: CompiledEpisode | None = None
    errors: list[CompilationError] = field(default_factory=list)


class TemplateCompiler:
    """
    Compiles episode templates into executable packet sequences.
    
    Per §11.4:
    1. Allocates correlation_id
    2. Binds MCP fields from context
    3. Generates compiled steps
    4. Validates template before compilation
    """
    
    def __init__(self, validator: TemplateValidator | None = None):
        self.validator = validator
    
    def compile(
        self,
        template: EpisodeTemplate,
        context: CompilationContext,
    ) -> CompilationResult:
        """
        Compile a template with the given context.
        
        Returns CompilationResult with compiled episode or errors.
        """
        errors: list[CompilationError] = []
        
        # 1. Validate template if validator provided
        if self.validator:
            validation = self.validator.validate(template)
            if not validation.valid:
                return CompilationResult(
                    success=False,
                    errors=[
                        CompilationError(e.step_id, f"Validation: {e.message}")
                        for e in validation.errors
                    ]
                )
        
        # 2. Check constraints
        constraint_errors = self._check_constraints(template, context)
        if constraint_errors:
            return CompilationResult(success=False, errors=constraint_errors)
        
        # 3. Compile steps
        compiled_steps = []
        for seq_num, step in enumerate(template.steps):
            compiled = self._compile_step(step, seq_num, context, template)
            compiled_steps.append(compiled)
        
        # 4. Build compiled episode
        episode = CompiledEpisode(
            correlation_id=context.correlation_id,
            template_id=template.template_id,
            campaign_id=context.campaign_id,
            steps=compiled_steps,
            entry_step=template.entry_step,
            exit_steps=template.exit_steps,
            compiled_at=context.created_at,
            context_snapshot=self._snapshot_context(context),
            current_step=None,
            completed=False,
        )
        
        return CompilationResult(success=True, episode=episode)
    
    def _check_constraints(
        self,
        template: EpisodeTemplate,
        context: CompilationContext,
    ) -> list[CompilationError]:
        """Check template constraints against context."""
        errors = []
        constraints = template.constraints
        
        # Check quality tier
        # NOTE: Depends on enum order. If QualityTier values change, update this.
        # Tests will catch mismatches immediately.
        tier_order = [QualityTier.SUBPAR, QualityTier.PAR, QualityTier.SUPERB]
        context_tier_idx = tier_order.index(context.quality.quality_tier)
        required_tier_idx = tier_order.index(constraints.min_tier)
        
        if context_tier_idx < required_tier_idx:
            errors.append(CompilationError(
                None,
                f"Context tier {context.quality.quality_tier.value} "
                f"below required {constraints.min_tier.value}"
            ))
        
        # Check tools state
        if context.tools_state not in constraints.tools_state:
            errors.append(CompilationError(
                None,
                f"Tools state {context.tools_state.value} "
                f"not in allowed {[t.value for t in constraints.tools_state]}"
            ))
        
        return errors
    
    def _compile_step(
        self,
        step: TemplateStep,
        sequence_number: int,
        context: CompilationContext,
        template: EpisodeTemplate,
    ) -> CompiledStep:
        """Compile a single template step."""
        # Build MCP bindings from context + step bindings
        mcp_bindings = self._build_mcp_bindings(context, step.bindings)
        
        return CompiledStep(
            step_id=step.step_id,
            sequence_number=sequence_number,
            owner_layer=step.owner_layer,
            fsm_state=step.fsm_state,
            packet_type=step.packet_type,
            mcp_bindings=mcp_bindings,
            next_steps=step.next_steps,
            executed=False,
            packet_id=None,
        )
    
    def _build_mcp_bindings(
        self,
        context: CompilationContext,
        step_bindings: dict[str, Any],
    ) -> dict[str, Any]:
        """Build MCP field bindings from context and step overrides."""
        bindings = {
            # From context
            "correlation_id": str(context.correlation_id),
            "campaign_id": context.campaign_id,
            "stakes": {
                "impact": context.stakes.impact,
                "irreversibility": context.stakes.irreversibility,
                "uncertainty": context.stakes.uncertainty,
                "adversariality": context.stakes.adversariality,
                "stakes_level": context.stakes.stakes_level.value,
            },
            "quality": {
                "quality_tier": context.quality.quality_tier.value,
                "satisficing_mode": context.quality.satisficing_mode,
                "verification_requirement": context.quality.verification_requirement.value,
                "definition_of_done": context.quality.definition_of_done,
            },
            "budgets": {
                "token_budget": context.budgets.token_budget,
                "tool_call_budget": context.budgets.tool_call_budget,
                "time_budget_seconds": context.budgets.time_budget_seconds,
                "risk_budget": context.budgets.risk_budget,
            },
            "routing": {
                "tools_state": context.tools_state.value,
            },
            # Epistemics defaults (pre-execution artifacts)
            "epistemics": {
                "status": "HYPOTHESIZED",
                "confidence": 0.5,
                "freshness_class": context.freshness_class.value,
                "calibration_note": "Pre-execution estimate",
            },
            # Evidence defaults (step not yet executed)
            "evidence": {
                "evidence_refs": [],
                "evidence_absent_reason": "Step not yet executed",
            },
            # Intent left unbound - filled at runtime by layer
        }
        
        # Apply step-specific overrides
        bindings.update(step_bindings)
        
        return bindings
    
    def _snapshot_context(self, context: CompilationContext) -> dict[str, Any]:
        """Create serializable snapshot of compilation context."""
        return {
            "correlation_id": str(context.correlation_id),
            "campaign_id": context.campaign_id,
            "stakes_level": context.stakes.stakes_level.value,
            "quality_tier": context.quality.quality_tier.value,
            "tools_state": context.tools_state.value,
            "compiled_at": context.created_at.isoformat(),
        }


def create_compiler(validator: TemplateValidator | None = None) -> TemplateCompiler:
    """Factory for template compiler."""
    return TemplateCompiler(validator=validator)

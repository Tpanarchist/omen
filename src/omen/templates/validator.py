"""
Template Validator — Validates template internal consistency.

Ensures templates have valid step references, legal FSM transitions,
and layer contracts are respected before compilation.

Spec: OMEN.md §11.1, §11.2, §10.3
"""

from dataclasses import dataclass, field
from typing import Any

from omen.vocabulary import LayerSource, PacketType, FSMState
from omen.templates.models import EpisodeTemplate, TemplateStep
from omen.validation.fsm_validator import LEGAL_TRANSITIONS
from omen.layers.contracts import get_contract


# =============================================================================
# VALIDATION RESULT
# =============================================================================

@dataclass
class TemplateValidationError:
    """Single validation error."""
    rule: str
    step_id: str | None
    message: str


@dataclass
class TemplateValidationResult:
    """Result of template validation."""
    valid: bool
    template_id: str
    errors: list[TemplateValidationError] = field(default_factory=list)
    warnings: list[TemplateValidationError] = field(default_factory=list)


# =============================================================================
# TEMPLATE VALIDATOR
# =============================================================================

class TemplateValidator:
    """
    Validates episode templates for internal consistency.
    
    Checks:
    - Step connectivity (all references valid)
    - Entry/exit validity
    - FSM compliance (legal transitions)
    - Layer contracts (allowed packet types)
    - Reachability (no orphaned steps)
    """
    
    def validate(self, template: EpisodeTemplate) -> TemplateValidationResult:
        """
        Validate a template.
        
        Returns TemplateValidationResult with valid=True if all checks pass.
        """
        errors: list[TemplateValidationError] = []
        warnings: list[TemplateValidationError] = []
        
        # Run all validation checks
        errors.extend(self._check_step_connectivity(template))
        errors.extend(self._check_entry_exit(template))
        errors.extend(self._check_fsm_compliance(template))
        errors.extend(self._check_layer_contracts(template))
        errors.extend(self._check_reachability(template))
        warnings.extend(self._check_dead_ends(template))
        
        return TemplateValidationResult(
            valid=len(errors) == 0,
            template_id=template.template_id.value,
            errors=errors,
            warnings=warnings,
        )
    
    def validate_all(
        self, templates: list[EpisodeTemplate]
    ) -> dict[str, TemplateValidationResult]:
        """Validate multiple templates, return results keyed by template_id."""
        return {t.template_id.value: self.validate(t) for t in templates}
    
    def _check_step_connectivity(
        self, template: EpisodeTemplate
    ) -> list[TemplateValidationError]:
        """Check that all next_steps references point to existing steps."""
        errors = []
        step_ids = template.get_step_ids()
        
        for step in template.steps:
            for next_id in step.next_steps:
                if next_id not in step_ids:
                    errors.append(TemplateValidationError(
                        rule="step_connectivity",
                        step_id=step.step_id,
                        message=f"next_step '{next_id}' not found in template",
                    ))
        
        return errors
    
    def _check_entry_exit(
        self, template: EpisodeTemplate
    ) -> list[TemplateValidationError]:
        """Check entry_step and exit_steps validity."""
        errors = []
        step_ids = template.get_step_ids()
        
        # Entry must exist (already validated by model, but defense in depth)
        if template.entry_step not in step_ids:
            errors.append(TemplateValidationError(
                rule="entry_valid",
                step_id=None,
                message=f"entry_step '{template.entry_step}' not found",
            ))
        
        # Exit steps must exist and have no next_steps
        for exit_id in template.exit_steps:
            if exit_id not in step_ids:
                errors.append(TemplateValidationError(
                    rule="exit_valid",
                    step_id=None,
                    message=f"exit_step '{exit_id}' not found",
                ))
            else:
                exit_step = template.get_step(exit_id)
                if exit_step and exit_step.next_steps:
                    errors.append(TemplateValidationError(
                        rule="exit_valid",
                        step_id=exit_id,
                        message=f"exit_step '{exit_id}' has next_steps (should be empty)",
                    ))
        
        return errors
    
    def _check_fsm_compliance(
        self, template: EpisodeTemplate
    ) -> list[TemplateValidationError]:
        """Check that step transitions are legal per FSM."""
        errors = []
        
        for step in template.steps:
            from_state = step.fsm_state
            
            for next_id in step.next_steps:
                next_step = template.get_step(next_id)
                if next_step is None:
                    continue  # Caught by connectivity check
                
                to_state = next_step.fsm_state
                legal_targets = LEGAL_TRANSITIONS.get(from_state, set())
                
                if to_state not in legal_targets:
                    errors.append(TemplateValidationError(
                        rule="fsm_compliance",
                        step_id=step.step_id,
                        message=f"Illegal FSM transition: {from_state.value} → {to_state.value}",
                    ))
        
        return errors
    
    def _check_layer_contracts(
        self, template: EpisodeTemplate
    ) -> list[TemplateValidationError]:
        """Check that layers only emit allowed packet types."""
        errors = []
        
        for step in template.steps:
            # Terminal steps don't emit packets
            if step.packet_type is None:
                continue
            
            contract = get_contract(step.owner_layer)
            if not contract.allows_emit(step.packet_type):
                errors.append(TemplateValidationError(
                    rule="layer_contract",
                    step_id=step.step_id,
                    message=f"Layer {step.owner_layer.value} cannot emit {step.packet_type.value}",
                ))
        
        return errors
    
    def _check_reachability(
        self, template: EpisodeTemplate
    ) -> list[TemplateValidationError]:
        """Check that all steps are reachable from entry_step."""
        errors = []
        
        # BFS from entry
        visited: set[str] = set()
        queue = [template.entry_step]
        
        while queue:
            step_id = queue.pop(0)
            if step_id in visited:
                continue
            visited.add(step_id)
            
            step = template.get_step(step_id)
            if step:
                queue.extend(step.next_steps)
        
        # Check for orphans
        all_ids = template.get_step_ids()
        orphans = all_ids - visited
        
        for orphan_id in orphans:
            errors.append(TemplateValidationError(
                rule="reachability",
                step_id=orphan_id,
                message=f"Step '{orphan_id}' not reachable from entry_step",
            ))
        
        return errors
    
    def _check_dead_ends(
        self, template: EpisodeTemplate
    ) -> list[TemplateValidationError]:
        """Check for non-exit steps with no next_steps (warnings only)."""
        warnings = []
        exit_ids = set(template.exit_steps)
        
        for step in template.steps:
            if step.step_id not in exit_ids and not step.next_steps:
                warnings.append(TemplateValidationError(
                    rule="dead_end",
                    step_id=step.step_id,
                    message=f"Non-exit step '{step.step_id}' has no next_steps",
                ))
        
        return warnings


# =============================================================================
# FACTORY
# =============================================================================

def create_template_validator() -> TemplateValidator:
    """Create a template validator instance."""
    return TemplateValidator()

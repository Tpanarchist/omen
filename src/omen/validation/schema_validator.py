"""
Schema Validator — Structural correctness for packets.

First validation gate. Ensures:
- All required MCP fields present
- Enum values valid
- Evidence completeness (refs OR absent_reason)
- Budget values non-negative
- Confidence in bounds

Spec: OMEN.md §9.2, §15.4
"""

from dataclasses import dataclass
from typing import Any

from omen.schemas import MCP, PacketHeader
from omen.schemas.packets import (
    ObservationPacket,
    BeliefUpdatePacket,
    DecisionPacket,
    VerificationPlanPacket,
    ToolAuthorizationToken,
    TaskDirectivePacket,
    TaskResultPacket,
    EscalationPacket,
    IntegrityAlertPacket,
)
from omen.vocabulary import PacketType, QualityTier, DecisionOutcome, TaskResultStatus


# Type alias for any packet
Packet = (
    ObservationPacket
    | BeliefUpdatePacket
    | DecisionPacket
    | VerificationPlanPacket
    | ToolAuthorizationToken
    | TaskDirectivePacket
    | TaskResultPacket
    | EscalationPacket
    | IntegrityAlertPacket
)


@dataclass
class ValidationResult:
    """Result of a validation check."""
    valid: bool
    errors: list[str]
    warnings: list[str]
    
    @classmethod
    def success(cls) -> "ValidationResult":
        return cls(valid=True, errors=[], warnings=[])
    
    @classmethod
    def failure(cls, errors: list[str], warnings: list[str] | None = None) -> "ValidationResult":
        return cls(valid=False, errors=errors, warnings=warnings or [])
    
    def merge(self, other: "ValidationResult") -> "ValidationResult":
        """Combine two results."""
        return ValidationResult(
            valid=self.valid and other.valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
        )


class SchemaValidator:
    """
    Validates packet structural correctness.
    
    This is the first validation gate. Packets that fail here
    should not proceed to FSM or invariant validation.
    
    Spec: OMEN.md §15.4 bullet 1
    """
    
    def validate(self, packet: Packet) -> ValidationResult:
        """
        Validate a packet's structure.
        
        Checks:
        1. Header completeness
        2. MCP completeness  
        3. Evidence completeness
        4. Payload-specific rules
        """
        result = ValidationResult.success()
        
        # Header validation
        result = result.merge(self._validate_header(packet.header))
        
        # MCP validation
        result = result.merge(self._validate_mcp(packet.mcp))
        
        # Payload-specific validation
        result = result.merge(self._validate_payload(packet))
        
        return result
    
    def _validate_header(self, header: PacketHeader) -> ValidationResult:
        """Validate packet header."""
        errors = []
        warnings = []
        
        # packet_id is required and must be non-empty
        if not header.packet_id:
            errors.append("Header missing packet_id")
        
        # packet_type must be valid enum
        if header.packet_type not in PacketType:
            errors.append(f"Invalid packet_type: {header.packet_type}")
        
        # correlation_id is required for episode tracking
        if not header.correlation_id:
            errors.append("Header missing correlation_id")
        
        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _validate_mcp(self, mcp: MCP) -> ValidationResult:
        """
        Validate MCP envelope completeness.
        
        Spec: OMEN.md §9.2, §15.4 bullet 1
        """
        errors = []
        warnings = []
        
        # Intent validation
        if not mcp.intent.summary:
            errors.append("MCP intent.summary is empty")
        
        # Stakes validation  
        # (enum validation handled by Pydantic, but we verify stakes_level is set)
        if not mcp.stakes.stakes_level:
            errors.append("MCP stakes.stakes_level is missing")
        
        # Quality validation
        if not mcp.quality.definition_of_done.text:
            warnings.append("MCP quality.definition_of_done.text is empty")
        
        # Budgets validation (non-negative handled by Pydantic)
        if mcp.budgets.token_budget == 0 and mcp.budgets.tool_call_budget == 0:
            warnings.append("Both token_budget and tool_call_budget are 0")
        
        # Epistemics validation
        if mcp.epistemics.confidence < 0 or mcp.epistemics.confidence > 1:
            errors.append(f"MCP epistemics.confidence out of bounds: {mcp.epistemics.confidence}")
        
        # Warn on confidence of 1.0 (epistemically suspicious per §8.1)
        if mcp.epistemics.confidence == 1.0:
            warnings.append("Confidence of 1.0 is rarely justified")
        
        # Evidence validation — rely on Pydantic MCP.validate_evidence_completeness
        # If packet construction succeeded, evidence XOR is already satisfied
        
        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _validate_payload(self, packet: Packet) -> ValidationResult:
        """Validate payload-specific rules."""
        if isinstance(packet, DecisionPacket):
            return self._validate_decision_payload(packet)
        elif isinstance(packet, TaskResultPacket):
            return self._validate_task_result_payload(packet)
        elif isinstance(packet, ToolAuthorizationToken):
            return self._validate_token_payload(packet)
        elif isinstance(packet, EscalationPacket):
            return self._validate_escalation_payload(packet)
        # Other packets have validation in Pydantic models
        return ValidationResult.success()
    
    def _validate_decision_payload(self, packet: DecisionPacket) -> ValidationResult:
        """
        Validate DecisionPacket payload rules.
        
        Spec: OMEN.md §10.3
        
        Note: VERIFY_FIRST and ESCALATE requirements are already enforced by
        Pydantic validators in DecisionPacket. This method handles additional
        semantic checks that Pydantic can't catch.
        """
        errors = []
        warnings = []
        payload = packet.payload
        
        # Load-bearing assumptions should be flagged
        if payload.load_bearing_assumptions:
            if not payload.assumptions:
                warnings.append("load_bearing_assumptions set but assumptions list is empty")
        
        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _validate_task_result_payload(self, packet: TaskResultPacket) -> ValidationResult:
        """
        Validate TaskResultPacket payload rules.
        
        Spec: OMEN.md §10.4
        
        Note: FAILURE status requirements are already enforced by Pydantic
        validators. This method handles additional semantic checks.
        """
        errors = []
        warnings = []
        payload = packet.payload
        
        # SUCCESS with no output is unusual
        if payload.status == TaskResultStatus.SUCCESS:
            if payload.output is None:
                warnings.append("SUCCESS result has no output")
        
        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _validate_token_payload(self, packet: ToolAuthorizationToken) -> ValidationResult:
        """
        Validate ToolAuthorizationToken payload rules.
        
        Spec: OMEN.md §10.4
        
        Note: Revoked token and scope requirements are already enforced by
        Pydantic validators. This method handles additional semantic checks.
        """
        errors = []
        warnings = []
        # All critical validations handled by Pydantic
        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _validate_escalation_payload(self, packet: EscalationPacket) -> ValidationResult:
        """
        Validate EscalationPacket payload rules.
        
        Spec: OMEN.md §8.2.6
        """
        errors = []
        warnings = []
        payload = packet.payload
        
        # Must have at least one option
        if not payload.options:
            errors.append("Escalation must present at least one option")
        
        # Should have evidence of what's known vs believed
        if not payload.what_we_know and not payload.what_we_believe:
            warnings.append("Escalation has neither what_we_know nor what_we_believe")
        
        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


# Convenience function
def validate_schema(packet: Packet) -> ValidationResult:
    """Validate a packet's structural correctness."""
    return SchemaValidator().validate(packet)

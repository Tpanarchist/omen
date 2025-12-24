"""
Tests for MCP envelope schema.

Validates structure matches OMEN.md §9.2 and §15.2.
"""

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from omen.schemas import (
    Intent,
    Stakes,
    DefinitionOfDone,
    Quality,
    RiskBudget,
    Budgets,
    Epistemics,
    EvidenceRef,
    Evidence,
    Routing,
    MCP,
)
from omen.vocabulary import (
    EpistemicStatus,
    FreshnessClass,
    EvidenceRefType,
    ImpactLevel,
    Irreversibility,
    UncertaintyLevel,
    Adversariality,
    StakesLevel,
    QualityTier,
    VerificationRequirement,
    TaskClass,
    ToolsState,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def valid_intent() -> dict:
    return {"summary": "Test intent", "scope": "test_scope"}


@pytest.fixture
def valid_stakes() -> dict:
    return {
        "impact": "MEDIUM",
        "irreversibility": "REVERSIBLE",
        "uncertainty": "HIGH",
        "adversariality": "CONTESTED",
        "stakes_level": "MEDIUM",
    }


@pytest.fixture
def valid_definition_of_done() -> dict:
    return {"text": "Task is complete", "checks": ["check1", "check2"]}


@pytest.fixture
def valid_quality(valid_definition_of_done) -> dict:
    return {
        "quality_tier": "PAR",
        "satisficing_mode": True,
        "definition_of_done": valid_definition_of_done,
        "verification_requirement": "VERIFY_ONE",
    }


@pytest.fixture
def valid_risk_budget() -> dict:
    return {"envelope": "low", "max_loss": "minimal"}


@pytest.fixture
def valid_budgets(valid_risk_budget) -> dict:
    return {
        "token_budget": 1000,
        "tool_call_budget": 5,
        "time_budget_seconds": 120,
        "risk_budget": valid_risk_budget,
    }


@pytest.fixture
def valid_epistemics() -> dict:
    return {
        "status": "OBSERVED",
        "confidence": 0.85,
        "calibration_note": "High confidence from direct observation",
        "freshness_class": "REALTIME",
        "stale_if_older_than_seconds": 300,
        "assumptions": [],
    }


@pytest.fixture
def valid_evidence_ref() -> dict:
    return {
        "ref_type": "tool_output",
        "ref_id": "obs_12345",
        "timestamp": "2025-01-15T10:30:00Z",
        "reliability_score": 0.95,
    }


@pytest.fixture
def valid_evidence_with_refs(valid_evidence_ref) -> dict:
    return {"evidence_refs": [valid_evidence_ref], "evidence_absent_reason": None}


@pytest.fixture
def valid_evidence_without_refs() -> dict:
    return {"evidence_refs": [], "evidence_absent_reason": "No observation performed yet"}


@pytest.fixture
def valid_routing() -> dict:
    return {"task_class": "VERIFY", "tools_state": "tools_ok"}


@pytest.fixture
def valid_mcp(
    valid_intent,
    valid_stakes,
    valid_quality,
    valid_budgets,
    valid_epistemics,
    valid_evidence_with_refs,
    valid_routing,
) -> dict:
    return {
        "intent": valid_intent,
        "stakes": valid_stakes,
        "quality": valid_quality,
        "budgets": valid_budgets,
        "epistemics": valid_epistemics,
        "evidence": valid_evidence_with_refs,
        "routing": valid_routing,
    }


# =============================================================================
# ATOMIC STRUCTURE TESTS
# =============================================================================

class TestIntent:
    """Tests for Intent structure."""

    def test_valid_intent_string_scope(self, valid_intent):
        intent = Intent(**valid_intent)
        assert intent.summary == "Test intent"
        assert intent.scope == "test_scope"

    def test_valid_intent_dict_scope(self):
        intent = Intent(summary="Test", scope={"domain": "intel", "target": "system_x"})
        assert isinstance(intent.scope, dict)

    def test_intent_requires_summary(self):
        with pytest.raises(ValidationError):
            Intent(scope="test")

    def test_intent_requires_scope(self):
        with pytest.raises(ValidationError):
            Intent(summary="Test")


class TestStakes:
    """Tests for Stakes structure."""

    def test_valid_stakes(self, valid_stakes):
        stakes = Stakes(**valid_stakes)
        assert stakes.impact == ImpactLevel.MEDIUM
        assert stakes.irreversibility == Irreversibility.REVERSIBLE
        assert stakes.uncertainty == UncertaintyLevel.HIGH
        assert stakes.adversariality == Adversariality.CONTESTED
        assert stakes.stakes_level == StakesLevel.MEDIUM

    def test_stakes_requires_all_fields(self):
        with pytest.raises(ValidationError):
            Stakes(impact="MEDIUM")  # Missing other fields

    def test_stakes_validates_enum_values(self):
        with pytest.raises(ValidationError):
            Stakes(
                impact="INVALID",
                irreversibility="REVERSIBLE",
                uncertainty="HIGH",
                adversariality="CONTESTED",
                stakes_level="MEDIUM",
            )


class TestQuality:
    """Tests for Quality structure."""

    def test_valid_quality(self, valid_quality):
        quality = Quality(**valid_quality)
        assert quality.quality_tier == QualityTier.PAR
        assert quality.satisficing_mode is True
        assert quality.verification_requirement == VerificationRequirement.VERIFY_ONE

    def test_quality_tiers_all_valid(self, valid_definition_of_done):
        for tier in ["SUBPAR", "PAR", "SUPERB"]:
            quality = Quality(
                quality_tier=tier,
                satisficing_mode=True,
                definition_of_done=valid_definition_of_done,
                verification_requirement="OPTIONAL",
            )
            assert quality.quality_tier.value == tier


class TestBudgets:
    """Tests for Budgets structure."""

    def test_valid_budgets(self, valid_budgets):
        budgets = Budgets(**valid_budgets)
        assert budgets.token_budget == 1000
        assert budgets.tool_call_budget == 5
        assert budgets.time_budget_seconds == 120

    def test_budgets_rejects_negative(self, valid_risk_budget):
        with pytest.raises(ValidationError):
            Budgets(
                token_budget=-1,
                tool_call_budget=5,
                time_budget_seconds=120,
                risk_budget=valid_risk_budget,
            )

    def test_risk_budget_accepts_numeric_max_loss(self):
        risk = RiskBudget(envelope="medium", max_loss=10000)
        assert risk.max_loss == 10000

    def test_risk_budget_accepts_string_max_loss(self):
        risk = RiskBudget(envelope="low", max_loss="minimal")
        assert risk.max_loss == "minimal"


class TestEpistemics:
    """Tests for Epistemics structure."""

    def test_valid_epistemics(self, valid_epistemics):
        epistemics = Epistemics(**valid_epistemics)
        assert epistemics.status == EpistemicStatus.OBSERVED
        assert epistemics.confidence == 0.85

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            Epistemics(
                status="OBSERVED",
                confidence=1.5,  # Invalid: > 1.0
                calibration_note="Test",
                freshness_class="REALTIME",
                stale_if_older_than_seconds=300,
                assumptions=[],
            )

    def test_all_epistemic_statuses_valid(self):
        for status in EpistemicStatus:
            epistemics = Epistemics(
                status=status.value,
                confidence=0.5,
                calibration_note="Test",
                freshness_class="OPERATIONAL",
                stale_if_older_than_seconds=600,
                assumptions=[],
            )
            assert epistemics.status == status


class TestEvidence:
    """Tests for Evidence structure."""

    def test_valid_evidence_with_refs(self, valid_evidence_with_refs):
        evidence = Evidence(**valid_evidence_with_refs)
        assert len(evidence.evidence_refs) == 1

    def test_valid_evidence_with_absent_reason(self, valid_evidence_without_refs):
        evidence = Evidence(**valid_evidence_without_refs)
        assert evidence.evidence_refs == []
        assert evidence.evidence_absent_reason is not None

    def test_evidence_ref_timestamp_parsing(self):
        ref = EvidenceRef(
            ref_type="tool_output",
            ref_id="test_123",
            timestamp="2025-01-15T10:30:00Z",
        )
        assert ref.timestamp.year == 2025

    def test_evidence_ref_reliability_optional(self):
        ref = EvidenceRef(
            ref_type="user_observation",
            ref_id="obs_456",
            timestamp=datetime.now(timezone.utc),
        )
        assert ref.reliability_score is None


class TestRouting:
    """Tests for Routing structure."""

    def test_valid_routing(self, valid_routing):
        routing = Routing(**valid_routing)
        assert routing.task_class == TaskClass.VERIFY
        assert routing.tools_state == ToolsState.TOOLS_OK

    def test_all_task_classes_valid(self):
        for task_class in TaskClass:
            routing = Routing(task_class=task_class.value, tools_state="tools_ok")
            assert routing.task_class == task_class

    def test_all_tools_states_valid(self):
        for tools_state in ToolsState:
            routing = Routing(task_class="FIND", tools_state=tools_state.value)
            assert routing.tools_state == tools_state


# =============================================================================
# MCP ENVELOPE TESTS
# =============================================================================

class TestMCP:
    """Tests for complete MCP envelope."""

    def test_valid_mcp(self, valid_mcp):
        mcp = MCP(**valid_mcp)
        assert mcp.intent.summary is not None
        assert mcp.stakes.impact == ImpactLevel.MEDIUM
        assert mcp.quality.quality_tier == QualityTier.PAR

    def test_mcp_requires_all_sections(self, valid_intent):
        with pytest.raises(ValidationError):
            MCP(intent=valid_intent)  # Missing other sections

    def test_mcp_evidence_must_have_refs_or_reason(
        self,
        valid_intent,
        valid_stakes,
        valid_quality,
        valid_budgets,
        valid_epistemics,
        valid_routing,
    ):
        """Evidence with neither refs nor reason should fail."""
        with pytest.raises(ValidationError) as exc_info:
            MCP(
                intent=valid_intent,
                stakes=valid_stakes,
                quality=valid_quality,
                budgets=valid_budgets,
                epistemics=valid_epistemics,
                evidence={"evidence_refs": [], "evidence_absent_reason": None},
                routing=valid_routing,
            )
        assert "evidence_refs or evidence_absent_reason" in str(exc_info.value)

    def test_mcp_serializes_to_json(self, valid_mcp):
        mcp = MCP(**valid_mcp)
        json_str = mcp.model_dump_json()
        parsed = json.loads(json_str)
        assert "intent" in parsed
        assert "stakes" in parsed
        assert "quality" in parsed
        assert "budgets" in parsed
        assert "epistemics" in parsed
        assert "evidence" in parsed
        assert "routing" in parsed

    def test_mcp_roundtrip(self, valid_mcp):
        """MCP can be serialized and deserialized."""
        mcp1 = MCP(**valid_mcp)
        json_str = mcp1.model_dump_json()
        mcp2 = MCP.model_validate_json(json_str)
        assert mcp1 == mcp2


class TestMCPSpecExample:
    """Test against the canonical example from OMEN.md §15.2."""

    def test_spec_example_validates(self):
        """The exact MCP from spec §15.2 should validate."""
        spec_mcp = {
            "intent": {
                "summary": "Decide whether to verify intel before acting",
                "scope": "intel_update",
            },
            "stakes": {
                "impact": "MEDIUM",
                "irreversibility": "REVERSIBLE",
                "uncertainty": "HIGH",
                "adversariality": "CONTESTED",
                "stakes_level": "MEDIUM",
            },
            "quality": {
                "quality_tier": "PAR",
                "satisficing_mode": True,
                "verification_requirement": "VERIFY_ONE",
                "definition_of_done": {
                    "text": "Have at least one fresh observation for the key unknown",
                    "checks": ["fresh evidence collected"],
                },
            },
            "budgets": {
                "token_budget": 900,
                "tool_call_budget": 2,
                "time_budget_seconds": 90,
                "risk_budget": {"envelope": "low", "max_loss": "small"},
            },
            "epistemics": {
                "status": "HYPOTHESIZED",
                "confidence": 0.45,
                "calibration_note": "Uncertainty high; no fresh observation yet",
                "freshness_class": "OPERATIONAL",
                "stale_if_older_than_seconds": 1800,
                "assumptions": ["Local threat level is low enough to proceed"],
            },
            "evidence": {
                "evidence_refs": [],
                "evidence_absent_reason": "No tool read executed yet in this episode",
            },
            "routing": {"task_class": "VERIFY", "tools_state": "tools_ok"},
        }

        mcp = MCP(**spec_mcp)
        
        # Verify key fields match spec
        assert mcp.intent.summary == "Decide whether to verify intel before acting"
        assert mcp.stakes.stakes_level == StakesLevel.MEDIUM
        assert mcp.quality.quality_tier == QualityTier.PAR
        assert mcp.epistemics.status == EpistemicStatus.HYPOTHESIZED
        assert mcp.epistemics.confidence == 0.45
        assert mcp.routing.task_class == TaskClass.VERIFY


class TestMCPJsonSchema:
    """Tests for JSON Schema generation."""

    def test_generates_json_schema(self):
        """MCP can generate a JSON Schema."""
        schema = MCP.model_json_schema()
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "intent" in schema["properties"]
        assert "stakes" in schema["properties"]

    def test_json_schema_has_definitions(self):
        """JSON Schema includes nested type definitions."""
        schema = MCP.model_json_schema()
        assert "$defs" in schema
        # Should have definitions for nested models
        defs = schema["$defs"]
        assert "Intent" in defs
        assert "Stakes" in defs
        assert "Quality" in defs

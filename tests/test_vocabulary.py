"""
Tests for vocabulary enums.

Verifies all enums match the specification exactly.
"""

import pytest
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
    ToolSafety,
    PacketType,
    LayerSource,
    FSMState,
    DecisionOutcome,
    TaskResultStatus,
)


class TestEpistemicPolicy:
    """Tests for E-POL enums (OMEN.md §8.1)."""

    def test_epistemic_status_values(self):
        """EpistemicStatus has exactly 6 values per spec."""
        expected = {"OBSERVED", "DERIVED", "REMEMBERED", "INFERRED", "HYPOTHESIZED", "UNKNOWN"}
        actual = {e.value for e in EpistemicStatus}
        assert actual == expected

    def test_freshness_class_values(self):
        """FreshnessClass has exactly 4 values per spec."""
        expected = {"REALTIME", "OPERATIONAL", "STRATEGIC", "ARCHIVAL"}
        actual = {e.value for e in FreshnessClass}
        assert actual == expected

    def test_evidence_ref_type_values(self):
        """EvidenceRefType has exactly 4 values per spec."""
        expected = {"tool_output", "user_observation", "memory_item", "derived_calc"}
        actual = {e.value for e in EvidenceRefType}
        assert actual == expected


class TestQualityPolicy:
    """Tests for Q-POL enums (OMEN.md §8.2)."""

    def test_impact_level_values(self):
        """ImpactLevel has exactly 4 values per spec."""
        expected = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        actual = {e.value for e in ImpactLevel}
        assert actual == expected

    def test_irreversibility_values(self):
        """Irreversibility has exactly 3 values per spec."""
        expected = {"REVERSIBLE", "PARTIAL", "IRREVERSIBLE"}
        actual = {e.value for e in Irreversibility}
        assert actual == expected

    def test_uncertainty_level_values(self):
        """UncertaintyLevel has exactly 3 values per spec."""
        expected = {"LOW", "MEDIUM", "HIGH"}
        actual = {e.value for e in UncertaintyLevel}
        assert actual == expected

    def test_adversariality_values(self):
        """Adversariality has exactly 3 values per spec."""
        expected = {"BENIGN", "CONTESTED", "HOSTILE"}
        actual = {e.value for e in Adversariality}
        assert actual == expected

    def test_stakes_level_values(self):
        """StakesLevel has exactly 4 values per spec."""
        expected = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        actual = {e.value for e in StakesLevel}
        assert actual == expected

    def test_quality_tier_values(self):
        """QualityTier has exactly 3 values per spec."""
        expected = {"SUBPAR", "PAR", "SUPERB"}
        actual = {e.value for e in QualityTier}
        assert actual == expected

    def test_verification_requirement_values(self):
        """VerificationRequirement has exactly 3 values per spec."""
        expected = {"OPTIONAL", "VERIFY_ONE", "VERIFY_ALL"}
        actual = {e.value for e in VerificationRequirement}
        assert actual == expected


class TestComputePolicy:
    """Tests for C-POL enums (OMEN.md §8.3)."""

    def test_task_class_values(self):
        """TaskClass has exactly 6 values per spec."""
        expected = {"FIND", "LOOKUP", "SEARCH", "CREATE", "VERIFY", "COMPILE"}
        actual = {e.value for e in TaskClass}
        assert actual == expected

    def test_tools_state_values(self):
        """ToolsState has exactly 3 values per spec."""
        expected = {"tools_ok", "tools_partial", "tools_down"}
        actual = {e.value for e in ToolsState}
        assert actual == expected

    def test_tool_safety_values(self):
        """ToolSafety has exactly 3 values per spec."""
        expected = {"READ", "WRITE", "MIXED"}
        actual = {e.value for e in ToolSafety}
        assert actual == expected


class TestPacketModel:
    """Tests for packet-related enums (OMEN.md §9)."""

    def test_packet_type_values(self):
        """PacketType has exactly 9 values per spec."""
        expected = {
            "ObservationPacket",
            "BeliefUpdatePacket",
            "DecisionPacket",
            "VerificationPlanPacket",
            "ToolAuthorizationToken",
            "TaskDirectivePacket",
            "TaskResultPacket",
            "EscalationPacket",
            "IntegrityAlertPacket",
        }
        actual = {e.value for e in PacketType}
        assert actual == expected

    def test_layer_source_values(self):
        """LayerSource has exactly 7 values per spec (6 layers + Integrity)."""
        expected = {"1", "2", "3", "4", "5", "6", "Integrity"}
        actual = {e.value for e in LayerSource}
        assert actual == expected


class TestFSM:
    """Tests for FSM enums (OMEN.md §10)."""

    def test_fsm_state_values(self):
        """FSMState has exactly 10 values per spec."""
        expected = {
            "S0_IDLE",
            "S1_SENSE",
            "S2_MODEL",
            "S3_DECIDE",
            "S4_VERIFY",
            "S5_AUTHORIZE",
            "S6_EXECUTE",
            "S7_REVIEW",
            "S8_ESCALATED",
            "S9_SAFEMODE",
        }
        actual = {e.value for e in FSMState}
        assert actual == expected

    def test_fsm_state_count(self):
        """FSM has exactly 10 states."""
        assert len(FSMState) == 10


class TestDecisions:
    """Tests for decision-related enums (OMEN.md §15.2)."""

    def test_decision_outcome_values(self):
        """DecisionOutcome has exactly 4 values per spec."""
        expected = {"ACT", "VERIFY_FIRST", "ESCALATE", "DEFER"}
        actual = {e.value for e in DecisionOutcome}
        assert actual == expected

    def test_task_result_status_values(self):
        """TaskResultStatus has exactly 3 values per spec."""
        expected = {"SUCCESS", "FAILURE", "CANCELLED"}
        actual = {e.value for e in TaskResultStatus}
        assert actual == expected


class TestEnumUsability:
    """Tests that enums are usable as expected."""

    def test_string_enum_serialization(self):
        """String enums serialize to their values."""
        assert str(EpistemicStatus.OBSERVED) == "EpistemicStatus.OBSERVED"
        assert EpistemicStatus.OBSERVED.value == "OBSERVED"

    def test_enum_from_value(self):
        """Enums can be constructed from string values."""
        assert EpistemicStatus("OBSERVED") == EpistemicStatus.OBSERVED
        assert QualityTier("SUPERB") == QualityTier.SUPERB
        assert FSMState("S3_DECIDE") == FSMState.S3_DECIDE

    def test_enum_comparison(self):
        """Enums compare correctly."""
        assert EpistemicStatus.OBSERVED == EpistemicStatus.OBSERVED
        assert EpistemicStatus.OBSERVED != EpistemicStatus.INFERRED

    def test_enum_in_dict(self):
        """Enums work as dictionary keys."""
        mapping = {EpistemicStatus.OBSERVED: "high", EpistemicStatus.INFERRED: "low"}
        assert mapping[EpistemicStatus.OBSERVED] == "high"

    def test_enum_json_compatible(self):
        """Enum values are JSON-serializable strings."""
        import json
        data = {"status": EpistemicStatus.OBSERVED.value}
        serialized = json.dumps(data)
        assert '"OBSERVED"' in serialized

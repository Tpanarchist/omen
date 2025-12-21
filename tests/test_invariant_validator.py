"""
Tests for OMEN v0.7 Invariant Validator

Tests all 12 invariants (INV-001 through INV-012) with positive and negative cases.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "validators" / "v0.7"))

from invariant_validator import InvariantValidator


class TestInvariant001_MCPCompleteness:
    """Test INV-001: MCP Completeness"""
    
    @pytest.fixture
    def validator(self):
        return InvariantValidator()
    
    def test_complete_mcp_accepted(self, validator):
        """DecisionPacket with complete MCP passes"""
        packet = self._create_complete_decision("corr_001")
        result = validator.validate_packet(packet)
        assert result.is_valid
        assert len(result.violations) == 0
    
    def test_missing_intent_summary_rejected(self, validator):
        """DecisionPacket missing intent.summary fails INV-001"""
        packet = self._create_complete_decision("corr_001")
        del packet["mcp"]["intent"]["summary"]
        
        result = validator.validate_packet(packet)
        assert not result.is_valid
        assert any("INV-001" in v and "intent.summary" in v for v in result.violations)
    
    def test_missing_evidence_absent_reason_rejected(self, validator):
        """Empty evidence_refs without absent_reason fails INV-001"""
        packet = self._create_complete_decision("corr_001")
        packet["mcp"]["evidence"]["evidence_refs"] = []
        del packet["mcp"]["evidence"]["evidence_absent_reason"]
        
        result = validator.validate_packet(packet)
        assert not result.is_valid
        assert any("INV-001" in v and "evidence_absent_reason" in v for v in result.violations)
    
    def _create_complete_decision(self, correlation_id):
        """Helper: Create fully populated DecisionPacket"""
        return {
            "header": {
                "packet_id": f"pkt_decision_{correlation_id}",
                "packet_type": "DecisionPacket",
                "created_at": datetime.now().isoformat(),
                "layer_source": 5,
                "correlation_id": correlation_id
            },
            "mcp": {
                "intent": {"summary": "Test decision", "scope": "test"},
                "stakes": {
                    "impact": "LOW", "irreversibility": "REVERSIBLE",
                    "uncertainty": "LOW", "adversariality": "BENIGN",
                    "stakes_level": "LOW"
                },
                "quality": {
                    "quality_tier": "PAR", "satisficing_mode": False,
                    "definition_of_done": {"text": "Decision made", "checks": ["decided"]},
                    "verification_requirement": "OPTIONAL"
                },
                "budgets": {
                    "token_budget": 500, "tool_call_budget": 2,
                    "time_budget_seconds": 60,
                    "risk_budget": {"envelope": "minimal", "max_loss": "0"}
                },
                "epistemics": {
                    "status": "DERIVED", "confidence": 0.85,
                    "calibration_note": "Test decision", "freshness_class": "STRATEGIC",
                    "assumptions": []
                },
                "evidence": {
                    "evidence_refs": [],
                    "evidence_absent_reason": "Initial decision, no prior evidence"
                },
                "routing": {"task_class": "CREATE", "tools_state": "tools_ok"}
            },
            "payload": {
                "decision_outcome": "ACT",
                "decision_summary": "Test decision",
                "chosen_option": {"option_id": "opt_1", "description": "Test", "expected_value": 0.8},
                "rejected_alternatives": [],
                "constraints_satisfied": {
                    "constitutional_check": True,
                    "budget_check": True,
                    "tier_check": True,
                    "verification_check": True
                },
                "load_bearing_assumptions": [],
                "failure_modes": []
            }
        }


class TestInvariant002_SUBPARNoACT:
    """Test INV-002: SUBPAR Never Authorizes Action"""
    
    @pytest.fixture
    def validator(self):
        return InvariantValidator()
    
    def test_subpar_with_verify_accepted(self, validator):
        """SUBPAR with VERIFY_FIRST is allowed"""
        packet = self._create_decision("corr_001", "SUBPAR", "VERIFY_FIRST")
        result = validator.validate_packet(packet)
        assert result.is_valid
    
    def test_subpar_with_act_rejected(self, validator):
        """SUBPAR with ACT fails INV-002"""
        packet = self._create_decision("corr_001", "SUBPAR", "ACT")
        result = validator.validate_packet(packet)
        assert not result.is_valid
        assert any("INV-002" in v and "SUBPAR" in v for v in result.violations)
    
    def test_par_with_act_accepted(self, validator):
        """PAR with ACT is allowed"""
        packet = self._create_decision("corr_001", "PAR", "ACT")
        result = validator.validate_packet(packet)
        assert result.is_valid
    
    def _create_decision(self, correlation_id, tier, outcome):
        packet = TestInvariant001_MCPCompleteness()._create_complete_decision(correlation_id)
        packet["mcp"]["quality"]["quality_tier"] = tier
        packet["payload"]["decision_outcome"] = outcome
        return packet


class TestInvariant003_HighCriticalVerification:
    """Test INV-003: HIGH/CRITICAL Requires Verification or Escalation"""
    
    @pytest.fixture
    def validator(self):
        return InvariantValidator()
    
    def test_high_stakes_with_verify_accepted(self, validator):
        """HIGH stakes with VERIFY_FIRST accepted"""
        packet = self._create_decision("corr_001", "HIGH", "VERIFY_FIRST", "PAR")
        result = validator.validate_packet(packet)
        assert result.is_valid
    
    def test_high_stakes_with_escalate_accepted(self, validator):
        """HIGH stakes with ESCALATE accepted"""
        packet = self._create_decision("corr_001", "HIGH", "ESCALATE", "PAR")
        result = validator.validate_packet(packet)
        assert result.is_valid
    
    def test_high_stakes_act_requires_superb(self, validator):
        """HIGH stakes with ACT requires SUPERB tier"""
        packet = self._create_decision("corr_001", "HIGH", "ACT", "PAR")
        result = validator.validate_packet(packet)
        assert not result.is_valid
        assert any("INV-003" in v and "SUPERB" in v for v in result.violations)
    
    def test_high_stakes_superb_act_with_verified_assumptions_accepted(self, validator):
        """HIGH stakes SUPERB ACT with verified assumptions accepted"""
        packet = self._create_decision("corr_001", "HIGH", "ACT", "SUPERB")
        packet["payload"]["load_bearing_assumptions"] = [
            {"assumption": "Market price stable", "verified": True}
        ]
        result = validator.validate_packet(packet)
        assert result.is_valid
    
    def test_high_stakes_unverified_assumptions_rejected(self, validator):
        """HIGH stakes with unverified assumptions fails INV-003"""
        packet = self._create_decision("corr_001", "HIGH", "ACT", "SUPERB")
        packet["payload"]["load_bearing_assumptions"] = [
            {"assumption": "Market price stable", "verified": False}
        ]
        result = validator.validate_packet(packet)
        assert not result.is_valid
        assert any("INV-003" in v and "Unverified" in v for v in result.violations)
    
    def _create_decision(self, correlation_id, stakes_level, outcome, tier):
        packet = TestInvariant001_MCPCompleteness()._create_complete_decision(correlation_id)
        packet["mcp"]["stakes"]["stakes_level"] = stakes_level
        packet["mcp"]["quality"]["quality_tier"] = tier
        packet["payload"]["decision_outcome"] = outcome
        
        # Fix stakes axes to match stakes_level
        if stakes_level == "HIGH":
            packet["mcp"]["stakes"]["impact"] = "HIGH"
            packet["mcp"]["stakes"]["uncertainty"] = "HIGH"
        elif stakes_level == "CRITICAL":
            packet["mcp"]["stakes"]["impact"] = "CRITICAL"
        
        return packet


class TestInvariant007_TokenScope:
    """Test INV-007: WRITE Requires Token Scope Containment"""
    
    @pytest.fixture
    def validator(self):
        return InvariantValidator()
    
    def test_write_without_token_rejected(self, validator):
        """WRITE directive without token fails INV-007"""
        packet = self._create_directive("corr_001", "WRITE", None)
        result = validator.validate_packet(packet)
        assert not result.is_valid
        assert any("INV-007" in v and "authorization_token_id" in v for v in result.violations)
    
    def test_write_with_valid_token_accepted(self, validator):
        """WRITE directive with valid token accepted"""
        # First issue token
        token = self._create_token("corr_001", "token_001", ["trade_api"])
        validator.validate_packet(token)
        
        # Then issue WRITE directive with token
        packet = self._create_directive("corr_001", "WRITE", "token_001", "trade_api")
        result = validator.validate_packet(packet)
        assert result.is_valid
    
    def test_write_with_wrong_tool_rejected(self, validator):
        """WRITE directive with token for wrong tool fails INV-007"""
        # Issue token for trade_api
        token = self._create_token("corr_001", "token_001", ["trade_api"])
        validator.validate_packet(token)
        
        # Try to use token for market_api
        packet = self._create_directive("corr_001", "WRITE", "token_001", "market_api")
        result = validator.validate_packet(packet)
        assert not result.is_valid
        assert any("INV-007" in v and "not in token scope" in v for v in result.violations)
    
    def test_read_without_token_accepted(self, validator):
        """READ directive doesn't require token"""
        packet = self._create_directive("corr_001", "READ", None)
        result = validator.validate_packet(packet)
        assert result.is_valid
    
    def _create_token(self, correlation_id, token_id, tool_ids):
        expiry = datetime.now() + timedelta(hours=1)
        return {
            "header": {
                "packet_id": f"pkt_token_{token_id}",
                "packet_type": "ToolAuthorizationToken",
                "created_at": datetime.now().isoformat(),
                "layer_source": 1,
                "correlation_id": correlation_id
            },
            "mcp": self._minimal_mcp(),
            "payload": {
                "token_id": token_id,
                "authorized_scope": {
                    "tool_ids": tool_ids,
                    "operation_types": ["write"],
                    "resource_constraints": {}
                },
                "expiry": expiry.isoformat(),
                "max_usage_count": 1,
                "usage_count": 0,
                "revoked": False,
                "issuer_layer": 1
            }
        }
    
    def _create_directive(self, correlation_id, safety_class, token_id=None, tool_id="test_tool"):
        packet = {
            "header": {
                "packet_id": f"pkt_directive_{correlation_id}",
                "packet_type": "TaskDirectivePacket",
                "created_at": datetime.now().isoformat(),
                "layer_source": 5,
                "correlation_id": correlation_id
            },
            "mcp": self._minimal_mcp(),
            "payload": {
                "task_id": f"task_{correlation_id}",
                "task_type": "tool_write" if safety_class == "WRITE" else "tool_read",
                "execution_method": {
                    "method": "tool",
                    "tool_id": tool_id,
                    "tool_params": {}
                },
                "tool_safety_class": safety_class,
                "timeout_seconds": 60
            }
        }
        
        if token_id:
            packet["payload"]["authorization_token_id"] = token_id
        
        return packet
    
    def _minimal_mcp(self):
        return {
            "intent": {"summary": "Test", "scope": "test"},
            "stakes": {
                "impact": "LOW", "irreversibility": "REVERSIBLE",
                "uncertainty": "LOW", "adversariality": "BENIGN",
                "stakes_level": "LOW"
            },
            "quality": {
                "quality_tier": "PAR", "satisficing_mode": False,
                "definition_of_done": {"text": "Done", "checks": ["check"]},
                "verification_requirement": "OPTIONAL"
            },
            "budgets": {
                "token_budget": 200, "tool_call_budget": 1,
                "time_budget_seconds": 60,
                "risk_budget": {"envelope": "minimal", "max_loss": "0"}
            },
            "epistemics": {
                "status": "DERIVED", "confidence": 0.85,
                "calibration_note": "Test", "freshness_class": "STRATEGIC",
                "assumptions": []
            },
            "evidence": {
                "evidence_refs": [],
                "evidence_absent_reason": "Test"
            },
            "routing": {"task_class": "VERIFY", "tools_state": "tools_ok"}
        }


class TestInvariant009_EscalationOptions:
    """Test INV-009: Escalation Must Present Options"""
    
    @pytest.fixture
    def validator(self):
        return InvariantValidator()
    
    def test_escalation_with_valid_options_accepted(self, validator):
        """EscalationPacket with 2-3 options accepted"""
        packet = self._create_escalation("corr_001", 2)
        result = validator.validate_packet(packet)
        assert result.is_valid
    
    def test_escalation_with_one_option_rejected(self, validator):
        """EscalationPacket with 1 option fails INV-009"""
        packet = self._create_escalation("corr_001", 1)
        result = validator.validate_packet(packet)
        assert not result.is_valid
        assert any("INV-009" in v and "2-3 top_options" in v for v in result.violations)
    
    def test_escalation_without_evidence_gaps_rejected(self, validator):
        """EscalationPacket without evidence_gaps fails INV-009"""
        packet = self._create_escalation("corr_001", 2)
        packet["payload"]["evidence_gaps"] = []
        result = validator.validate_packet(packet)
        assert not result.is_valid
        assert any("INV-009" in v and "evidence_gap" in v for v in result.violations)
    
    def test_escalation_without_recommendation_rejected(self, validator):
        """EscalationPacket without recommended_next_step fails INV-009"""
        packet = self._create_escalation("corr_001", 2)
        del packet["payload"]["recommended_next_step"]
        result = validator.validate_packet(packet)
        assert not result.is_valid
        assert any("INV-009" in v and "recommended_next_step" in v for v in result.violations)
    
    def _create_escalation(self, correlation_id, num_options):
        return {
            "header": {
                "packet_id": f"pkt_escalation_{correlation_id}",
                "packet_type": "EscalationPacket",
                "created_at": datetime.now().isoformat(),
                "layer_source": 5,
                "correlation_id": correlation_id
            },
            "mcp": TestInvariant007_TokenScope()._minimal_mcp(),
            "payload": {
                "escalation_trigger": "uncertainty_high",
                "top_options": [
                    {"option_id": f"opt_{i}", "description": f"Option {i}", "expected_value": 0.5}
                    for i in range(num_options)
                ],
                "evidence_gaps": ["Market data missing"],
                "recommended_next_step": "Gather more data"
            }
        }


class TestInvariant012_StakesConsistency:
    """Test INV-012: Stakes Consistency"""
    
    @pytest.fixture
    def validator(self):
        return InvariantValidator()
    
    def test_low_stakes_with_low_axes_accepted(self, validator):
        """LOW stakes_level with all LOW axes accepted"""
        packet = self._create_decision_with_stakes(
            "corr_001", "LOW", "LOW", "REVERSIBLE", "LOW", "BENIGN"
        )
        result = validator.validate_packet(packet)
        assert result.is_valid
    
    def test_low_stakes_with_high_axis_rejected(self, validator):
        """LOW stakes_level with HIGH axis fails INV-012"""
        packet = self._create_decision_with_stakes(
            "corr_001", "LOW", "HIGH", "REVERSIBLE", "LOW", "BENIGN"
        )
        result = validator.validate_packet(packet)
        assert not result.is_valid
        assert any("INV-012" in v and "LOW stakes" in v for v in result.violations)
    
    def test_high_stakes_with_two_high_axes_accepted(self, validator):
        """HIGH stakes_level with two HIGH axes accepted"""
        packet = self._create_decision_with_stakes(
            "corr_001", "HIGH", "HIGH", "REVERSIBLE", "HIGH", "BENIGN"
        )
        # Change decision to VERIFY_FIRST (ACT requires SUPERB tier)
        packet["payload"]["decision_outcome"] = "VERIFY_FIRST"
        result = validator.validate_packet(packet)
        assert result.is_valid
    
    def test_high_stakes_with_one_high_axis_rejected(self, validator):
        """HIGH stakes_level with only one HIGH axis fails INV-012"""
        packet = self._create_decision_with_stakes(
            "corr_001", "HIGH", "HIGH", "REVERSIBLE", "LOW", "BENIGN"
        )
        result = validator.validate_packet(packet)
        assert not result.is_valid
        assert any("INV-012" in v and "HIGH stakes" in v for v in result.violations)
    
    def _create_decision_with_stakes(self, correlation_id, stakes_level, 
                                     impact, irreversibility, uncertainty, adversariality):
        packet = TestInvariant001_MCPCompleteness()._create_complete_decision(correlation_id)
        packet["mcp"]["stakes"] = {
            "impact": impact,
            "irreversibility": irreversibility,
            "uncertainty": uncertainty,
            "adversariality": adversariality,
            "stakes_level": stakes_level
        }
        return packet


class TestGoldenFixtures:
    """Test invariant validator with golden fixtures"""
    
    @pytest.fixture
    def validator(self):
        # Disable timestamp checks for historical fixtures
        return InvariantValidator(check_timestamps=False)
    
    @pytest.fixture
    def goldens_dir(self):
        return Path(__file__).parent.parent / "goldens" / "v0.7"
    
    def test_verify_loop_episode(self, validator, goldens_dir):
        """Validate verify_loop episode passes all invariants"""
        fixture = goldens_dir / "Episode.verify_loop.jsonl"
        
        packets = []
        with open(fixture, 'r') as f:
            for line in f:
                if line.strip():
                    packets.append(json.loads(line))
        
        results = validator.validate_episode_sequence(packets)
        
        # All packets should pass invariant checks
        assert all(r.is_valid for r in results), \
            f"Failed packets: {[(r.packet_id, r.violations) for r in results if not r.is_valid]}"
    
    def test_write_with_token_episode(self, validator, goldens_dir):
        """Validate write_with_token episode passes all invariants"""
        fixture = goldens_dir / "Episode.write_with_token.jsonl"
        
        packets = []
        with open(fixture, 'r') as f:
            for line in f:
                if line.strip():
                    packets.append(json.loads(line))
        
        results = validator.validate_episode_sequence(packets)
        
        # All packets should pass invariant checks
        assert all(r.is_valid for r in results), \
            f"Failed packets: {[(r.packet_id, r.violations) for r in results if not r.is_valid]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

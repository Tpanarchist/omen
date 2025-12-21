"""
Tests for OMEN v0.7 FSM Validator

Tests FSM state transitions, enforcement rules, and episode tracking.
"""

import json
import pytest
from pathlib import Path
from datetime import datetime, timedelta

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "validators" / "v0.7"))

from fsm_validator import FSMValidator, FSMState


@pytest.fixture
def validator():
    """Create fresh FSM validator for each test"""
    return FSMValidator()


@pytest.fixture
def goldens_dir():
    """Path to golden fixtures directory"""
    return Path(__file__).parent.parent / "goldens" / "v0.7"


class TestFSMBasicTransitions:
    """Test basic FSM state transitions"""
    
    def test_idle_to_sense(self, validator):
        """Initial observation moves from IDLE to SENSE"""
        packet = self._create_observation("corr_001")
        
        result = validator.validate_packet(packet)
        
        assert result.is_valid
        assert result.from_state == FSMState.S0_IDLE
        assert result.to_state == FSMState.S1_SENSE
    
    def test_sense_to_model(self, validator):
        """BeliefUpdate after observation moves to MODEL"""
        # First: observation
        obs = self._create_observation("corr_001")
        validator.validate_packet(obs)
        
        # Then: belief update
        belief = self._create_belief_update("corr_001")
        result = validator.validate_packet(belief)
        
        assert result.is_valid
        assert result.from_state == FSMState.S1_SENSE
        assert result.to_state == FSMState.S2_MODEL
    
    def test_model_to_decide(self, validator):
        """Decision after belief update moves to DECIDE"""
        # Setup: obs → belief
        validator.validate_packet(self._create_observation("corr_001"))
        validator.validate_packet(self._create_belief_update("corr_001"))
        
        # Then: decision
        decision = self._create_decision("corr_001", "ACT")
        result = validator.validate_packet(decision)
        
        assert result.is_valid
        assert result.from_state == FSMState.S2_MODEL
        assert result.to_state == FSMState.S3_DECIDE
    
    def test_invalid_transition_rejected(self, validator):
        """Invalid transition (e.g., IDLE → Decision) rejected"""
        decision = self._create_decision("corr_001", "ACT")
        result = validator.validate_packet(decision)
        
        assert not result.is_valid
        assert "Invalid transition" in result.errors[0]
        assert result.from_state == FSMState.S0_IDLE
    
    # Helper methods
    def _create_observation(self, correlation_id, packet_id="pkt_obs_001"):
        return {
            "header": {
                "packet_id": packet_id,
                "packet_type": "ObservationPacket",
                "created_at": datetime.now().isoformat(),
                "layer_source": 6,
                "correlation_id": correlation_id
            },
            "mcp": self._minimal_mcp(),
            "payload": {
                "observation_type": "tool_output",
                "data": {"test": "data"},
                "source_tool": "test_tool",
                "reliability_metadata": {
                    "tool_success": True,
                    "latency_ms": 100,
                    "partial_result": False
                }
            }
        }
    
    def _create_belief_update(self, correlation_id, packet_id="pkt_belief_001"):
        return {
            "header": {
                "packet_id": packet_id,
                "packet_type": "BeliefUpdatePacket",
                "created_at": datetime.now().isoformat(),
                "layer_source": 5,
                "correlation_id": correlation_id
            },
            "mcp": self._minimal_mcp(),
            "payload": {
                "update_type": "new_belief",
                "belief_changes": [{
                    "domain": "test",
                    "key": "status",
                    "new_value": "active",
                    "prior_value": "unknown",
                    "epistemic_upgrade": True
                }],
                "evidence_integration": ["pkt_obs_001"]
            }
        }
    
    def _create_decision(self, correlation_id, outcome, packet_id="pkt_dec_001"):
        return {
            "header": {
                "packet_id": packet_id,
                "packet_type": "DecisionPacket",
                "created_at": datetime.now().isoformat(),
                "layer_source": 5,
                "correlation_id": correlation_id
            },
            "mcp": self._minimal_mcp(),
            "payload": {
                "decision_outcome": outcome,
                "decision_summary": f"Test decision: {outcome}",
                "chosen_option": {
                    "option_id": "opt_1",
                    "description": "Test option",
                    "expected_value": 0.8,
                    "risk_profile": "low"
                },
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
    
    def _minimal_mcp(self):
        return {
            "intent": {"summary": "Test", "scope": "test"},
            "stakes": {
                "impact": "LOW",
                "irreversibility": "REVERSIBLE",
                "uncertainty": "LOW",
                "adversariality": "BENIGN",
                "stakes_level": "LOW"
            },
            "quality": {
                "quality_tier": "ADEQUATE",
                "satisficing_mode": True,
                "definition_of_done": {"text": "Test complete", "checks": []},
                "verification_requirement": "NONE"
            },
            "budgets": {
                "token_budget": 1000,
                "tool_call_budget": 5,
                "time_budget_seconds": 60,
                "risk_budget": {"envelope": "minimal", "max_loss": "0"}
            },
            "epistemics": {
                "status": "DERIVED",
                "confidence": 0.9,
                "calibration_note": "Test",
                "freshness_class": "REALTIME",
                "assumptions": []
            },
            "evidence": {
                "evidence_refs": [],
                "evidence_absent_reason": "Test packet"
            },
            "routing": {
                "task_class": "CREATE",
                "tools_state": "tools_ok"
            }
        }


class TestEnforcementRules:
    """Test FSM enforcement rules E1-E7"""
    
    def test_rule_e2_no_action_without_decision(self, validator):
        """TaskDirective without prior ACT/VERIFY_FIRST decision rejected"""
        # Setup: obs → belief → decision(DEFER) transitions to S7_REVIEW
        # S7_REVIEW has no outbound transitions, so directive will fail on transition check
        validator.validate_packet(self._create_observation("corr_001"))
        validator.validate_packet(self._create_belief_update("corr_001"))
        decision = self._create_decision("corr_001", "DEFER")
        validator.validate_packet(decision)
        
        # Attempt directive - should fail on invalid transition
        directive = self._create_directive("corr_001", "READ")
        result = validator.validate_packet(directive)
        
        assert not result.is_valid
        # Either transition error or Rule E2 error is acceptable
        assert ("Invalid transition" in result.errors[0] or 
                "requires prior DecisionPacket" in result.errors[0])
    
    def test_rule_e4_write_requires_token(self, validator):
        """WRITE directive without token rejected"""
        # Setup: obs → belief → decision(ACT)
        validator.validate_packet(self._create_observation("corr_001"))
        validator.validate_packet(self._create_belief_update("corr_001"))
        decision = self._create_decision("corr_001", "ACT")
        validator.validate_packet(decision)
        
        # Attempt WRITE without token
        directive = self._create_directive("corr_001", "WRITE", authorization_token_id="missing_token")
        result = validator.validate_packet(directive)
        
        assert not result.is_valid
        assert "Token missing_token not found" in result.errors[0]
    
    def test_rule_e4_write_with_valid_token(self, validator):
        """WRITE directive with valid token succeeds"""
        # Setup: obs → belief → decision(ACT) → token
        validator.validate_packet(self._create_observation("corr_001"))
        validator.validate_packet(self._create_belief_update("corr_001"))
        validator.validate_packet(self._create_decision("corr_001", "ACT"))
        
        # Issue token
        token = self._create_token("corr_001", "token_001")
        validator.validate_packet(token)
        
        # WRITE directive with token
        directive = self._create_directive("corr_001", "WRITE", authorization_token_id="token_001")
        result = validator.validate_packet(directive)
        
        assert result.is_valid
        assert result.to_state == FSMState.S6_EXECUTE
    
    def test_rule_e5_escalation_requires_options(self, validator):
        """EscalationPacket must have 2-3 options and evidence gaps"""
        # Setup to ESCALATED state
        validator.validate_packet(self._create_observation("corr_001"))
        validator.validate_packet(self._create_belief_update("corr_001"))
        decision = self._create_decision("corr_001", "ESCALATE")
        validator.validate_packet(decision)
        
        # Escalation packet with insufficient options
        escalation = {
            "header": {
                "packet_id": "pkt_esc_001",
                "packet_type": "EscalationPacket",
                "created_at": datetime.now().isoformat(),
                "layer_source": 5,
                "correlation_id": "corr_001"
            },
            "mcp": self._minimal_mcp(),
            "payload": {
                "top_options": [{"option_id": "opt_1"}],  # Only 1 option
                "evidence_gaps": [],  # Missing gaps
                "recommended_next_step": None  # Missing recommendation
            }
        }
        
        result = validator.validate_packet(escalation)
        
        assert not result.is_valid
        assert any("2-3 top_options" in err for err in result.errors)
        assert any("evidence_gap" in err for err in result.errors)
        assert any("recommended_next_step" in err for err in result.errors)
    
    # Helper methods (same as TestFSMBasicTransitions)
    def _create_observation(self, correlation_id, packet_id="pkt_obs_001"):
        return {
            "header": {
                "packet_id": packet_id,
                "packet_type": "ObservationPacket",
                "created_at": datetime.now().isoformat(),
                "layer_source": 6,
                "correlation_id": correlation_id
            },
            "mcp": self._minimal_mcp(),
            "payload": {
                "observation_type": "tool_output",
                "data": {"test": "data"},
                "source_tool": "test_tool",
                "reliability_metadata": {
                    "tool_success": True,
                    "latency_ms": 100,
                    "partial_result": False
                }
            }
        }
    
    def _create_belief_update(self, correlation_id, packet_id="pkt_belief_001"):
        return {
            "header": {
                "packet_id": packet_id,
                "packet_type": "BeliefUpdatePacket",
                "created_at": datetime.now().isoformat(),
                "layer_source": 5,
                "correlation_id": correlation_id
            },
            "mcp": self._minimal_mcp(),
            "payload": {
                "update_type": "new_belief",
                "belief_changes": [{
                    "domain": "test",
                    "key": "status",
                    "new_value": "active",
                    "prior_value": "unknown",
                    "epistemic_upgrade": True
                }],
                "evidence_integration": ["pkt_obs_001"]
            }
        }
    
    def _create_decision(self, correlation_id, outcome, packet_id="pkt_dec_001"):
        return {
            "header": {
                "packet_id": packet_id,
                "packet_type": "DecisionPacket",
                "created_at": datetime.now().isoformat(),
                "layer_source": 5,
                "correlation_id": correlation_id
            },
            "mcp": self._minimal_mcp(),
            "payload": {
                "decision_outcome": outcome,
                "decision_summary": f"Test decision: {outcome}",
                "chosen_option": {
                    "option_id": "opt_1",
                    "description": "Test option",
                    "expected_value": 0.8,
                    "risk_profile": "low"
                },
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
    
    def _create_directive(self, correlation_id, safety_class, packet_id="pkt_dir_001", authorization_token_id=None):
        payload = {
            "task_id": "task_001",
            "task_type": "tool_call",
            "execution_method": {
                "method": "tool",
                "tool_id": "test_tool",
                "tool_params": {}
            },
            "tool_safety_class": safety_class,
            "timeout_seconds": 30,
            "retry_policy": {"max_retries": 0, "backoff_multiplier": 1}
        }
        if authorization_token_id:
            payload["authorization_token_id"] = authorization_token_id
        
        return {
            "header": {
                "packet_id": packet_id,
                "packet_type": "TaskDirectivePacket",
                "created_at": datetime.now().isoformat(),
                "layer_source": 5,
                "correlation_id": correlation_id
            },
            "mcp": self._minimal_mcp(),
            "payload": payload
        }
    
    def _create_token(self, correlation_id, token_id, packet_id="pkt_token_001"):
        return {
            "header": {
                "packet_id": packet_id,
                "packet_type": "ToolAuthorizationToken",
                "created_at": datetime.now().isoformat(),
                "layer_source": 1,
                "correlation_id": correlation_id
            },
            "mcp": self._minimal_mcp(),
            "payload": {
                "token_id": token_id,
                "authorized_scope": {
                    "tool_ids": ["test_tool"],
                    "operation_types": ["write"],
                    "resource_constraints": {}
                },
                "expiry": (datetime.now() + timedelta(minutes=5)).isoformat(),
                "max_usage_count": 1,
                "usage_count": 0,
                "issuer_layer": 1,
                "revoked": False,
                "rationale": "Test token"
            }
        }
    
    def _minimal_mcp(self):
        return {
            "intent": {"summary": "Test", "scope": "test"},
            "stakes": {
                "impact": "LOW",
                "irreversibility": "REVERSIBLE",
                "uncertainty": "LOW",
                "adversariality": "BENIGN",
                "stakes_level": "LOW"
            },
            "quality": {
                "quality_tier": "ADEQUATE",
                "satisficing_mode": True,
                "definition_of_done": {"text": "Test complete", "checks": []},
                "verification_requirement": "NONE"
            },
            "budgets": {
                "token_budget": 1000,
                "tool_call_budget": 5,
                "time_budget_seconds": 60,
                "risk_budget": {"envelope": "minimal", "max_loss": "0"}
            },
            "epistemics": {
                "status": "DERIVED",
                "confidence": 0.9,
                "calibration_note": "Test",
                "freshness_class": "REALTIME",
                "assumptions": []
            },
            "evidence": {
                "evidence_refs": [],
                "evidence_absent_reason": "Test packet"
            },
            "routing": {
                "task_class": "CREATE",
                "tools_state": "tools_ok"
            }
        }


class TestGoldenFixtures:
    """Test FSM validator against golden episode fixtures"""
    
    def test_verify_loop_episode(self, validator, goldens_dir):
        """Validate verify_loop episode sequence"""
        fixture = goldens_dir / "Episode.verify_loop.jsonl"
        
        packets = []
        with open(fixture, 'r') as f:
            for line in f:
                if line.strip():
                    packets.append(json.loads(line))
        
        results = validator.validate_episode_sequence(packets)
        
        # All packets should be valid
        assert all(r.is_valid for r in results), \
            f"Failed packets: {[r.packet_id for r in results if not r.is_valid]}"
        
        # Verify state progression
        expected_states = [
            FSMState.S1_SENSE,    # Observation
            FSMState.S2_MODEL,    # BeliefUpdate (stale)
            FSMState.S4_VERIFY,   # Decision (VERIFY_FIRST) - goes directly to S4_VERIFY
            FSMState.S4_VERIFY,   # Directive (READ) - stays in S4_VERIFY
            FSMState.S4_VERIFY,   # Result (SUCCESS)
            FSMState.S4_VERIFY,   # Observation (OBSERVED)
            FSMState.S2_MODEL,    # BeliefUpdate (upgrade)
            FSMState.S3_DECIDE    # Decision (ACT)
        ]
        
        actual_states = [r.to_state for r in results]
        assert actual_states == expected_states
    
    def test_write_with_token_episode(self, validator, goldens_dir):
        """Validate write_with_token episode sequence"""
        fixture = goldens_dir / "Episode.write_with_token.jsonl"
        
        packets = []
        with open(fixture, 'r') as f:
            for line in f:
                if line.strip():
                    packets.append(json.loads(line))
        
        results = validator.validate_episode_sequence(packets)
        
        # All packets should be valid
        assert all(r.is_valid for r in results), \
            f"Failed: {[(r.packet_id, r.errors) for r in results if not r.is_valid]}"
        
        # Check for token authorization flow
        packet_types = [p["header"]["packet_type"] for p in packets]
        assert "ToolAuthorizationToken" in packet_types
        assert "TaskDirectivePacket" in packet_types


class TestEpisodeTracking:
    """Test multi-episode tracking"""
    
    def test_multiple_episodes_isolated(self, validator):
        """Episodes with different correlation_ids tracked separately"""
        # Episode 1
        obs1 = self._create_observation("corr_001")
        result1 = validator.validate_packet(obs1)
        assert result1.is_valid
        
        # Episode 2
        obs2 = self._create_observation("corr_002")
        result2 = validator.validate_packet(obs2)
        assert result2.is_valid
        
        # Check both episodes tracked
        summary1 = validator.get_episode_summary("corr_001")
        summary2 = validator.get_episode_summary("corr_002")
        
        assert summary1["current_state"] == "S1_SENSE"
        assert summary2["current_state"] == "S1_SENSE"
        assert summary1["packets_seen"] == 1
        assert summary2["packets_seen"] == 1
    
    def _create_observation(self, correlation_id, packet_id=None):
        if packet_id is None:
            packet_id = f"pkt_obs_{correlation_id}"
        
        return {
            "header": {
                "packet_id": packet_id,
                "packet_type": "ObservationPacket",
                "created_at": datetime.now().isoformat(),
                "layer_source": 6,
                "correlation_id": correlation_id
            },
            "mcp": {
                "intent": {"summary": "Test", "scope": "test"},
                "stakes": {
                    "impact": "LOW",
                    "irreversibility": "REVERSIBLE",
                    "uncertainty": "LOW",
                    "adversariality": "BENIGN",
                    "stakes_level": "LOW"
                },
                "quality": {
                    "quality_tier": "ADEQUATE",
                    "satisficing_mode": True,
                    "definition_of_done": {"text": "Test complete", "checks": []},
                    "verification_requirement": "NONE"
                },
                "budgets": {
                    "token_budget": 1000,
                    "tool_call_budget": 5,
                    "time_budget_seconds": 60,
                    "risk_budget": {"envelope": "minimal", "max_loss": "0"}
                },
                "epistemics": {
                    "status": "DERIVED",
                    "confidence": 0.9,
                    "calibration_note": "Test",
                    "freshness_class": "REALTIME",
                    "assumptions": []
                },
                "evidence": {
                    "evidence_refs": [],
                    "evidence_absent_reason": "Test packet"
                },
                "routing": {
                    "task_class": "CREATE",
                    "tools_state": "tools_ok"
                }
            },
            "payload": {
                "observation_type": "tool_output",
                "data": {"test": "data"},
                "source_tool": "test_tool",
                "reliability_metadata": {
                    "tool_success": True,
                    "latency_ms": 100,
                    "partial_result": False
                }
            }
        }

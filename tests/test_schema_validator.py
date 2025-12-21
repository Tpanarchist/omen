"""
Tests for OMEN v0.7 Schema Validator

Tests schema validation against golden fixtures.
"""

import json
import pytest
from pathlib import Path

# Add validators to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "validators" / "v0.7"))

from schema_validator import SchemaValidator, ValidationResultType


@pytest.fixture
def validator():
    """Create schema validator instance."""
    base_path = Path(__file__).parent.parent
    return SchemaValidator(base_path)


@pytest.fixture
def goldens_dir():
    """Get goldens directory path."""
    return Path(__file__).parent.parent / "goldens" / "v0.7"


class TestSchemaValidator:
    """Test suite for SchemaValidator."""
    
    def test_validator_initialization(self, validator):
        """Test validator initializes correctly."""
        assert validator is not None
        assert validator.schema_dir.exists()
        assert len(validator._schema_cache) >= 3  # Header, MCP, Base
    
    def test_valid_decision_verify_first(self, validator, goldens_dir):
        """Test valid DecisionPacket with VERIFY_FIRST outcome."""
        fixture = goldens_dir / "DecisionPacket.verify_first.json"
        result = validator.load_and_validate_file(fixture)
        
        assert result.is_valid, f"Errors: {result.errors}"
        assert result.result_type == ValidationResultType.PASS
        assert result.packet_type == "DecisionPacket"
        assert result.packet_id == "pkt_decision_001"
    
    def test_valid_decision_act_readonly(self, validator, goldens_dir):
        """Test valid DecisionPacket with ACT (read-only)."""
        fixture = goldens_dir / "DecisionPacket.act_readonly.json"
        result = validator.load_and_validate_file(fixture)
        
        assert result.is_valid, f"Errors: {result.errors}"
        assert result.result_type == ValidationResultType.PASS
    
    def test_valid_decision_act_write(self, validator, goldens_dir):
        """Test valid DecisionPacket with ACT (write)."""
        fixture = goldens_dir / "DecisionPacket.act_write.json"
        result = validator.load_and_validate_file(fixture)
        
        assert result.is_valid, f"Errors: {result.errors}"
        assert result.result_type == ValidationResultType.PASS
        assert len(result.warnings) >= 0  # May have warnings
    
    def test_valid_escalation(self, validator, goldens_dir):
        """Test valid EscalationPacket."""
        fixture = goldens_dir / "EscalationPacket.high_stakes_uncertainty.json"
        result = validator.load_and_validate_file(fixture)
        
        assert result.is_valid, f"Errors: {result.errors}"
        assert result.result_type == ValidationResultType.PASS
        assert result.packet_type == "EscalationPacket"
    
    def test_invalid_subpar_action(self, validator, goldens_dir):
        """Test INVALID fixture (SUBPAR attempting ACT)."""
        fixture = goldens_dir / "DecisionPacket.subpar_blocks_action.INVALID.json"
        result = validator.load_and_validate_file(fixture)
        
        # Schema validation should PASS (structure is valid)
        # Invariant validation (not tested here) should FAIL
        assert result.is_valid, "Schema structure should be valid for INVALID fixtures"
        # Note: This tests that JSON Schema alone doesn't catch policy violations
        # Invariant validator will catch INV-002 violation
    
    def test_episode_verify_loop(self, validator, goldens_dir):
        """Test valid episode sequence (verify loop)."""
        fixture = goldens_dir / "Episode.verify_loop.jsonl"
        results = validator.load_and_validate_jsonl(fixture)
        
        assert len(results) == 8, "Verify loop should have 8 packets"
        
        for i, result in enumerate(results):
            assert result.is_valid, f"Packet {i+1} failed: {result.errors}"
        
        # Check packet sequence
        packet_types = [r.packet_type for r in results]
        expected = [
            "ObservationPacket",
            "BeliefUpdatePacket",
            "DecisionPacket",
            "TaskDirectivePacket",
            "TaskResultPacket",
            "ObservationPacket",
            "BeliefUpdatePacket",
            "DecisionPacket"
        ]
        assert packet_types == expected, f"Unexpected sequence: {packet_types}"
    
    def test_episode_degraded_tools(self, validator, goldens_dir):
        """Test valid episode with degraded tools."""
        fixture = goldens_dir / "Episode.degraded_tools_high_stakes.jsonl"
        results = validator.load_and_validate_jsonl(fixture)
        
        assert len(results) == 4, "Degraded tools episode should have 4 packets"
        
        for i, result in enumerate(results):
            assert result.is_valid, f"Packet {i+1} failed: {result.errors}"
    
    def test_episode_write_with_token(self, validator, goldens_dir):
        """Test valid episode with write authorization."""
        fixture = goldens_dir / "Episode.write_with_token.jsonl"
        results = validator.load_and_validate_jsonl(fixture)
        
        assert len(results) == 6, "Write episode should have 6 packets"
        
        for i, result in enumerate(results):
            assert result.is_valid, f"Packet {i+1} failed: {result.errors}"
        
        # Check for ToolAuthorizationToken
        packet_types = [r.packet_type for r in results]
        assert "ToolAuthorizationToken" in packet_types
        assert "TaskDirectivePacket" in packet_types
    
    def test_missing_required_field(self, validator):
        """Test packet with missing required field."""
        packet = {
            "header": {
                "packet_id": "pkt_test_001",
                "packet_type": "ObservationPacket",
                # Missing created_at, layer_source, correlation_id
            },
            "mcp": {},
            "payload": {}
        }
        
        result = validator.validate_packet(packet)
        assert not result.is_valid
        assert any("required" in err.lower() for err in result.errors)
    
    def test_invalid_enum_value(self, validator):
        """Test packet with invalid enum value."""
        packet = {
            "header": {
                "packet_id": "pkt_test_002",
                "packet_type": "InvalidPacketType",  # Not in enum
                "created_at": "2025-12-21T12:00:00Z",
                "layer_source": 5,
                "correlation_id": "corr_test"
            },
            "mcp": {},
            "payload": {}
        }
        
        result = validator.validate_packet(packet)
        assert not result.is_valid
        # Should fail because InvalidPacketType has no schema
        assert result.result_type == ValidationResultType.ERROR


class TestGoldenFixtures:
    """Test that all golden fixtures validate correctly."""
    
    def test_all_valid_fixtures_pass(self, validator, goldens_dir):
        """All non-INVALID fixtures should pass schema validation."""
        for fixture in goldens_dir.glob("*.json"):
            if "INVALID" in fixture.name:
                continue  # Skip negative tests
            
            result = validator.load_and_validate_file(fixture)
            assert result.is_valid, (
                f"{fixture.name} failed validation:\n"
                f"Errors: {result.errors}\n"
                f"Warnings: {result.warnings}"
            )
    
    def test_all_episodes_pass(self, validator, goldens_dir):
        """All episode sequences should pass schema validation."""
        for fixture in goldens_dir.glob("*.jsonl"):
            results = validator.load_and_validate_jsonl(fixture)
            
            for i, result in enumerate(results, 1):
                assert result.is_valid, (
                    f"{fixture.name} packet {i} failed:\n"
                    f"Packet ID: {result.packet_id}\n"
                    f"Errors: {result.errors}"
                )
    
    def test_invalid_fixtures_structure_valid(self, validator, goldens_dir):
        """INVALID fixtures should be structurally valid (fail on invariants)."""
        for fixture in goldens_dir.glob("*INVALID*.json"):
            result = validator.load_and_validate_file(fixture)
            
            # Schema validation should pass for INVALID fixtures
            # (They fail on semantic invariants, not structure)
            assert result.is_valid, (
                f"{fixture.name} should be structurally valid:\n"
                f"Errors: {result.errors}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

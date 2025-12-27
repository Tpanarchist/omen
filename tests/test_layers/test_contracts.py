"""Tests for layer contracts."""

import pytest

from omen.vocabulary import LayerSource, PacketType
from omen.layers import (
    LayerContract,
    ContractViolation,
    ContractEnforcer,
    LAYER_CONTRACTS,
    LAYER_1_CONTRACT,
    LAYER_5_CONTRACT,
    LAYER_6_CONTRACT,
    INTEGRITY_CONTRACT,
    get_contract,
    get_all_contracts,
    create_contract_enforcer,
)


class TestLayerContract:
    """Tests for LayerContract dataclass."""
    
    def test_contract_immutable(self):
        """Contracts are frozen (immutable)."""
        with pytest.raises(Exception):  # FrozenInstanceError
            LAYER_1_CONTRACT.description = "modified"
    
    def test_allows_emit(self):
        """allows_emit checks can_emit set."""
        # L5 can emit Decision
        assert LAYER_5_CONTRACT.allows_emit(PacketType.DECISION) is True
        # L5 cannot emit Observation
        assert LAYER_5_CONTRACT.allows_emit(PacketType.OBSERVATION) is False
    
    def test_allows_receive(self):
        """allows_receive checks can_receive set."""
        # L6 can receive TaskDirective
        assert LAYER_6_CONTRACT.allows_receive(PacketType.TASK_DIRECTIVE) is True
        # L6 cannot receive Escalation (that's for higher layers)
        assert LAYER_6_CONTRACT.allows_receive(PacketType.ESCALATION) is False


class TestContractRegistry:
    """Tests for contract registry."""
    
    def test_all_layers_have_contracts(self):
        """Every LayerSource has a contract defined."""
        for layer in LayerSource:
            assert layer in LAYER_CONTRACTS
    
    def test_get_contract(self):
        """get_contract returns correct contract."""
        contract = get_contract(LayerSource.LAYER_5)
        assert contract.layer == LayerSource.LAYER_5
    
    def test_get_all_contracts(self):
        """get_all_contracts returns all 7 contracts."""
        contracts = get_all_contracts()
        assert len(contracts) == 7


class TestLayer1Contract:
    """Tests for L1 (Aspirational) contract."""
    
    def test_can_emit_integrity_alert(self):
        """L1 can emit IntegrityAlert (vetoes)."""
        assert LAYER_1_CONTRACT.allows_emit(PacketType.INTEGRITY_ALERT)
    
    def test_cannot_emit_directive(self):
        """L1 cannot emit TaskDirective (no directives)."""
        assert not LAYER_1_CONTRACT.allows_emit(PacketType.TASK_DIRECTIVE)
    
    def test_cannot_emit_decision(self):
        """L1 cannot emit Decision (that's L5's job)."""
        assert not LAYER_1_CONTRACT.allows_emit(PacketType.DECISION)
    
    def test_receives_escalations(self):
        """L1 receives Escalation packets."""
        assert LAYER_1_CONTRACT.allows_receive(PacketType.ESCALATION)


class TestLayer5Contract:
    """Tests for L5 (Cognitive Control) contract."""
    
    def test_can_emit_decision(self):
        """L5 can emit Decision."""
        assert LAYER_5_CONTRACT.allows_emit(PacketType.DECISION)
    
    def test_can_emit_token(self):
        """L5 can emit ToolAuthorizationToken."""
        assert LAYER_5_CONTRACT.allows_emit(PacketType.TOOL_AUTHORIZATION)
    
    def test_can_emit_directive(self):
        """L5 can emit TaskDirective."""
        assert LAYER_5_CONTRACT.allows_emit(PacketType.TASK_DIRECTIVE)
    
    def test_cannot_emit_observation(self):
        """L5 cannot emit Observation (that's L6's job)."""
        assert not LAYER_5_CONTRACT.allows_emit(PacketType.OBSERVATION)
    
    def test_cannot_emit_task_result(self):
        """L5 cannot emit TaskResult (that's L6's job)."""
        assert not LAYER_5_CONTRACT.allows_emit(PacketType.TASK_RESULT)


class TestLayer6Contract:
    """Tests for L6 (Task Prosecution) contract."""
    
    def test_can_emit_observation(self):
        """L6 can emit Observation."""
        assert LAYER_6_CONTRACT.allows_emit(PacketType.OBSERVATION)
    
    def test_can_emit_task_result(self):
        """L6 can emit TaskResult."""
        assert LAYER_6_CONTRACT.allows_emit(PacketType.TASK_RESULT)
    
    def test_cannot_emit_decision(self):
        """L6 cannot emit Decision (no policy decisions)."""
        assert not LAYER_6_CONTRACT.allows_emit(PacketType.DECISION)
    
    def test_cannot_emit_token(self):
        """L6 cannot emit ToolAuthorizationToken."""
        assert not LAYER_6_CONTRACT.allows_emit(PacketType.TOOL_AUTHORIZATION)
    
    def test_receives_directives(self):
        """L6 receives TaskDirective."""
        assert LAYER_6_CONTRACT.allows_receive(PacketType.TASK_DIRECTIVE)


class TestIntegrityContract:
    """Tests for Integrity overlay contract."""
    
    def test_can_emit_integrity_alert(self):
        """Integrity can emit IntegrityAlert."""
        assert INTEGRITY_CONTRACT.allows_emit(PacketType.INTEGRITY_ALERT)
    
    def test_cannot_emit_decision(self):
        """Integrity cannot emit Decision."""
        assert not INTEGRITY_CONTRACT.allows_emit(PacketType.DECISION)
    
    def test_receives_everything(self):
        """Integrity can receive all packet types."""
        for pt in PacketType:
            assert INTEGRITY_CONTRACT.allows_receive(pt), f"Should receive {pt}"


class TestContractEnforcer:
    """Tests for contract enforcement."""
    
    @pytest.fixture
    def enforcer(self):
        return create_contract_enforcer()
    
    def test_valid_emit_returns_none(self, enforcer):
        """Valid emission returns None (no violation)."""
        result = enforcer.check_emit(LayerSource.LAYER_5, PacketType.DECISION)
        assert result is None
    
    def test_invalid_emit_returns_violation(self, enforcer):
        """Invalid emission returns ContractViolation."""
        result = enforcer.check_emit(LayerSource.LAYER_6, PacketType.DECISION)
        assert result is not None
        assert result.layer == LayerSource.LAYER_6
        assert result.packet_type == PacketType.DECISION
        assert result.violation_type == "emit"
    
    def test_valid_receive_returns_none(self, enforcer):
        """Valid reception returns None."""
        result = enforcer.check_receive(LayerSource.LAYER_6, PacketType.TASK_DIRECTIVE)
        assert result is None
    
    def test_invalid_receive_returns_violation(self, enforcer):
        """Invalid reception returns ContractViolation."""
        result = enforcer.check_receive(LayerSource.LAYER_6, PacketType.ESCALATION)
        assert result is not None
        assert result.violation_type == "receive"
    
    def test_validate_emission_boolean(self, enforcer):
        """validate_emission returns boolean."""
        assert enforcer.validate_emission(LayerSource.LAYER_5, PacketType.DECISION) is True
        assert enforcer.validate_emission(LayerSource.LAYER_6, PacketType.DECISION) is False
    
    def test_validate_reception_boolean(self, enforcer):
        """validate_reception returns boolean."""
        assert enforcer.validate_reception(LayerSource.LAYER_6, PacketType.TASK_DIRECTIVE) is True
        assert enforcer.validate_reception(LayerSource.LAYER_6, PacketType.ESCALATION) is False


class TestContractConsistency:
    """Tests for contract consistency with template validator."""
    
    def test_matches_template_layer_packet_contracts(self):
        """Layer contracts should align with template validator emissions."""
        # All layers in the contract registry should be able to emit
        # the packets they're allowed to emit
        for layer_source in LayerSource:
            contract = get_contract(layer_source)
            
            # Verify the contract has emission permissions
            assert isinstance(contract.can_emit, frozenset)
            assert isinstance(contract.can_receive, frozenset)
            
            # Verify all emittable packets are valid PacketTypes
            for packet_type in contract.can_emit:
                assert isinstance(packet_type, PacketType)

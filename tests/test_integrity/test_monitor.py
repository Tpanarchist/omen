"""Tests for integrity monitor."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from omen.vocabulary import LayerSource, PacketType
from omen.buses import BusMessage, NorthboundBus, SouthboundBus
from omen.orchestrator.ledger import EpisodeLedger, BudgetState, ActiveToken, create_ledger
from omen.integrity import (
    SafeMode,
    AlertSeverity,
    AlertType,
    IntegrityEvent,
    MonitorConfig,
    IntegrityMonitor,
    create_monitor,
)


class TestSafeMode:
    """Tests for safe mode enum."""
    
    def test_modes_exist(self):
        """All safe modes are defined."""
        assert SafeMode.NORMAL.value == "normal"
        assert SafeMode.CAUTIOUS.value == "cautious"
        assert SafeMode.RESTRICTED.value == "restricted"
        assert SafeMode.HALTED.value == "halted"


class TestMonitorConfig:
    """Tests for monitor configuration."""
    
    def test_default_config(self):
        """Default config has sensible values."""
        config = MonitorConfig()
        assert config.budget_warning_threshold == 0.8
        assert config.budget_halt_threshold == 1.0
        assert config.halt_on_budget_exceeded is True
    
    def test_custom_config(self):
        """Can customize config."""
        config = MonitorConfig(
            budget_warning_threshold=0.7,
            halt_on_budget_exceeded=False,
        )
        assert config.budget_warning_threshold == 0.7
        assert config.halt_on_budget_exceeded is False


class TestIntegrityMonitor:
    """Tests for integrity monitor."""
    
    @pytest.fixture
    def monitor(self):
        return create_monitor()
    
    @pytest.fixture
    def ledger(self):
        return create_ledger(
            correlation_id=uuid4(),
            budget=BudgetState(token_budget=1000, tool_call_budget=10),
        )
    
    def test_initial_state(self, monitor):
        """Monitor starts in normal mode."""
        assert monitor.safe_mode == SafeMode.NORMAL
        assert monitor.is_halted is False
    
    def test_register_ledger(self, monitor, ledger):
        """Can register ledger for monitoring."""
        monitor.register_ledger(ledger)
        assert ledger.correlation_id in monitor._active_ledgers
    
    def test_unregister_ledger(self, monitor, ledger):
        """Can unregister ledger."""
        monitor.register_ledger(ledger)
        monitor.unregister_ledger(ledger.correlation_id)
        assert ledger.correlation_id not in monitor._active_ledgers


class TestBudgetEnforcement:
    """Tests for budget enforcement."""
    
    @pytest.fixture
    def monitor(self):
        return create_monitor()
    
    @pytest.fixture
    def ledger(self):
        return create_ledger(
            correlation_id=uuid4(),
            budget=BudgetState(token_budget=1000, tool_call_budget=10),
        )
    
    def test_no_alert_under_threshold(self, monitor, ledger):
        """No alert when under warning threshold."""
        ledger.budget.consume(tokens=500)  # 50%
        event = monitor.check_budget(ledger)
        assert event is None
    
    def test_warning_at_threshold(self, monitor, ledger):
        """Warning when at warning threshold."""
        ledger.budget.consume(tokens=850)  # 85%
        event = monitor.check_budget(ledger)
        
        assert event is not None
        assert event.alert_type == AlertType.BUDGET_WARNING
        assert event.severity == AlertSeverity.WARNING
    
    def test_halt_when_exceeded(self, monitor, ledger):
        """Halt requested when budget exceeded."""
        ledger.budget.consume(tokens=1100)  # 110%
        event = monitor.check_budget(ledger)
        
        assert event is not None
        assert event.alert_type == AlertType.BUDGET_EXCEEDED
        assert event.severity == AlertSeverity.CRITICAL
        assert monitor.is_halted is True
    
    def test_tokens_revoked_on_exceed(self, monitor, ledger):
        """Tokens revoked when budget exceeded."""
        # Add a token
        token = ActiveToken(
            token_id="tok_test",
            scope={},
            issued_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            max_uses=5,
            uses_remaining=5,
        )
        ledger.add_token(token)
        
        # Exceed budget
        ledger.budget.consume(tokens=1100)
        monitor.check_budget(ledger)
        
        # Token should be revoked
        assert token.revoked is True
    
    def test_no_halt_when_disabled(self, ledger):
        """No halt when configured to not halt."""
        config = MonitorConfig(halt_on_budget_exceeded=False)
        monitor = create_monitor(config=config)
        
        ledger.budget.consume(tokens=1100)
        monitor.check_budget(ledger)
        
        assert monitor.is_halted is False


class TestTokenValidation:
    """Tests for token validation."""
    
    @pytest.fixture
    def monitor(self):
        return create_monitor()
    
    def test_valid_token(self, monitor):
        """No alert for valid token."""
        token = ActiveToken(
            token_id="tok_valid",
            scope={},
            issued_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            max_uses=5,
            uses_remaining=5,
        )
        
        event = monitor.check_token(token)
        assert event is None
    
    def test_revoked_token(self, monitor):
        """Alert for revoked token."""
        token = ActiveToken(
            token_id="tok_revoked",
            scope={},
            issued_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            max_uses=5,
            uses_remaining=5,
            revoked=True,
        )
        
        event = monitor.check_token(token)
        assert event is not None
        assert event.alert_type == AlertType.TOKEN_REVOKED
    
    def test_expired_token(self, monitor):
        """Alert for expired token."""
        token = ActiveToken(
            token_id="tok_expired",
            scope={},
            issued_at=datetime.now() - timedelta(hours=2),
            expires_at=datetime.now() - timedelta(hours=1),
            max_uses=5,
            uses_remaining=5,
        )
        
        event = monitor.check_token(token)
        assert event is not None
        assert event.alert_type == AlertType.TOKEN_EXPIRED


class TestTokenRevocation:
    """Tests for token revocation."""
    
    @pytest.fixture
    def monitor(self):
        return create_monitor()
    
    @pytest.fixture
    def ledger(self):
        ledger = create_ledger(correlation_id=uuid4())
        token = ActiveToken(
            token_id="tok_test",
            scope={},
            issued_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            max_uses=5,
            uses_remaining=5,
        )
        ledger.add_token(token)
        return ledger
    
    def test_revoke_token(self, monitor, ledger):
        """Can revoke specific token."""
        event = monitor.revoke_token(ledger, "tok_test", "Policy violation")
        
        assert event.alert_type == AlertType.TOKEN_REVOKED
        assert ledger.get_token("tok_test").revoked is True


class TestContradictionHandling:
    """Tests for contradiction detection."""
    
    @pytest.fixture
    def monitor(self):
        config = MonitorConfig(max_contradictions_before_halt=3)
        return create_monitor(config=config)
    
    @pytest.fixture
    def ledger(self):
        return create_ledger(correlation_id=uuid4())
    
    def test_flag_contradiction(self, monitor, ledger):
        """Can flag contradictions."""
        event = monitor.flag_contradiction(ledger, "Price mismatch")
        
        assert event.alert_type == AlertType.CONTRADICTION_DETECTED
        assert ledger.contradiction_detected is True
    
    def test_safe_mode_on_many_contradictions(self, monitor, ledger):
        """Transitions to cautious mode after threshold."""
        monitor.flag_contradiction(ledger, "Contradiction 1")
        monitor.flag_contradiction(ledger, "Contradiction 2")
        event = monitor.flag_contradiction(ledger, "Contradiction 3")
        
        assert event.severity == AlertSeverity.HIGH
        assert monitor.safe_mode == SafeMode.CAUTIOUS


class TestSafeModeTransitions:
    """Tests for safe mode transitions."""
    
    @pytest.fixture
    def monitor(self):
        return create_monitor()
    
    def test_transition_to_restricted(self, monitor):
        """Can transition to restricted mode."""
        event = monitor.transition_safe_mode(SafeMode.RESTRICTED, "Test reason")
        
        assert monitor.safe_mode == SafeMode.RESTRICTED
        assert event.alert_type == AlertType.SAFE_MODE_TRIGGERED
        assert "restricted" in event.details["new_mode"]
    
    def test_transition_to_halted(self, monitor):
        """Halted mode sets is_halted."""
        monitor.transition_safe_mode(SafeMode.HALTED)
        
        assert monitor.is_halted is True
    
    def test_reset(self, monitor):
        """Reset restores normal mode."""
        monitor.transition_safe_mode(SafeMode.HALTED)
        monitor.reset()
        
        assert monitor.safe_mode == SafeMode.NORMAL
        assert monitor.is_halted is False


class TestCheckSafeMode:
    """Tests for safe mode operation checking."""
    
    @pytest.fixture
    def monitor(self):
        return create_monitor()
    
    def test_normal_mode_allows_all(self, monitor):
        """Normal mode allows all operations."""
        assert monitor.check_safe_mode("READ") is None
        assert monitor.check_safe_mode("WRITE") is None
    
    def test_restricted_blocks_write(self, monitor):
        """Restricted mode blocks WRITE operations."""
        monitor.transition_safe_mode(SafeMode.RESTRICTED)
        
        event = monitor.check_safe_mode("WRITE")
        assert event is not None
        assert event.alert_type == AlertType.SAFE_MODE_TRIGGERED
        assert event.severity == AlertSeverity.HIGH
        assert "WRITE operation blocked" in event.message
    
    def test_restricted_allows_read(self, monitor):
        """Restricted mode allows READ operations."""
        monitor.transition_safe_mode(SafeMode.RESTRICTED)
        
        assert monitor.check_safe_mode("READ") is None
    
    def test_halted_blocks_all(self, monitor):
        """Halted mode blocks all operations."""
        monitor.transition_safe_mode(SafeMode.HALTED)
        
        read_event = monitor.check_safe_mode("READ")
        write_event = monitor.check_safe_mode("WRITE")
        
        assert read_event is not None
        assert write_event is not None
        assert read_event.severity == AlertSeverity.CRITICAL
        assert write_event.severity == AlertSeverity.CRITICAL


class TestEventTracking:
    """Tests for event tracking."""
    
    @pytest.fixture
    def monitor(self):
        return create_monitor()
    
    @pytest.fixture
    def ledger(self):
        return create_ledger(
            correlation_id=uuid4(),
            budget=BudgetState(token_budget=100),
        )
    
    def test_events_recorded(self, monitor, ledger):
        """Events are recorded."""
        ledger.budget.consume(tokens=90)  # Warning threshold
        monitor.check_budget(ledger)
        
        events = monitor.get_events()
        assert len(events) == 1
    
    def test_query_by_severity(self, monitor, ledger):
        """Can query events by severity."""
        ledger.budget.consume(tokens=90)
        monitor.check_budget(ledger)
        
        ledger.budget.consume(tokens=20)  # Now over
        monitor.check_budget(ledger)
        
        warnings = monitor.get_events(severity=AlertSeverity.WARNING)
        criticals = monitor.get_events(severity=AlertSeverity.CRITICAL)
        
        assert len(warnings) == 1
        assert len(criticals) == 1
    
    def test_query_by_correlation_id(self, monitor):
        """Can query events by correlation ID."""
        cid1 = uuid4()
        cid2 = uuid4()
        
        ledger1 = create_ledger(correlation_id=cid1, budget=BudgetState(token_budget=100))
        ledger2 = create_ledger(correlation_id=cid2, budget=BudgetState(token_budget=100))
        
        ledger1.budget.consume(tokens=90)
        ledger2.budget.consume(tokens=90)
        
        monitor.check_budget(ledger1)
        monitor.check_budget(ledger2)
        
        events = monitor.get_events(correlation_id=cid1)
        assert len(events) == 1
        assert events[0].correlation_id == cid1


class TestAlertCallback:
    """Tests for alert callback."""
    
    def test_callback_invoked(self):
        """Callback is invoked on events."""
        received = []
        monitor = create_monitor(on_alert=lambda e: received.append(e))
        
        monitor._emit_event(IntegrityEvent(
            event_id="test",
            alert_type=AlertType.BUDGET_WARNING,
            severity=AlertSeverity.WARNING,
            message="Test",
        ))
        
        assert len(received) == 1


class TestBusSubscription:
    """Tests for bus subscription."""
    
    def test_subscribes_to_buses(self):
        """Monitor subscribes to both buses."""
        monitor = create_monitor()
        north = NorthboundBus()
        south = SouthboundBus()
        
        monitor.subscribe_to_buses(north, south)
        
        assert LayerSource.INTEGRITY in north._subscribers
        assert LayerSource.INTEGRITY in south._subscribers

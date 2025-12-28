"""
Integrity Monitor — Watches bus traffic and enforces constraints.

The Integrity Overlay monitors all packets flowing through the system
and can trigger alerts, halt execution, or revoke tokens when
violations are detected.

Spec: OMEN.md §12
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable
from uuid import UUID

from omen.vocabulary import LayerSource, PacketType
from omen.buses import BusMessage, NorthboundBus, SouthboundBus
from omen.orchestrator.ledger import EpisodeLedger, ActiveToken


class SafeMode(Enum):
    """System safety modes."""
    NORMAL = "normal"           # Full operation
    CAUTIOUS = "cautious"       # Verify everything
    RESTRICTED = "restricted"   # No write operations
    HALTED = "halted"           # No execution


class AlertSeverity(Enum):
    """Integrity alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of integrity alerts."""
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_REVOKED = "token_revoked"
    CONSTITUTIONAL_VETO = "constitutional_veto"
    CONTRACT_VIOLATION = "contract_violation"
    CONTRADICTION_DETECTED = "contradiction_detected"
    SAFE_MODE_TRIGGERED = "safe_mode_triggered"


@dataclass
class IntegrityEvent:
    """
    Record of an integrity event.
    """
    event_id: str
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: UUID | None = None
    source_layer: LayerSource | None = None
    details: dict[str, Any] = field(default_factory=dict)
    action_taken: str | None = None


@dataclass
class MonitorConfig:
    """Configuration for integrity monitor."""
    # Budget thresholds
    budget_warning_threshold: float = 0.8  # 80% consumed
    budget_halt_threshold: float = 1.0     # 100% consumed
    
    # Behavior
    halt_on_budget_exceeded: bool = True
    halt_on_constitutional_veto: bool = True
    revoke_tokens_on_budget_exceeded: bool = True
    
    # Contradiction handling
    max_contradictions_before_halt: int = 3


class IntegrityMonitor:
    """
    Monitors system integrity and enforces constraints.
    
    Subscribes to buses, watches for violations, and can:
    - Issue alerts
    - Revoke tokens
    - Trigger safe mode transitions
    - Halt execution
    """
    
    def __init__(
        self,
        config: MonitorConfig | None = None,
        on_alert: Callable[[IntegrityEvent], None] | None = None,
    ):
        """
        Initialize monitor.
        
        Args:
            config: Monitor configuration
            on_alert: Callback for alert events
        """
        self.config = config or MonitorConfig()
        self._on_alert = on_alert
        self._safe_mode = SafeMode.NORMAL
        self._events: list[IntegrityEvent] = []
        self._event_counter = 0
        self._halt_requested = False
        self._active_ledgers: dict[UUID, EpisodeLedger] = {}
    
    @property
    def safe_mode(self) -> SafeMode:
        """Current safety mode."""
        return self._safe_mode
    
    @property
    def is_halted(self) -> bool:
        """Check if execution is halted."""
        return self._halt_requested or self._safe_mode == SafeMode.HALTED
    
    def register_ledger(self, ledger: EpisodeLedger) -> None:
        """Register a ledger for monitoring."""
        self._active_ledgers[ledger.correlation_id] = ledger
    
    def unregister_ledger(self, correlation_id: UUID) -> None:
        """Unregister a ledger."""
        self._active_ledgers.pop(correlation_id, None)
    
    def subscribe_to_buses(
        self,
        northbound: NorthboundBus,
        southbound: SouthboundBus,
    ) -> None:
        """Subscribe to both buses for monitoring."""
        northbound.subscribe(LayerSource.INTEGRITY, self._handle_northbound)
        southbound.subscribe(LayerSource.INTEGRITY, self._handle_southbound)
    
    def check_budget(self, ledger: EpisodeLedger) -> IntegrityEvent | None:
        """
        Check budget status and return alert if threshold exceeded.
        """
        budget = ledger.budget
        
        # Calculate consumption ratios
        token_ratio = (
            budget.tokens_consumed / budget.token_budget 
            if budget.token_budget > 0 else 0
        )
        tool_ratio = (
            budget.tool_calls_consumed / budget.tool_call_budget
            if budget.tool_call_budget > 0 else 0
        )
        
        max_ratio = max(token_ratio, tool_ratio)
        
        if max_ratio >= self.config.budget_halt_threshold:
            event = self._create_event(
                AlertType.BUDGET_EXCEEDED,
                AlertSeverity.CRITICAL,
                f"Budget exceeded: tokens={token_ratio:.0%}, tools={tool_ratio:.0%}",
                correlation_id=ledger.correlation_id,
                details={
                    "token_ratio": token_ratio,
                    "tool_ratio": tool_ratio,
                    "tokens_consumed": budget.tokens_consumed,
                    "token_budget": budget.token_budget,
                },
            )
            
            if self.config.halt_on_budget_exceeded:
                event.action_taken = "halt_requested"
                self._halt_requested = True
            
            if self.config.revoke_tokens_on_budget_exceeded:
                self._revoke_all_tokens(ledger)
            
            return event
        
        elif max_ratio >= self.config.budget_warning_threshold:
            return self._create_event(
                AlertType.BUDGET_WARNING,
                AlertSeverity.WARNING,
                f"Budget warning: tokens={token_ratio:.0%}, tools={tool_ratio:.0%}",
                correlation_id=ledger.correlation_id,
                details={
                    "token_ratio": token_ratio,
                    "tool_ratio": tool_ratio,
                },
            )
        
        return None
    
    def check_token(self, token: ActiveToken) -> IntegrityEvent | None:
        """Check token validity."""
        if token.revoked:
            return self._create_event(
                AlertType.TOKEN_REVOKED,
                AlertSeverity.HIGH,
                f"Token {token.token_id} has been revoked",
                details={"token_id": token.token_id},
            )
        
        if not token.is_valid:
            return self._create_event(
                AlertType.TOKEN_EXPIRED,
                AlertSeverity.WARNING,
                f"Token {token.token_id} is expired or exhausted",
                details={
                    "token_id": token.token_id,
                    "uses_remaining": token.uses_remaining,
                },
            )
        
        return None
    
    def check_safe_mode(self, operation: str) -> IntegrityEvent | None:
        """Check if operation is allowed in current safe mode."""
        if self._safe_mode == SafeMode.HALTED:
            return self._create_event(
                AlertType.SAFE_MODE_TRIGGERED,
                AlertSeverity.CRITICAL,
                f"Operation '{operation}' blocked: system halted",
            )
        if self._safe_mode == SafeMode.RESTRICTED and operation == "WRITE":
            return self._create_event(
                AlertType.SAFE_MODE_TRIGGERED,
                AlertSeverity.HIGH,
                f"WRITE operation blocked: restricted mode",
            )
        return None
    
    def process_veto(
        self,
        packet: Any,
        correlation_id: UUID,
    ) -> IntegrityEvent | None:
        """
        Process a constitutional veto from L1.
        
        Returns alert if veto detected.
        """
        # Check if this is an IntegrityAlert packet with veto
        if not self._is_veto_packet(packet):
            return None
        
        event = self._create_event(
            AlertType.CONSTITUTIONAL_VETO,
            AlertSeverity.CRITICAL,
            "Constitutional veto issued by Layer 1",
            correlation_id=correlation_id,
            source_layer=LayerSource.LAYER_1,
            details=self._extract_veto_details(packet),
        )
        
        if self.config.halt_on_constitutional_veto:
            event.action_taken = "halt_requested"
            self._halt_requested = True
            self._transition_safe_mode(SafeMode.HALTED)
        
        # Revoke ALL tokens on constitutional veto (hard stop)
        ledger = self._active_ledgers.get(correlation_id)
        if ledger:
            self._revoke_all_tokens(ledger)
        
        return event
    
    def revoke_token(
        self,
        ledger: EpisodeLedger,
        token_id: str,
        reason: str,
    ) -> IntegrityEvent:
        """Revoke a specific token."""
        ledger.revoke_token(token_id)
        
        return self._create_event(
            AlertType.TOKEN_REVOKED,
            AlertSeverity.HIGH,
            f"Token {token_id} revoked: {reason}",
            correlation_id=ledger.correlation_id,
            details={
                "token_id": token_id,
                "reason": reason,
            },
            action="token_revoked",
        )
    
    def flag_contradiction(
        self,
        ledger: EpisodeLedger,
        detail: str,
    ) -> IntegrityEvent | None:
        """
        Flag a contradiction. May trigger safe mode if threshold exceeded.
        """
        ledger.flag_contradiction(detail)
        
        event = self._create_event(
            AlertType.CONTRADICTION_DETECTED,
            AlertSeverity.WARNING,
            f"Contradiction detected: {detail}",
            correlation_id=ledger.correlation_id,
            details={"contradiction": detail},
        )
        
        # Check if we've exceeded threshold
        if len(ledger.contradiction_details) >= self.config.max_contradictions_before_halt:
            event.severity = AlertSeverity.HIGH
            event.action_taken = "safe_mode_cautious"
            self._transition_safe_mode(SafeMode.CAUTIOUS)
        
        return event
    
    def transition_safe_mode(self, mode: SafeMode, reason: str = "") -> IntegrityEvent:
        """Manually transition to a safe mode."""
        return self._transition_safe_mode(mode, reason)
    
    def reset(self) -> None:
        """Reset monitor state."""
        self._safe_mode = SafeMode.NORMAL
        self._halt_requested = False
        self._events.clear()
        self._active_ledgers.clear()
    
    def get_events(
        self,
        correlation_id: UUID | None = None,
        severity: AlertSeverity | None = None,
        limit: int = 100,
    ) -> list[IntegrityEvent]:
        """Query recorded events."""
        events = self._events
        
        if correlation_id:
            events = [e for e in events if e.correlation_id == correlation_id]
        if severity:
            events = [e for e in events if e.severity == severity]
        
        return events[-limit:]
    
    # -------------------------------------------------------------------------
    # Internal methods
    # -------------------------------------------------------------------------
    
    def _handle_northbound(self, message: BusMessage) -> None:
        """Handle northbound (telemetry) messages."""
        # Check for L1 veto
        if message.source_layer == LayerSource.LAYER_1:
            event = self.process_veto(message.packet, message.correlation_id)
            if event:
                self._emit_event(event)
        
        # Check budget for associated ledger
        ledger = self._active_ledgers.get(message.correlation_id)
        if ledger:
            event = self.check_budget(ledger)
            if event:
                self._emit_event(event)
    
    def _handle_southbound(self, message: BusMessage) -> None:
        """Handle southbound (directive) messages."""
        # Monitor directives for policy compliance
        pass  # Extension point
    
    def _create_event(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        correlation_id: UUID | None = None,
        source_layer: LayerSource | None = None,
        details: dict[str, Any] | None = None,
        action: str | None = None,
    ) -> IntegrityEvent:
        """Create and record an event."""
        self._event_counter += 1
        event = IntegrityEvent(
            event_id=f"evt_{self._event_counter:06d}",
            alert_type=alert_type,
            severity=severity,
            message=message,
            correlation_id=correlation_id,
            source_layer=source_layer,
            details=details or {},
            action_taken=action,
        )
        self._events.append(event)
        return event
    
    def _emit_event(self, event: IntegrityEvent) -> None:
        """Emit event to callback if configured."""
        if self._on_alert:
            self._on_alert(event)
    
    def _revoke_all_tokens(self, ledger: EpisodeLedger) -> None:
        """Revoke all active tokens in ledger."""
        for token_id, token in ledger.active_tokens.items():
            if not token.revoked:
                token.revoked = True
    
    def _transition_safe_mode(
        self,
        mode: SafeMode,
        reason: str = "",
    ) -> IntegrityEvent:
        """Transition to new safe mode."""
        old_mode = self._safe_mode
        self._safe_mode = mode
        
        return self._create_event(
            AlertType.SAFE_MODE_TRIGGERED,
            AlertSeverity.HIGH if mode in {SafeMode.RESTRICTED, SafeMode.HALTED} else AlertSeverity.WARNING,
            f"Safe mode transition: {old_mode.value} → {mode.value}" + (f" ({reason})" if reason else ""),
            details={
                "old_mode": old_mode.value,
                "new_mode": mode.value,
                "reason": reason,
            },
            action=f"safe_mode_{mode.value}",
        )
    
    def _is_veto_packet(self, packet: Any) -> bool:
        """Check if packet is a constitutional veto."""
        # Check for IntegrityAlert with veto type
        try:
            if hasattr(packet, 'header'):
                if packet.header.packet_type == PacketType.INTEGRITY_ALERT:
                    payload = packet.payload if hasattr(packet, 'payload') else {}
                    return payload.get('alert_type') == 'CONSTITUTIONAL_VETO'
            elif isinstance(packet, dict):
                return packet.get('alert_type') == 'CONSTITUTIONAL_VETO'
        except Exception:
            pass
        return False
    
    def _extract_veto_details(self, packet: Any) -> dict[str, Any]:
        """Extract details from veto packet."""
        try:
            if hasattr(packet, 'payload'):
                return dict(packet.payload)
            elif isinstance(packet, dict):
                return {k: v for k, v in packet.items() if k != 'header'}
        except Exception:
            pass
        return {}


def create_monitor(
    config: MonitorConfig | None = None,
    on_alert: Callable[[IntegrityEvent], None] | None = None,
) -> IntegrityMonitor:
    """Factory for integrity monitor."""
    return IntegrityMonitor(config=config, on_alert=on_alert)

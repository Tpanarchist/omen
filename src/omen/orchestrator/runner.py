"""
Episode Runner — Executes compiled episodes step-by-step.

Coordinates layer invocation, bus routing, and ledger updates.

Spec: OMEN.md §10.4, §11.4
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from omen.vocabulary import LayerSource, PacketType
from omen.buses import NorthboundBus, SouthboundBus, BusMessage
from omen.layers import LayerInput, LayerOutput
from omen.compiler import CompiledEpisode, CompiledStep
from omen.orchestrator.ledger import EpisodeLedger, BudgetState
from omen.orchestrator.pool import LayerPool


# =============================================================================
# RUN RESULT
# =============================================================================

@dataclass
class StepResult:
    """Result of executing a single step."""
    step_id: str
    layer: LayerSource
    success: bool
    output: LayerOutput | None = None
    packets_emitted: int = 0
    error: str | None = None
    duration_seconds: float = 0.0


@dataclass
class EpisodeResult:
    """Result of executing a complete episode."""
    correlation_id: UUID
    template_id: str
    success: bool
    steps_completed: list[StepResult] = field(default_factory=list)
    final_step: str | None = None
    total_duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)
    ledger_summary: dict[str, Any] = field(default_factory=dict)
    
    @property
    def step_count(self) -> int:
        return len(self.steps_completed)


# =============================================================================
# EPISODE RUNNER
# =============================================================================

class EpisodeRunner:
    """
    Executes compiled episodes through the layer pool.
    
    Handles:
    - Step-by-step execution
    - Layer invocation
    - Bus routing
    - Ledger updates
    - Error handling
    """
    
    def __init__(
        self,
        layer_pool: LayerPool,
        northbound_bus: NorthboundBus | None = None,
        southbound_bus: SouthboundBus | None = None,
        max_steps: int = 100,  # Safety limit
    ):
        """
        Initialize runner.
        
        Args:
            layer_pool: Pool of layer instances
            northbound_bus: Bus for telemetry (optional)
            southbound_bus: Bus for directives (optional)
            max_steps: Maximum steps before forced termination
        """
        self.layer_pool = layer_pool
        self.northbound_bus = northbound_bus or NorthboundBus()
        self.southbound_bus = southbound_bus or SouthboundBus()
        self.max_steps = max_steps
    
    def run(
        self,
        episode: CompiledEpisode,
        ledger: EpisodeLedger,
        initial_packets: list[Any] | None = None,
    ) -> EpisodeResult:
        """
        Run a compiled episode to completion.
        
        Args:
            episode: The compiled episode to execute
            ledger: Ledger for state tracking
            initial_packets: Optional initial packets to seed execution
        
        Returns:
            EpisodeResult with execution details
        """
        start_time = datetime.now()
        step_results: list[StepResult] = []
        errors: list[str] = []
        
        # Initialize
        current_step_id = episode.entry_step
        current_packets = list(initial_packets) if initial_packets else []
        steps_executed = 0
        
        # Execute steps
        while current_step_id and steps_executed < self.max_steps:
            step = episode.get_step(current_step_id)
            if step is None:
                errors.append(f"Step not found: {current_step_id}")
                break
            
            # Mark step as started
            ledger.start_step(current_step_id)
            
            # Execute step
            step_result = self._execute_step(
                step=step,
                episode=episode,
                ledger=ledger,
                input_packets=current_packets,
            )
            step_results.append(step_result)
            steps_executed += 1
            
            # Update ledger
            ledger.complete_step(current_step_id)
            if step_result.error:
                ledger.add_error(step_result.error)
                errors.append(step_result.error)
            
            # Check for termination
            if not step_result.success:
                break
            
            if current_step_id in episode.exit_steps:
                # Reached an exit step - episode complete
                break
            
            # Determine next step
            current_step_id = self._select_next_step(step, step_result)
            
            # Collect packets for next step
            if step_result.output:
                current_packets = step_result.output.packets
            else:
                current_packets = []
        
        # Check for step limit
        if steps_executed >= self.max_steps:
            errors.append(f"Max steps ({self.max_steps}) exceeded")
        
        # Complete episode
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        ledger.complete_episode()
        
        return EpisodeResult(
            correlation_id=episode.correlation_id,
            template_id=episode.template_id.value,
            success=len(errors) == 0 and steps_executed > 0,
            steps_completed=step_results,
            final_step=step_results[-1].step_id if step_results else None,
            total_duration_seconds=duration,
            errors=errors,
            ledger_summary=ledger.to_summary(),
        )
    
    def _execute_step(
        self,
        step: CompiledStep,
        episode: CompiledEpisode,
        ledger: EpisodeLedger,
        input_packets: list[Any],
    ) -> StepResult:
        """Execute a single step."""
        start_time = datetime.now()
        
        # Check if layer exists
        if not self.layer_pool.has_layer(step.owner_layer):
            return StepResult(
                step_id=step.step_id,
                layer=step.owner_layer,
                success=False,
                error=f"Layer {step.owner_layer.value} not in pool",
            )
        
        # Skip if no packet type (terminal/transition step)
        if step.packet_type is None:
            duration = (datetime.now() - start_time).total_seconds()
            return StepResult(
                step_id=step.step_id,
                layer=step.owner_layer,
                success=True,
                packets_emitted=0,
                duration_seconds=duration,
            )
        
        # Build layer input
        layer_input = LayerInput(
            packets=input_packets,
            correlation_id=episode.correlation_id,
            campaign_id=episode.campaign_id,
            context={
                "step_id": step.step_id,
                "template_id": episode.template_id.value,
                "mcp_bindings": step.mcp_bindings,
            },
        )
        
        # Invoke layer
        output = self.layer_pool.invoke_layer(step.owner_layer, layer_input)
        
        if output is None:
            return StepResult(
                step_id=step.step_id,
                layer=step.owner_layer,
                success=False,
                error=f"Layer {step.owner_layer.value} invocation failed",
            )
        
        # Route output packets via buses
        self._route_packets(output, ledger)
        
        # Update ledger with consumption
        self._update_ledger_from_output(output, ledger)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return StepResult(
            step_id=step.step_id,
            layer=step.owner_layer,
            success=output.success,
            output=output,
            packets_emitted=len(output.packets),
            error="; ".join(output.errors) if output.errors else None,
            duration_seconds=duration,
        )
    
    def _route_packets(
        self,
        output: LayerOutput,
        ledger: EpisodeLedger,
    ) -> None:
        """Route output packets via appropriate buses."""
        for packet in output.packets:
            # Determine routing direction based on source layer
            message = BusMessage(
                packet=packet,
                source_layer=output.layer,
                target_layer=None,  # Broadcast
                correlation_id=output.correlation_id,
            )
            
            # Route based on packet type and source
            # Observations/Results go northbound (telemetry up)
            # Directives go southbound (commands down)
            packet_type = self._get_packet_type(packet)
            
            if packet_type in {
                PacketType.OBSERVATION,
                PacketType.TASK_RESULT,
                PacketType.BELIEF_UPDATE,
                PacketType.ESCALATION,
                PacketType.INTEGRITY_ALERT,
            }:
                self.northbound_bus.publish(message)
            elif packet_type in {
                PacketType.DECISION,
                PacketType.VERIFICATION_PLAN,
                PacketType.TOOL_AUTHORIZATION,
                PacketType.TASK_DIRECTIVE,
            }:
                self.southbound_bus.publish(message)
            
            # Track evidence refs
            if hasattr(packet, 'evidence_refs'):
                for ref in packet.evidence_refs:
                    ledger.add_evidence(ref)
    
    def _update_ledger_from_output(
        self,
        output: LayerOutput,
        ledger: EpisodeLedger,
    ) -> None:
        """Update ledger based on layer output."""
        # Estimate token consumption (rough heuristic)
        # In production, this would come from actual LLM response
        if output.raw_response:
            estimated_tokens = len(output.raw_response) // 4
            ledger.budget.consume(tokens=estimated_tokens)
    
    def _select_next_step(
        self,
        current_step: CompiledStep,
        result: StepResult,
    ) -> str | None:
        """Select the next step based on current step and result."""
        if not current_step.next_steps:
            return None
        
        # For now, simple linear progression
        # Future: Use decision outcome to select branch
        # (e.g., VERIFY_FIRST -> verification step, ACT -> execute step)
        return current_step.next_steps[0]
    
    def _get_packet_type(self, packet: Any) -> PacketType | None:
        """Extract packet type from packet."""
        try:
            return packet.header.packet_type
        except AttributeError:
            # Try dict access for parsed packets
            if isinstance(packet, dict):
                pt = packet.get("packet_type") or packet.get("type")
                if pt:
                    try:
                        return PacketType(pt)
                    except ValueError:
                        pass
            return None


# =============================================================================
# FACTORY
# =============================================================================

def create_runner(
    layer_pool: LayerPool,
    northbound_bus: NorthboundBus | None = None,
    southbound_bus: SouthboundBus | None = None,
    max_steps: int = 100,
) -> EpisodeRunner:
    """Factory for episode runner."""
    return EpisodeRunner(
        layer_pool=layer_pool,
        northbound_bus=northbound_bus,
        southbound_bus=southbound_bus,
        max_steps=max_steps,
    )

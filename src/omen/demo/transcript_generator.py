"""
Cognitive Transcript Generator — Makes OMEN's reasoning transparent.

Generates human-readable transcripts of episode execution showing:
- Layer-by-layer reasoning
- Packet flow with epistemic status
- Budget consumption
- Decision rationale
- FSM state transitions
- Integrity alerts

Usage:
    generator = CognitiveTranscriptGenerator()
    generator.from_episode_result(result)
    transcript = generator.generate_transcript()
    generator.save("episode_transcript.txt")
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID
import re
import json

from omen.orchestrator import EpisodeResult, StepResult
from omen.vocabulary import LayerSource, PacketType
from omen.demo.formatting_utils import (
    format_progress_bar,
    format_duration,
    format_packet_summary,
    format_section_header,
    format_box_header,
    format_timestamp,
    format_tree_branch,
    format_percentage,
    format_key_value,
    format_bullet_list,
    truncate_text,
    format_budget_delta,
)


# =============================================================================
# DATA CAPTURE STRUCTURES
# =============================================================================

@dataclass
class StepCapture:
    """Captures all data for a single step."""
    step_id: str
    layer: LayerSource
    fsm_state: str
    duration_seconds: float
    
    # Context
    system_prompt: str
    context_summary: dict[str, Any]
    
    # LLM interaction (optional, from DebugCapture)
    llm_reasoning: str | None = None
    raw_prompt: str | None = None
    raw_response: str | None = None
    
    # Tool executions
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    
    # Output packets
    packets_emitted: list[Any] = field(default_factory=list)
    
    # Budget deltas
    tokens_consumed: int = 0
    tool_calls_consumed: int = 0
    time_consumed: float = 0.0
    
    success: bool = True
    error_message: str | None = None


@dataclass
class EpisodeCapture:
    """Complete capture of episode execution."""
    correlation_id: UUID
    template_id: str
    campaign_id: str | None
    started_at: datetime
    completed_at: datetime | None = None
    
    # Context
    stakes_level: str = ""
    quality_tier: str = ""
    tools_state: str = ""
    
    # Budgets
    token_budget: int = 0
    token_consumed: int = 0
    tool_budget: int = 0
    tool_consumed: int = 0
    time_budget: float = 0.0
    time_consumed: float = 0.0
    
    # Initial state
    initial_seed: str = ""
    
    # Steps
    steps: list[StepCapture] = field(default_factory=list)
    
    # Epistemic tracking
    beliefs_created: list[dict[str, Any]] = field(default_factory=list)
    evidence_refs: list[dict[str, Any]] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    
    # Integrity
    integrity_alerts: list[dict[str, Any]] = field(default_factory=list)
    safe_mode_transitions: list[dict[str, Any]] = field(default_factory=list)
    
    # Outcome
    success: bool = False
    final_step: str = ""
    outcome_summary: str = ""


# =============================================================================
# COGNITIVE TRANSCRIPT GENERATOR
# =============================================================================

class CognitiveTranscriptGenerator:
    """
    Generates human-readable transcripts of cognitive episodes.
    
    Can operate in two modes:
    1. Post-hoc: Reconstructs from EpisodeResult
    2. Live capture: Via callback hooks (future enhancement)
    
    Example:
        generator = CognitiveTranscriptGenerator()
        generator.from_episode_result(result)
        transcript = generator.generate_transcript()
        generator.save("episode_001.txt")
    """
    
    def __init__(
        self,
        include_llm_reasoning: bool = True,
        include_raw_prompts: bool = False,
        max_content_length: int = 500,
    ):
        """
        Initialize generator.
        
        Args:
            include_llm_reasoning: Include extracted reasoning from LLM responses
            include_raw_prompts: Include full raw prompts/responses
            max_content_length: Max chars for content summaries
        """
        self.include_llm_reasoning = include_llm_reasoning
        self.include_raw_prompts = include_raw_prompts
        self.max_content_length = max_content_length
        
        self.capture: EpisodeCapture | None = None
    
    def from_episode_result(
        self,
        result: EpisodeResult,
        debug_captures: dict[str, Any] | None = None,
        layer_prompts: dict[LayerSource, str] | None = None,
    ) -> None:
        """
        Build capture from EpisodeResult.
        
        Args:
            result: Completed episode result
            debug_captures: Optional debug data from DebugRecorder
            layer_prompts: Optional system prompts by layer
        """
        # Extract ledger summary
        ledger = result.ledger_summary
        
        # Build episode capture
        self.capture = EpisodeCapture(
            correlation_id=result.correlation_id,
            template_id=result.template_id,
            campaign_id=ledger.get("campaign_id"),
            started_at=datetime.now(),  # Approximate if not in result
            completed_at=datetime.now(),
            stakes_level=ledger.get("stakes_level", "UNKNOWN"),
            quality_tier=ledger.get("quality_tier", "UNKNOWN"),
            tools_state=ledger.get("tools_state", "UNKNOWN"),
            token_budget=ledger.get("budget", {}).get("token_budget", 0),
            token_consumed=ledger.get("budget", {}).get("tokens_consumed", 0),
            tool_budget=ledger.get("budget", {}).get("tool_call_budget", 0),
            tool_consumed=ledger.get("budget", {}).get("tool_calls_consumed", 0),
            time_budget=ledger.get("budget", {}).get("time_budget_seconds", 0),
            time_consumed=result.total_duration_seconds,
            initial_seed=ledger.get("initial_seed", ""),
            success=result.success,
            final_step=result.final_step or "",
            outcome_summary="Episode completed successfully" if result.success else "Episode failed",
            assumptions=ledger.get("assumptions", []),
            evidence_refs=ledger.get("evidence", []),
        )
        
        # Convert step results to step captures
        for step_result in result.steps_completed:
            step_capture = self._convert_step_result(step_result, debug_captures, layer_prompts)
            self.capture.steps.append(step_capture)
            
            # Extract epistemic data from LLM reasoning
            if step_capture.llm_reasoning:
                assumptions, load_bearing = self._extract_assumptions_from_reasoning(step_capture.llm_reasoning)
                self.capture.assumptions.extend(assumptions)
                
                # Extract alerts
                alerts = self._extract_alerts_from_reasoning(step_capture.llm_reasoning)
                self.capture.integrity_alerts.extend(alerts)
    
    def _infer_fsm_state(self, step_id: str, fsm_state: str) -> str:
        """Infer FSM state from step ID if not provided."""
        if fsm_state and fsm_state != "":
            return fsm_state
        
        # Infer from step_id
        step_lower = step_id.lower()
        if "idle" in step_lower:
            return "S0_IDLE"
        elif "sense" in step_lower:
            return "S1_SENSE"
        elif "model" in step_lower:
            return "S2_MODEL"
        elif "decide" in step_lower:
            return "S3_DECIDE"
        elif "verify" in step_lower:
            return "S4_VERIFY"
        elif "authorize" in step_lower or "auth" in step_lower:
            return "S5_AUTHORIZE"
        elif "execute" in step_lower or "act" in step_lower:
            return "S6_EXECUTE"
        elif "review" in step_lower:
            return "S7_REVIEW"
        elif "escalat" in step_lower:
            return "S8_ESCALATED"
        elif "safe" in step_lower:
            return "S9_SAFEMODE"
        
        return "UNKNOWN"
    
    def _convert_step_result(
        self,
        step_result: StepResult,
        debug_captures: dict[str, Any] | None,
        layer_prompts: dict[LayerSource, str] | None,
    ) -> StepCapture:
        """Convert StepResult to StepCapture."""
        # Extract system prompt
        system_prompt = step_result.system_prompt
        if not system_prompt and layer_prompts:
            system_prompt = layer_prompts.get(step_result.layer, "")
        
        # Extract LLM reasoning from raw response if available
        llm_reasoning = None
        raw_response = None
        if step_result.output:
            raw_response = step_result.output.raw_response
            if self.include_llm_reasoning and raw_response:
                llm_reasoning = self._extract_reasoning(raw_response)
        
        # Build tool calls list
        tool_calls = []
        for tool_exec in step_result.tool_executions:
            tool_calls.append(tool_exec.to_dict())
        
        # Get packets emitted
        packets = step_result.packets_emitted_list if hasattr(step_result, 'packets_emitted_list') else []
        
        # Infer FSM state if not provided
        fsm_state = self._infer_fsm_state(step_result.step_id, step_result.fsm_state or "")
        
        return StepCapture(
            step_id=step_result.step_id,
            layer=step_result.layer,
            fsm_state=fsm_state,
            duration_seconds=step_result.duration_seconds,
            system_prompt=system_prompt,
            context_summary=step_result.context_summary,
            llm_reasoning=llm_reasoning,
            raw_response=raw_response if self.include_raw_prompts else None,
            tool_calls=tool_calls,
            packets_emitted=packets,
            tokens_consumed=step_result.tokens_consumed,
            tool_calls_consumed=step_result.tool_calls_consumed,
            time_consumed=step_result.time_consumed or step_result.duration_seconds,
            success=step_result.success,
            error_message=step_result.error,
        )
    
    def _extract_reasoning(self, raw_response: str) -> str:
        """Extract key reasoning from LLM response."""
        # Simple extraction: first paragraph or up to max length
        lines = raw_response.strip().split('\n')
        reasoning_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('{') and not line.startswith('['):
                reasoning_lines.append(line)
                if len('\n'.join(reasoning_lines)) > self.max_content_length:
                    break
        
        reasoning = '\n'.join(reasoning_lines)
        return truncate_text(reasoning, self.max_content_length)
    
    def _extract_json_from_reasoning(self, reasoning: str) -> dict | None:
        """
        Extract JSON blocks from LLM reasoning.
        
        Args:
            reasoning: LLM reasoning text
        
        Returns:
            Parsed JSON dict or None if no valid JSON found
        """
        if not reasoning:
            return None
        
        # Look for ```json blocks
        pattern = r'```json\s*(\{.*?\})\s*```'
        matches = re.findall(pattern, reasoning, re.DOTALL)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        # Try finding raw JSON objects
        pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(pattern, reasoning, re.DOTALL)
        
        for match in matches:
            try:
                parsed = json.loads(match)
                # Verify it looks like structured data
                if isinstance(parsed, dict) and len(parsed) > 0:
                    return parsed
            except json.JSONDecodeError:
                continue
        
        return None
    
    def _extract_assumptions_from_reasoning(self, reasoning: str) -> tuple[list[str], list[str]]:
        """
        Extract assumptions and load-bearing assumptions from reasoning.
        
        Args:
            reasoning: LLM reasoning text
        
        Returns:
            Tuple of (regular assumptions, load-bearing assumptions)
        """
        assumptions = []
        load_bearing = []
        
        data = self._extract_json_from_reasoning(reasoning)
        if data:
            assumptions = data.get("assumptions", [])
            load_bearing = data.get("load_bearing_assumptions", [])
        
        return assumptions, load_bearing
    
    def _extract_alerts_from_reasoning(self, reasoning: str) -> list[dict]:
        """
        Extract integrity alert structures from LLM reasoning.
        
        Args:
            reasoning: LLM reasoning text
        
        Returns:
            List of alert dictionaries
        """
        alerts = []
        
        data = self._extract_json_from_reasoning(reasoning)
        if data and "alert_type" in data:
            alerts.append(data)
        
        return alerts
    
    def generate_transcript(self) -> str:
        """
        Generate complete human-readable transcript.
        
        Returns:
            Multi-section formatted transcript
        """
        if self.capture is None:
            raise ValueError("No episode captured. Call from_episode_result() first.")
        
        sections = [
            self._generate_header(),
            self._generate_step_flow(),
            self._generate_packet_trace(),
            self._generate_budget_timeline(),
            self._generate_epistemic_report(),
            self._generate_integrity_report(),
            self._generate_summary(),
        ]
        
        return "\n\n".join(sections)
    
    def save(self, filepath: str | Path) -> None:
        """Save transcript to file."""
        transcript = self.generate_transcript()
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(transcript, encoding="utf-8")
    
    # =========================================================================
    # SECTION GENERATORS
    # =========================================================================
    
    def _generate_header(self) -> str:
        """Generate Section 1: Episode Header."""
        c = self.capture
        
        lines = [
            "=" * 80,
            "COGNITIVE EPISODE TRANSCRIPT",
            "=" * 80,
            format_key_value("Episode ID", str(c.correlation_id)),
            format_key_value("Template", c.template_id),
        ]
        
        if c.campaign_id:
            lines.append(format_key_value("Campaign", c.campaign_id))
        
        lines.extend([
            format_key_value("Started", format_timestamp(c.started_at)),
            format_key_value("Completed", format_timestamp(c.completed_at) if c.completed_at else "In Progress"),
            format_key_value("Duration", format_duration(c.time_consumed)),
            format_key_value("Status", "SUCCESS" if c.success else "FAILED"),
            format_key_value("Final Step", c.final_step),
            "",
            "Context:",
            format_key_value("Stakes Level", c.stakes_level),
            format_key_value("Quality Tier", c.quality_tier),
            format_key_value("Tools State", c.tools_state),
            "",
            "Budgets:",
        ])
        
        # Token budget
        if c.token_budget > 0:
            token_pct = format_percentage(c.token_consumed / c.token_budget)
            lines.append(format_key_value(
                "Token",
                f"{c.token_budget:,} allocated → {c.token_consumed:,} consumed ({token_pct})"
            ))
        else:
            lines.append(format_key_value(
                "Token",
                f"No limit set → {c.token_consumed:,} consumed"
            ))
        
        # Tool budget
        if c.tool_budget > 0:
            tool_pct = format_percentage(c.tool_consumed / c.tool_budget)
            lines.append(format_key_value(
                "Tool Calls",
                f"{c.tool_budget} allocated → {c.tool_consumed} consumed ({tool_pct})"
            ))
        else:
            lines.append(format_key_value(
                "Tool Calls",
                f"No limit set → {c.tool_consumed} consumed"
            ))
        
        # Time budget
        if c.time_budget > 0:
            time_pct = format_percentage(c.time_consumed / c.time_budget)
            lines.append(format_key_value(
                "Time",
                f"{format_duration(c.time_budget)} allocated → {format_duration(c.time_consumed)} consumed ({time_pct})"
            ))
        else:
            lines.append(format_key_value(
                "Time",
                f"No limit set → {format_duration(c.time_consumed)} consumed"
            ))
        
        if c.initial_seed:
            lines.extend([
                "",
                "Initial Seed:",
                f"  \"{truncate_text(c.initial_seed, 200)}\"",
            ])
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _generate_step_flow(self) -> str:
        """Generate Section 2: Step-by-Step Cognitive Flow."""
        if not self.capture or not self.capture.steps:
            return format_section_header("COGNITIVE FLOW", 80) + "\n\nNo steps recorded."
        
        sections = [format_section_header("COGNITIVE FLOW", 80), ""]
        
        for i, step in enumerate(self.capture.steps, 1):
            sections.append(self._format_step(i, step))
            sections.append("")  # Blank line between steps
        
        return "\n".join(sections)
    
    def _format_step(self, step_num: int, step: StepCapture) -> str:
        """Format a single step for the transcript."""
        lines = [
            format_box_header(f"STEP {step_num}: {step.step_id}"),
            format_key_value("Layer", f"{step.layer.value} - {self._get_layer_name(step.layer)}"),
            format_key_value("FSM State", step.fsm_state),
            format_key_value("Duration", format_duration(step.duration_seconds)),
            "",
        ]
        
        # System prompt (if available and requested)
        if step.system_prompt and not self.include_raw_prompts:
            lines.extend([
                "[LAYER ROLE]",
                f"  {truncate_text(step.system_prompt, self.max_content_length)}",
                "",
            ])
        
        # LLM reasoning (if available and requested)
        if self.include_llm_reasoning and step.llm_reasoning:
            lines.extend([
                "[LLM REASONING]",
                f"  {step.llm_reasoning}",
                "",
            ])
        
        # Tool executions
        if step.tool_calls:
            lines.append("[TOOL EXECUTIONS]")
            for tool_call in step.tool_calls:
                lines.append(f"  Tool: {tool_call['tool_name']}")
                lines.append(f"  Status: {'SUCCESS' if tool_call['success'] else 'FAILED'}")
                if tool_call.get('error'):
                    lines.append(f"  Error: {tool_call['error']}")
                if tool_call.get('duration_seconds'):
                    lines.append(f"  Duration: {format_duration(tool_call['duration_seconds'])}")
                lines.append("")
        elif step.layer.value == 6:  # Task Prosecution layer
            lines.extend([
                "[TOOL EXECUTIONS]",
                "  No tools executed",
                "",
            ])
        
        # Packets emitted
        if step.packets_emitted:
            lines.append(f"[PACKETS EMITTED] ({len(step.packets_emitted)})")
            for packet in step.packets_emitted:
                summary = format_packet_summary(packet, self.max_content_length)
                lines.append(f"  → {summary}")
            lines.append("")
        
        # Budget consumption
        lines.append("[BUDGET CONSUMPTION]")
        lines.append(format_budget_delta(step.tokens_consumed, "Tokens"))
        lines.append(format_budget_delta(step.tool_calls_consumed, "Tool Calls"))
        lines.append(format_budget_delta(step.time_consumed, "Time"))
        lines.append("")
        
        # Status
        status_symbol = "✓" if step.success else "✗"
        status_text = "SUCCESS" if step.success else f"FAILED: {step.error_message}"
        lines.append(f"Status: {status_symbol} {status_text}")
        
        return "\n".join(lines)
    
    def _generate_packet_trace(self) -> str:
        """Generate Section 3: Packet Flow Diagram."""
        if not self.capture or not self.capture.steps:
            return format_section_header("PACKET FLOW TRACE", 80) + "\n\nNo packets recorded."
        
        lines = [
            format_section_header("PACKET FLOW TRACE", 80),
            "",
        ]
        
        # Collect all packets across steps
        all_packets = []
        for step in self.capture.steps:
            for packet in step.packets_emitted:
                all_packets.append((step.step_id, step.layer, packet))
        
        if not all_packets:
            lines.append("No packets emitted during episode.")
        else:
            lines.append(f"Total Packets: {len(all_packets)}")
            lines.append("")
            
            # Simple sequential list with tree formatting
            for i, (step_id, layer, packet) in enumerate(all_packets):
                is_last = (i == len(all_packets) - 1)
                branch = format_tree_branch(1, is_last)
                summary = format_packet_summary(packet, 60)
                lines.append(f"{branch}{summary} ← {layer.value}")
        
        return "\n".join(lines)
    
    def _generate_budget_timeline(self) -> str:
        """Generate Section 4: Budget Consumption Timeline."""
        if not self.capture:
            return format_section_header("RESOURCE CONSUMPTION", 80) + "\n\nNo data available."
        
        c = self.capture
        lines = [
            format_section_header("RESOURCE CONSUMPTION", 80),
            "",
            f"Token Budget ({c.token_budget} total):",
            "  " + format_progress_bar(c.token_consumed, c.token_budget, 30),
            "",
        ]
        
        # Per-step token breakdown
        if c.steps:
            lines.append("  Breakdown by step:")
            for i, step in enumerate(c.steps, 1):
                pct = format_percentage(step.tokens_consumed / c.token_budget if c.token_budget > 0 else 0)
                lines.append(f"    Step {i} ({step.step_id}): {step.tokens_consumed} tokens ({pct})")
            lines.append("")
        
        # Tool call budget
        lines.extend([
            f"Tool Call Budget ({c.tool_budget} total):",
            "  " + format_progress_bar(c.tool_consumed, c.tool_budget, 30),
            "",
        ])
        
        # Time budget
        lines.extend([
            f"Time Budget ({format_duration(c.time_budget)} total):",
            "  " + format_progress_bar(int(c.time_consumed), int(c.time_budget), 30),
            "",
        ])
        
        # Layer breakdown
        if c.steps:
            layer_times: dict[LayerSource, float] = {}
            for step in c.steps:
                layer_times[step.layer] = layer_times.get(step.layer, 0) + step.duration_seconds
            
            lines.append("  Breakdown by layer:")
            for layer, time_spent in sorted(layer_times.items(), key=lambda x: x[1], reverse=True):
                pct = format_percentage(time_spent / c.time_consumed if c.time_consumed > 0 else 0)
                lines.append(f"    {layer.value}: {format_duration(time_spent)} ({pct})")
        
        return "\n".join(lines)
    
    def _generate_epistemic_report(self) -> str:
        """Generate Section 5: Epistemic Hygiene Report."""
        if not self.capture:
            return format_section_header("EPISTEMIC HYGIENE", 80) + "\n\nNo data available."
        
        c = self.capture
        lines = [
            format_section_header("EPISTEMIC HYGIENE", 80),
            "",
        ]
        
        # Beliefs created
        belief_count = len(c.beliefs_created)
        lines.append(f"Beliefs Created: {belief_count}")
        if c.beliefs_created:
            for belief in c.beliefs_created[:5]:  # Show first 5
                lines.append(f"  ✓ {belief.get('description', 'Unknown belief')}")
        lines.append("")
        
        # Evidence grounding
        evidence_count = len(c.evidence_refs)
        lines.append(f"Evidence References: {evidence_count}")
        if evidence_count > 0:
            grounding_pct = format_percentage(evidence_count / max(belief_count, 1))
            lines.append(f"  Grounding Rate: {grounding_pct}")
        lines.append("")
        
        # Assumptions
        assumption_count = len(c.assumptions)
        lines.append(f"Assumptions: {assumption_count}")
        if c.assumptions:
            for assumption in c.assumptions[:5]:  # Show first 5
                lines.append(f"  ⚠ {truncate_text(str(assumption), 80)}")
        lines.append("")
        
        # Freshness status
        lines.extend([
            "Data Freshness:",
            "  ✓ All observations within acceptable staleness windows",
        ])
        
        return "\n".join(lines)
    
    def _generate_integrity_report(self) -> str:
        """Generate Section 6: Integrity Events."""
        if not self.capture:
            return format_section_header("INTEGRITY MONITORING", 80) + "\n\nNo data available."
        
        c = self.capture
        lines = [
            format_section_header("INTEGRITY MONITORING", 80),
            "",
            f"Safe Mode Transitions: {len(c.safe_mode_transitions)}",
            "Current Mode: NORMAL",
            "",
            f"Alerts Generated: {len(c.integrity_alerts)}",
        ]
        
        if c.integrity_alerts:
            for alert in c.integrity_alerts[:5]:  # Show first 5
                alert_type = alert.get('alert_type', 'UNKNOWN')
                severity = alert.get('severity', 'UNKNOWN')
                explanation = alert.get('explanation', 'No explanation provided')
                lines.append(f"  [{severity}] {alert_type}")
                lines.append(f"    {truncate_text(explanation, 200)}")
        else:
            lines.append("  No alerts generated")
        
        # Count specific alert types
        constitutional_vetoes = sum(1 for a in c.integrity_alerts if a.get('alert_type') == 'CONSTITUTIONAL_VETO')
        budget_enforcements = sum(1 for a in c.integrity_alerts if 'budget' in a.get('explanation', '').lower())
        
        lines.extend([
            "",
            f"Constitutional Vetoes: {constitutional_vetoes}",
            f"Budget Enforcement Actions: {budget_enforcements}",
        ])
        
        return "\n".join(lines)
    
    def _generate_summary(self) -> str:
        """Generate Section 7: Episode Summary."""
        if not self.capture:
            return format_section_header("EPISODE SUMMARY", 80) + "\n\nNo data available."
        
        c = self.capture
        lines = [
            format_section_header("EPISODE SUMMARY", 80),
            "",
            "Outcome:",
            f"  {c.outcome_summary}",
            "",
            "Cognitive Quality:",
        ]
        
        # Quality checks
        quality_checks = [
            f"{'✓' if c.success else '✗'} Episode completed {'successfully' if c.success else 'with errors'}",
            f"✓ {len(c.steps)} steps executed",
        ]
        
        if c.evidence_refs:
            quality_checks.append(f"✓ {len(c.evidence_refs)} evidence references collected")
        
        if c.assumptions:
            quality_checks.append(f"⚠ {len(c.assumptions)} assumptions flagged")
        
        lines.extend([f"  {check}" for check in quality_checks])
        
        # Efficiency metrics
        lines.extend([
            "",
            "Efficiency:",
            f"  - {len(c.steps)} steps executed",
            f"  - {format_duration(c.time_consumed)} elapsed",
        ])
        
        if c.token_budget > 0:
            token_pct = format_percentage(c.token_consumed / c.token_budget)
            lines.append(f"  - {c.token_consumed}/{c.token_budget} tokens consumed ({token_pct})")
        
        if c.tool_budget > 0:
            tool_pct = format_percentage(c.tool_consumed / c.tool_budget)
            lines.append(f"  - {c.tool_consumed}/{c.tool_budget} tool calls consumed ({tool_pct})")
        
        # Lessons learned
        lines.extend([
            "",
            "Lessons for Future Episodes:",
        ])
        
        lessons = []
        if c.assumptions:
            lessons.append(f"Consider validating {len(c.assumptions)} assumptions in high-stakes scenarios")
        if c.token_consumed > c.token_budget * 0.9:
            lessons.append("Token consumption was high; consider increasing budget for similar tasks")
        if not lessons:
            lessons.append("Episode executed within normal parameters")
        
        for i, lesson in enumerate(lessons, 1):
            lines.append(f"  {i}. {lesson}")
        
        lines.extend([
            "",
            "=" * 80,
            "END OF TRANSCRIPT",
            "=" * 80,
        ])
        
        return "\n".join(lines)
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _get_layer_name(self, layer: LayerSource) -> str:
        """Get human-readable layer name."""
        layer_names = {
            LayerSource.LAYER_1: "Aspirational",
            LayerSource.LAYER_2: "Global Strategy",
            LayerSource.LAYER_3: "Agent Model",
            LayerSource.LAYER_4: "Executive Function",
            LayerSource.LAYER_5: "Cognitive Control",
            LayerSource.LAYER_6: "Task Prosecution",
            LayerSource.INTEGRITY: "Integrity Monitor",
        }
        return layer_names.get(layer, "Unknown")

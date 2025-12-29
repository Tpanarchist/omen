"""
Debug Mode — Verbose logging and response capture for development.

Enables detailed tracing of LLM interactions and packet flow.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from omen.observability.logging import get_logger

logger = get_logger("debug")


@dataclass
class DebugCapture:
    """
    Captures detailed execution data for debugging.
    """
    correlation_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    layer: str = ""
    step_id: str = ""
    
    # LLM interaction
    system_prompt: str = ""
    user_message: str = ""
    raw_response: str = ""
    
    # Parsing
    parsed_packets: list[dict] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)
    
    # Validation
    contract_violations: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "layer": self.layer,
            "step_id": self.step_id,
            "llm": {
                "system_prompt_length": len(self.system_prompt),
                "user_message_length": len(self.user_message),
                "response_length": len(self.raw_response),
            },
            "parsing": {
                "packets_parsed": len(self.parsed_packets),
                "errors": self.parse_errors,
            },
            "validation": {
                "violations": self.contract_violations,
            },
        }
    
    def to_json(self) -> str:
        full_data = {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "layer": self.layer,
            "step_id": self.step_id,
            "system_prompt": self.system_prompt,
            "user_message": self.user_message,
            "raw_response": self.raw_response,
            "parsed_packets": self.parsed_packets,
            "parse_errors": self.parse_errors,
            "contract_violations": self.contract_violations,
        }
        return json.dumps(full_data, indent=2)


class DebugRecorder:
    """
    Records debug information during episode execution.
    
    When enabled, captures full LLM interactions for analysis.
    """
    
    def __init__(
        self,
        enabled: bool = False,
        output_dir: Path | str | None = None,
        log_to_console: bool = True,
    ):
        """
        Initialize debug recorder.
        
        Args:
            enabled: Whether to capture debug data
            output_dir: Directory to save captures (None = don't save)
            log_to_console: Log summaries to console
        """
        self.enabled = enabled
        self.output_dir = Path(output_dir) if output_dir else None
        self.log_to_console = log_to_console
        self._captures: list[DebugCapture] = []
        
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def capture(
        self,
        correlation_id: UUID | str,
        layer: str,
        step_id: str = "",
        system_prompt: str = "",
        user_message: str = "",
        raw_response: str = "",
        parsed_packets: list[dict] | None = None,
        parse_errors: list[str] | None = None,
        contract_violations: list[str] | None = None,
    ) -> DebugCapture | None:
        """
        Capture debug information for a layer invocation.
        
        Returns capture if enabled, None otherwise.
        """
        if not self.enabled:
            return None
        
        capture = DebugCapture(
            correlation_id=str(correlation_id),
            layer=layer,
            step_id=step_id,
            system_prompt=system_prompt,
            user_message=user_message,
            raw_response=raw_response,
            parsed_packets=parsed_packets or [],
            parse_errors=parse_errors or [],
            contract_violations=contract_violations or [],
        )
        
        self._captures.append(capture)
        
        if self.log_to_console:
            self._log_capture(capture)
        
        if self.output_dir:
            self._save_capture(capture)
        
        return capture
    
    def get_captures(
        self,
        correlation_id: str | None = None,
        layer: str | None = None,
    ) -> list[DebugCapture]:
        """Query recorded captures."""
        captures = self._captures
        
        if correlation_id:
            captures = [c for c in captures if c.correlation_id == correlation_id]
        if layer:
            captures = [c for c in captures if c.layer == layer]
        
        return captures
    
    def clear(self) -> None:
        """Clear captured data."""
        self._captures.clear()
    
    def _log_capture(self, capture: DebugCapture) -> None:
        """Log capture summary to console."""
        logger.debug(
            f"Layer {capture.layer} invoked: "
            f"response={len(capture.raw_response)} chars, "
            f"packets={len(capture.parsed_packets)}, "
            f"errors={len(capture.parse_errors)}"
        )
        
        if capture.parse_errors:
            for error in capture.parse_errors:
                logger.warning(f"Parse error: {error}")
        
        if capture.contract_violations:
            for violation in capture.contract_violations:
                logger.warning(f"Contract violation: {violation}")
    
    def _save_capture(self, capture: DebugCapture) -> None:
        """Save capture to file."""
        if not self.output_dir:
            return
        
        filename = f"{capture.correlation_id}_{capture.layer}_{capture.timestamp.strftime('%H%M%S')}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, "w") as f:
            f.write(capture.to_json())


# Global debug recorder
_recorder = DebugRecorder(enabled=False)


def enable_debug(
    output_dir: Path | str | None = None,
    log_to_console: bool = True,
) -> None:
    """Enable debug mode globally."""
    global _recorder
    _recorder = DebugRecorder(
        enabled=True,
        output_dir=output_dir,
        log_to_console=log_to_console,
    )


def disable_debug() -> None:
    """Disable debug mode."""
    global _recorder
    _recorder = DebugRecorder(enabled=False)


def get_debug_recorder() -> DebugRecorder:
    """Get global debug recorder."""
    return _recorder


def is_debug_enabled() -> bool:
    """Check if debug mode is enabled."""
    return _recorder.enabled

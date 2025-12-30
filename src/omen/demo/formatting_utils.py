"""
Formatting Utilities for Cognitive Transcripts.

Provides ASCII art, progress bars, and text formatting helpers for
generating human-readable transcripts of OMEN episode executions.
"""

from typing import Any


def format_progress_bar(consumed: int, total: int, width: int = 20) -> str:
    """
    Generate ASCII progress bar.
    
    Args:
        consumed: Amount consumed
        total: Total available
        width: Character width of bar
    
    Returns:
        Formatted progress bar string with percentage
    
    Example:
        >>> format_progress_bar(75, 100, 20)
        '[███████████████-----] 75.0%'
    """
    if total <= 0:
        return f"[{'-' * width}] 0.0%"
    
    pct = consumed / total
    filled = int(width * pct)
    empty = width - filled
    bar = "█" * filled + "-" * empty
    return f"[{bar}] {pct * 100:.1f}%"


def format_duration(seconds: float) -> str:
    """
    Format duration as human-readable string.
    
    Args:
        seconds: Duration in seconds
    
    Returns:
        Formatted string (e.g., "1.2s", "45ms", "2m 15.3s")
    
    Example:
        >>> format_duration(0.045)
        '45ms'
        >>> format_duration(1.234)
        '1.2s'
        >>> format_duration(135.678)
        '2m 15.7s'
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}m {secs:.1f}s"


def format_packet_summary(packet: Any, max_length: int = 100) -> str:
    """
    Generate concise packet summary.
    
    Args:
        packet: Packet object to summarize
        max_length: Maximum characters for summary
    
    Returns:
        Brief packet description
    """
    # Extract packet type properly
    packet_type = _get_packet_type(packet)
    
    # Try to get packet ID if available
    packet_id = "unknown"
    if isinstance(packet, dict):
        packet_id = packet.get("mcp", {}).get("packet_id", "unknown")
        if isinstance(packet_id, str) and len(packet_id) > 8:
            packet_id = packet_id[:8]
    elif hasattr(packet, "mcp") and hasattr(packet.mcp, "packet_id"):
        packet_id = str(packet.mcp.packet_id)[:8]
    elif hasattr(packet, "packet_id"):
        packet_id = str(packet.packet_id)[:8]
    
    # Try to extract key content
    content = ""
    if isinstance(packet, dict):
        content = packet.get("content", "")
        if isinstance(content, dict):
            content = str(content)
    elif hasattr(packet, "content"):
        content = str(packet.content)
    
    if content:
        if len(content) > max_length:
            content = content[:max_length - 3] + "..."
        return f"{packet_type} ({packet_id}): {content}"
    else:
        return f"{packet_type} ({packet_id})"


def _get_packet_type(packet: Any) -> str:
    """
    Extract packet type from various formats.
    
    Args:
        packet: Packet object, dict, or other
    
    Returns:
        Packet type name
    """
    # Try dict with header
    if isinstance(packet, dict):
        header = packet.get("header", {})
        if isinstance(header, dict):
            pkt_type = header.get("packet_type", "unknown")
            if pkt_type != "unknown":
                return pkt_type
        # Try mcp envelope
        mcp = packet.get("mcp", {})
        if isinstance(mcp, dict):
            pkt_type = mcp.get("packet_type", "unknown")
            if pkt_type != "unknown":
                return pkt_type
        
        # Infer from dict keys (fallback)
        keys = set(packet.keys())
        if "decision_outcome" in keys or "decision_summary" in keys:
            return "DECISION"
        elif "new_beliefs" in keys or "belief_delta" in keys:
            return "BELIEF_UPDATE"
        elif "observation_source" in keys or "observation_type" in keys:
            return "OBSERVATION"
        elif "alert_type" in keys or "severity" in keys:
            return "INTEGRITY_ALERT"
        elif "task_id" in keys and "action" in keys:
            return "TASK_DIRECTIVE"
        elif "tool_name" in keys or "authorization" in keys:
            return "TOOL_AUTHORIZATION"
        elif "result" in keys and "task_id" in keys:
            return "TASK_RESULT"
        elif "plan_steps" in keys or "verification_criteria" in keys:
            return "VERIFICATION_PLAN"
        elif "escalation_reason" in keys:
            return "ESCALATION"
    
    # Try object with header
    if hasattr(packet, "header"):
        if hasattr(packet.header, "packet_type"):
            pkt_type = packet.header.packet_type
            if hasattr(pkt_type, "value"):
                return pkt_type.value
            return str(pkt_type)
    
    # Try mcp envelope on object
    if hasattr(packet, "mcp"):
        if hasattr(packet.mcp, "packet_type"):
            pkt_type = packet.mcp.packet_type
            if hasattr(pkt_type, "value"):
                return pkt_type.value
            return str(pkt_type)
    
    # Fallback to class name
    return getattr(packet, "__class__", type(packet)).__name__


def format_section_header(title: str, width: int = 80, char: str = "=") -> str:
    """
    Generate section header with border.
    
    Args:
        title: Section title
        width: Total width of header
        char: Character for border lines
    
    Returns:
        Formatted header with borders
    
    Example:
        EPISODE SUMMARY
        ================================================================================
    """
    border = char * width
    return f"{title}\n{border}"


def format_box_header(title: str, width: int = 77) -> str:
    """
    Generate a box-style header for steps.
    
    Args:
        title: Box title
        width: Total width (default 77 to fit 80-char with padding)
    
    Returns:
        Box-style header
    
    Example:
        ┌─────────────────────────────────────────────────────────────────────────────┐
        │ STEP 1: sense_reality                                                       │
        └─────────────────────────────────────────────────────────────────────────────┘
    """
    # Use ASCII-safe box drawing (for compatibility)
    top = "┌" + "─" * (width - 2) + "┐"
    middle = f"│ {title:<{width - 4}} │"
    bottom = "└" + "─" * (width - 2) + "┘"
    return f"{top}\n{middle}\n{bottom}"


def format_mini_progress_bar(consumed: int, total: int, width: int = 10) -> str:
    """
    Generate compact progress bar for inline use.
    
    Args:
        consumed: Amount consumed
        total: Total available
        width: Character width of bar
    
    Returns:
        Compact progress bar
    
    Example:
        >>> format_mini_progress_bar(8, 10, 10)
        '[████████--]'
    """
    if total <= 0:
        return f"[{'-' * width}]"
    
    pct = consumed / total
    filled = int(width * pct)
    empty = width - filled
    return "[" + "█" * filled + "-" * empty + "]"


def format_timestamp(dt: Any) -> str:
    """
    Format datetime as ISO 8601 string.
    
    Args:
        dt: Datetime object
    
    Returns:
        ISO 8601 formatted string
    """
    from datetime import datetime
    
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        return str(dt)


def format_tree_branch(depth: int, is_last: bool = False) -> str:
    """
    Generate tree branch characters for indented lists.
    
    Args:
        depth: Indentation depth (0 = root)
        is_last: Whether this is the last item at this depth
    
    Returns:
        Tree branch prefix
    
    Example:
        └─> (for last item)
        ├─> (for middle item)
    """
    if depth == 0:
        return ""
    
    indent = "  " * (depth - 1)
    if is_last:
        return f"{indent}└─> "
    else:
        return f"{indent}├─> "


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length (including suffix)
        suffix: Suffix to add when truncated
    
    Returns:
        Truncated text with indication of hidden chars
    """
    if len(text) <= max_length:
        return text
    
    hidden = len(text) - (max_length - len(suffix))
    return text[:max_length - len(suffix)] + f"...\n[truncated - {hidden} chars hidden]"


def format_budget_delta(consumed: int | float, budget_name: str) -> str:
    """
    Format budget consumption delta clearly.
    
    Args:
        consumed: Amount consumed
        budget_name: Name of budget (Tokens, Tool Calls, Time)
    
    Returns:
        Formatted delta string
    """
    if consumed == 0:
        return f"  {budget_name}: No change"
    
    if isinstance(consumed, float):
        return f"  {budget_name}: {consumed:.1f}s elapsed"
    
    return f"  {budget_name}: {consumed:,} consumed"


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Format float as percentage string.
    
    Args:
        value: Float value (0.0 to 1.0)
        decimals: Number of decimal places
    
    Returns:
        Formatted percentage
    """
    return f"{value * 100:.{decimals}f}%"


def format_key_value(key: str, value: Any, indent: int = 2) -> str:
    """
    Format key-value pair with indentation.
    
    Args:
        key: Key name
        value: Value to format
        indent: Number of spaces to indent
    
    Returns:
        Formatted line
    """
    spaces = " " * indent
    return f"{spaces}{key}: {value}"


def format_bullet_list(items: list[str], bullet: str = "•", indent: int = 2) -> str:
    """
    Format list as bulleted items.
    
    Args:
        items: List of items to format
        bullet: Bullet character
        indent: Number of spaces to indent
    
    Returns:
        Formatted bullet list
    """
    spaces = " " * indent
    lines = [f"{spaces}{bullet} {item}" for item in items]
    return "\n".join(lines)

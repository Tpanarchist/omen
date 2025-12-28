"""
Built-in Tools — Simple tools for testing and basic operations.

These tools provide real data for L6 observations.
"""

import os
from datetime import datetime, timezone
from typing import Any

from omen.tools.base import BaseTool, ToolResult, ToolSafety


class ClockTool(BaseTool):
    """
    Get current time.
    
    Params:
        timezone: Optional timezone name (default: UTC)
        format: Optional strftime format (default: ISO)
    """
    
    @property
    def name(self) -> str:
        return "clock"
    
    @property
    def description(self) -> str:
        return "Get current date and time"
    
    def execute(self, params: dict[str, Any]) -> ToolResult:
        fmt = params.get("format", "iso")
        now = datetime.now(timezone.utc)
        
        if fmt == "iso":
            time_str = now.isoformat()
        elif fmt == "unix":
            time_str = str(int(now.timestamp()))
        else:
            time_str = now.strftime(fmt)
        
        return ToolResult.ok(
            data={"current_time": time_str, "timezone": "UTC"},
            tool_name=self.name,
        )


class FileReadTool(BaseTool):
    """
    Read contents of a local file.
    
    Params:
        path: File path to read
        encoding: Text encoding (default: utf-8)
    """
    
    @property
    def name(self) -> str:
        return "file_read"
    
    @property
    def description(self) -> str:
        return "Read contents of a local file"
    
    def execute(self, params: dict[str, Any]) -> ToolResult:
        path = params.get("path")
        if not path:
            return ToolResult.fail("Missing required parameter: path")
        
        encoding = params.get("encoding", "utf-8")
        
        try:
            with open(path, "r", encoding=encoding) as f:
                content = f.read()
            
            return ToolResult.ok(
                data={
                    "path": path,
                    "content": content,
                    "size_bytes": len(content.encode(encoding)),
                },
                tool_name=self.name,
                raw_data=content,
            )
        except FileNotFoundError:
            return ToolResult.fail(f"File not found: {path}")
        except Exception as e:
            return ToolResult.fail(f"Read error: {str(e)}")


class FileWriteTool(BaseTool):
    """
    Write contents to a local file.
    
    Params:
        path: File path to write
        content: Content to write
        mode: 'write' (overwrite) or 'append' (default: write)
    
    REQUIRES AUTHORIZATION TOKEN.
    """
    
    @property
    def name(self) -> str:
        return "file_write"
    
    @property
    def description(self) -> str:
        return "Write contents to a local file (requires authorization)"
    
    @property
    def safety(self) -> ToolSafety:
        return ToolSafety.WRITE
    
    def execute(self, params: dict[str, Any]) -> ToolResult:
        path = params.get("path")
        content = params.get("content")
        
        if not path:
            return ToolResult.fail("Missing required parameter: path")
        if content is None:
            return ToolResult.fail("Missing required parameter: content")
        
        mode = "a" if params.get("mode") == "append" else "w"
        
        try:
            with open(path, mode, encoding="utf-8") as f:
                f.write(content)
            
            return ToolResult.ok(
                data={
                    "path": path,
                    "bytes_written": len(content.encode("utf-8")),
                    "mode": "append" if mode == "a" else "write",
                },
                tool_name=self.name,
            )
        except Exception as e:
            return ToolResult.fail(f"Write error: {str(e)}")


class HttpGetTool(BaseTool):
    """
    Fetch content from a URL via HTTP GET.
    
    Params:
        url: URL to fetch
        timeout: Request timeout in seconds (default: 10)
    """
    
    @property
    def name(self) -> str:
        return "http_get"
    
    @property
    def description(self) -> str:
        return "Fetch content from a URL"
    
    def execute(self, params: dict[str, Any]) -> ToolResult:
        url = params.get("url")
        if not url:
            return ToolResult.fail("Missing required parameter: url")
        
        timeout = params.get("timeout", 10)
        
        try:
            import requests
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            
            return ToolResult.ok(
                data={
                    "url": url,
                    "status_code": response.status_code,
                    "content_type": response.headers.get("Content-Type", ""),
                    "content": response.text[:10000],  # Limit size
                    "content_length": len(response.text),
                },
                tool_name=self.name,
                raw_data=response.text,
            )
        except ImportError:
            return ToolResult.fail("requests library not installed")
        except Exception as e:
            return ToolResult.fail(f"HTTP error: {str(e)}")


class EnvironmentTool(BaseTool):
    """
    Read environment variables.
    
    Params:
        name: Variable name to read (or None for all safe vars)
    """
    
    @property
    def name(self) -> str:
        return "env_read"
    
    @property
    def description(self) -> str:
        return "Read environment variables"
    
    def execute(self, params: dict[str, Any]) -> ToolResult:
        var_name = params.get("name")
        
        # Safe vars that can be exposed
        safe_vars = {"PATH", "HOME", "USER", "SHELL", "PWD", "LANG"}
        
        if var_name:
            if var_name.upper() not in safe_vars:
                return ToolResult.fail(f"Variable '{var_name}' not in safe list")
            value = os.environ.get(var_name)
            data = {var_name: value}
        else:
            data = {k: os.environ.get(k) for k in safe_vars if k in os.environ}
        
        return ToolResult.ok(data=data, tool_name=self.name)


def create_default_registry() -> "ToolRegistry":
    """Create registry with all built-in tools."""
    from omen.tools.registry import ToolRegistry
    
    registry = ToolRegistry()
    registry.register(ClockTool())
    registry.register(FileReadTool())
    registry.register(FileWriteTool())
    registry.register(HttpGetTool())
    registry.register(EnvironmentTool())
    
    return registry

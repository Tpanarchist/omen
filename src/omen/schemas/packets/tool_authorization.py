"""
ToolAuthorizationToken — Authorization for WRITE/MIXED tool operations.

Tokens gate dangerous operations. They are:
- Issued by Layer 5 (or Layer 1 for critical operations)
- Consumed by Layer 6 when executing WRITE/MIXED tools
- Bounded by scope, time, and usage count
- Revocable by System Integrity overlay

Spec: OMEN.md §9.3, §8.3.6, §10.4, §12
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from omen.vocabulary import PacketType, ToolSafety, StakesLevel
from omen.schemas.header import PacketHeader
from omen.schemas.mcp import MCP


class TokenScope(BaseModel):
    """
    Defines what operations a token authorizes.
    
    Directives must have scope ⊆ token scope to use the token.
    """
    allowed_tool_ids: list[str] = Field(
        ...,
        min_length=1,
        description="Tools this token authorizes (at least one required)"
    )
    
    allowed_tool_safeties: list[ToolSafety] = Field(
        default_factory=lambda: [ToolSafety.WRITE, ToolSafety.MIXED],
        description="Safety levels authorized (default: WRITE, MIXED)"
    )
    
    allowed_operations: list[str] | None = Field(
        default=None,
        description="Specific operations allowed (None = all operations on allowed tools)"
    )
    
    resource_constraints: dict[str, Any] | None = Field(
        default=None,
        description="Constraints on resources affected (e.g., max ISK, specific assets)"
    )
    
    target_constraints: dict[str, Any] | None = Field(
        default=None,
        description="Constraints on targets (e.g., specific systems, entities)"
    )


class TokenLimits(BaseModel):
    """
    Usage and time limits for the token.
    
    Token becomes invalid when any limit is exceeded.
    """
    max_uses: int = Field(
        ...,
        ge=1,
        description="Maximum number of times token can be used"
    )
    
    expires_at: datetime = Field(
        ...,
        description="When the token expires (absolute time)"
    )
    
    max_tool_calls_per_use: int | None = Field(
        default=None,
        ge=1,
        description="Maximum tool calls per single use"
    )
    
    max_total_tool_calls: int | None = Field(
        default=None,
        ge=1,
        description="Maximum total tool calls across all uses"
    )


class TokenUsage(BaseModel):
    """
    Tracks how the token has been used.
    
    Updated each time the token is consumed.
    """
    uses_consumed: int = Field(
        default=0,
        ge=0,
        description="Number of times token has been used"
    )
    
    tool_calls_consumed: int = Field(
        default=0,
        ge=0,
        description="Total tool calls made using this token"
    )
    
    last_used_at: datetime | None = Field(
        default=None,
        description="When the token was last used"
    )
    
    last_used_by_directive: str | None = Field(
        default=None,
        description="Directive ID that last used the token"
    )


class ToolAuthorizationPayload(BaseModel):
    """
    Payload for ToolAuthorizationToken.
    
    Contains all authorization parameters and usage tracking.
    
    Spec: OMEN.md §9.3 "ToolAuthorizationToken", §8.3.6, §10.4
    """
    token_id: str = Field(
        ...,
        description="Unique identifier for this token"
    )
    
    issued_for_episode: UUID = Field(
        ...,
        description="Episode (correlation_id) this token is valid for"
    )
    
    issued_by_layer: str = Field(
        ...,
        description="Which layer issued the token (typically '5' or '1')"
    )
    
    authorization_reason: str = Field(
        ...,
        description="Why this authorization was granted"
    )
    
    stakes_level: StakesLevel = Field(
        ...,
        description="Stakes level that justified this authorization"
    )
    
    scope: TokenScope = Field(
        ...,
        description="What operations this token authorizes"
    )
    
    limits: TokenLimits = Field(
        ...,
        description="Usage and time limits"
    )
    
    usage: TokenUsage = Field(
        default_factory=TokenUsage,
        description="Current usage statistics"
    )
    
    revoked: bool = Field(
        default=False,
        description="Whether the token has been revoked"
    )
    
    revoked_at: datetime | None = Field(
        default=None,
        description="When the token was revoked"
    )
    
    revoked_reason: str | None = Field(
        default=None,
        description="Why the token was revoked"
    )
    
    parent_token_id: str | None = Field(
        default=None,
        description="If this token was derived from another token"
    )
    
    @model_validator(mode="after")
    def validate_revocation_consistency(self):
        """If revoked, should have revoked_at and reason."""
        if self.revoked:
            if not self.revoked_at:
                raise ValueError("Revoked token must have revoked_at timestamp")
            if not self.revoked_reason:
                raise ValueError("Revoked token must have revoked_reason")
        return self


class ToolAuthorizationToken(BaseModel):
    """
    Complete ToolAuthorizationToken.
    
    Gates WRITE/MIXED tool operations. Tracks authorization
    scope, limits, and usage for auditability.
    
    Spec: OMEN.md §9.3, §8.3.6
    """
    header: PacketHeader = Field(
        ...,
        description="Packet identification and routing"
    )
    
    mcp: MCP = Field(
        ...,
        description="Mandatory Compliance Payload"
    )
    
    payload: ToolAuthorizationPayload = Field(
        ...,
        description="Token content"
    )
    
    def __init__(self, **data):
        # Ensure packet_type is correct
        if "header" in data and isinstance(data["header"], dict):
            data["header"]["packet_type"] = PacketType.TOOL_AUTHORIZATION.value
        super().__init__(**data)
    
    def is_valid(self, now: datetime | None = None) -> tuple[bool, str]:
        """
        Check if the token is currently valid.
        
        Returns (is_valid, reason).
        """
        if now is None:
            from datetime import timezone as tz
            now = datetime.now(tz.utc)
        
        if self.payload.revoked:
            return False, f"Token revoked: {self.payload.revoked_reason}"
        
        if now > self.payload.limits.expires_at:
            return False, "Token expired"
        
        if self.payload.usage.uses_consumed >= self.payload.limits.max_uses:
            return False, "Max uses exceeded"
        
        if self.payload.limits.max_total_tool_calls is not None:
            if self.payload.usage.tool_calls_consumed >= self.payload.limits.max_total_tool_calls:
                return False, "Max total tool calls exceeded"
        
        return True, "Valid"
    
    def authorizes_tool(self, tool_id: str, tool_safety: ToolSafety) -> tuple[bool, str]:
        """
        Check if this token authorizes a specific tool.
        
        Returns (authorized, reason).
        """
        if tool_id not in self.payload.scope.allowed_tool_ids:
            return False, f"Tool {tool_id} not in allowed_tool_ids"
        
        if tool_safety not in self.payload.scope.allowed_tool_safeties:
            return False, f"Tool safety {tool_safety} not authorized"
        
        return True, "Authorized"
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "header": {
                        "packet_type": "ToolAuthorizationToken",
                        "created_at": "2025-12-21T11:32:45Z",
                        "layer_source": "5",
                        "correlation_id": "77a88b99-c0d1-e2f3-4567-890abcdef012"
                    },
                    "mcp": {
                        "intent": {"summary": "Authorize market order placement", "scope": "authorization"},
                        "stakes": {
                            "impact": "MEDIUM",
                            "irreversibility": "PARTIAL",
                            "uncertainty": "LOW",
                            "adversariality": "CONTESTED",
                            "stakes_level": "MEDIUM"
                        },
                        "quality": {
                            "quality_tier": "PAR",
                            "satisficing_mode": False,
                            "definition_of_done": {"text": "Token issued", "checks": []},
                            "verification_requirement": "VERIFY_ONE"
                        },
                        "budgets": {
                            "token_budget": 50,
                            "tool_call_budget": 0,
                            "time_budget_seconds": 5,
                            "risk_budget": {"envelope": "medium", "max_loss": 1000000}
                        },
                        "epistemics": {
                            "status": "DERIVED",
                            "confidence": 0.95,
                            "calibration_note": "Authorization based on verified market conditions",
                            "freshness_class": "OPERATIONAL",
                            "stale_if_older_than_seconds": 300,
                            "assumptions": ["Market conditions stable", "Sufficient ISK available"]
                        },
                        "evidence": {
                            "evidence_refs": [{
                                "ref_type": "tool_output",
                                "ref_id": "wallet_check_001",
                                "timestamp": "2025-12-21T11:32:30Z"
                            }],
                            "evidence_absent_reason": None
                        },
                        "routing": {"task_class": "CREATE", "tools_state": "tools_ok"}
                    },
                    "payload": {
                        "token_id": "auth_market_001",
                        "issued_for_episode": "77a88b99-c0d1-e2f3-4567-890abcdef012",
                        "issued_by_layer": "5",
                        "authorization_reason": "Market order placement approved after verification",
                        "stakes_level": "MEDIUM",
                        "scope": {
                            "allowed_tool_ids": ["market_order_api"],
                            "allowed_tool_safeties": ["WRITE"],
                            "allowed_operations": ["place_buy_order", "place_sell_order"],
                            "resource_constraints": {"max_isk_per_order": 100000000}
                        },
                        "limits": {
                            "max_uses": 3,
                            "expires_at": "2025-12-21T12:32:45Z",
                            "max_tool_calls_per_use": 1,
                            "max_total_tool_calls": 3
                        },
                        "usage": {
                            "uses_consumed": 0,
                            "tool_calls_consumed": 0
                        },
                        "revoked": False
                    }
                }
            ]
        }
    }

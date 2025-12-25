"""
Tests for ToolAuthorizationToken schema.

Validates structure matches OMEN.md §9.3, §8.3.6, §10.4, §12.
"""

import json
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omen.schemas import ToolAuthorizationToken, ToolAuthorizationPayload
from omen.schemas.packets.tool_authorization import TokenScope, TokenLimits, TokenUsage
from omen.vocabulary import PacketType, LayerSource, ToolSafety, StakesLevel


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def valid_token_scope() -> dict:
    return {
        "allowed_tool_ids": ["market_order_api", "wallet_api"],
        "allowed_tool_safeties": ["WRITE", "MIXED"],
        "allowed_operations": ["place_order", "cancel_order"],
        "resource_constraints": {"max_isk": 100000000}
    }


@pytest.fixture
def valid_token_limits() -> dict:
    return {
        "max_uses": 5,
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "max_tool_calls_per_use": 2,
        "max_total_tool_calls": 10
    }


@pytest.fixture
def valid_token_payload(valid_token_scope, valid_token_limits) -> dict:
    return {
        "token_id": "auth_001",
        "issued_for_episode": str(uuid4()),
        "issued_by_layer": "5",
        "authorization_reason": "Market trading approved",
        "stakes_level": "MEDIUM",
        "scope": valid_token_scope,
        "limits": valid_token_limits,
        "revoked": False
    }


@pytest.fixture
def valid_header() -> dict:
    return {
        "packet_type": "ToolAuthorizationToken",
        "created_at": "2025-12-21T11:32:45Z",
        "layer_source": "5",
        "correlation_id": str(uuid4())
    }


@pytest.fixture
def valid_mcp() -> dict:
    return {
        "intent": {"summary": "Issue authorization", "scope": "authorization"},
        "stakes": {
            "impact": "MEDIUM",
            "irreversibility": "PARTIAL",
            "uncertainty": "LOW",
            "adversariality": "BENIGN",
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
            "calibration_note": "Based on verified conditions",
            "freshness_class": "OPERATIONAL",
            "stale_if_older_than_seconds": 300,
            "assumptions": []
        },
        "evidence": {
            "evidence_refs": [],
            "evidence_absent_reason": "Authorization decision"
        },
        "routing": {"task_class": "CREATE", "tools_state": "tools_ok"}
    }


# =============================================================================
# TOKEN SCOPE TESTS
# =============================================================================

class TestTokenScope:
    """Tests for TokenScope structure."""

    def test_valid_scope(self, valid_token_scope):
        scope = TokenScope(**valid_token_scope)
        assert "market_order_api" in scope.allowed_tool_ids
        assert ToolSafety.WRITE in scope.allowed_tool_safeties

    def test_scope_requires_at_least_one_tool(self):
        with pytest.raises(ValidationError):
            TokenScope(allowed_tool_ids=[])

    def test_scope_default_safeties(self):
        scope = TokenScope(allowed_tool_ids=["test_tool"])
        assert ToolSafety.WRITE in scope.allowed_tool_safeties
        assert ToolSafety.MIXED in scope.allowed_tool_safeties

    def test_scope_with_constraints(self, valid_token_scope):
        scope = TokenScope(**valid_token_scope)
        assert scope.resource_constraints["max_isk"] == 100000000


# =============================================================================
# TOKEN LIMITS TESTS
# =============================================================================

class TestTokenLimits:
    """Tests for TokenLimits structure."""

    def test_valid_limits(self, valid_token_limits):
        limits = TokenLimits(**valid_token_limits)
        assert limits.max_uses == 5
        assert limits.max_tool_calls_per_use == 2

    def test_limits_requires_positive_uses(self):
        with pytest.raises(ValidationError):
            TokenLimits(
                max_uses=0,
                expires_at=datetime.now(timezone.utc)
            )

    def test_limits_minimal(self):
        limits = TokenLimits(
            max_uses=1,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5)
        )
        assert limits.max_tool_calls_per_use is None
        assert limits.max_total_tool_calls is None


# =============================================================================
# TOKEN USAGE TESTS
# =============================================================================

class TestTokenUsage:
    """Tests for TokenUsage structure."""

    def test_default_usage(self):
        usage = TokenUsage()
        assert usage.uses_consumed == 0
        assert usage.tool_calls_consumed == 0
        assert usage.last_used_at is None

    def test_usage_with_history(self):
        usage = TokenUsage(
            uses_consumed=2,
            tool_calls_consumed=5,
            last_used_at="2025-12-21T11:30:00Z",
            last_used_by_directive="dir_001"
        )
        assert usage.uses_consumed == 2
        assert usage.last_used_by_directive == "dir_001"


# =============================================================================
# TOKEN PAYLOAD TESTS
# =============================================================================

class TestToolAuthorizationPayload:
    """Tests for ToolAuthorizationPayload structure."""

    def test_valid_payload(self, valid_token_payload):
        payload = ToolAuthorizationPayload(**valid_token_payload)
        assert payload.token_id == "auth_001"
        assert payload.stakes_level == StakesLevel.MEDIUM

    def test_payload_all_stakes_levels(self, valid_token_payload):
        for stakes in StakesLevel:
            valid_token_payload["stakes_level"] = stakes.value
            payload = ToolAuthorizationPayload(**valid_token_payload)
            assert payload.stakes_level == stakes

    def test_revoked_requires_timestamp_and_reason(self, valid_token_payload):
        valid_token_payload["revoked"] = True
        # Missing revoked_at and revoked_reason
        with pytest.raises(ValidationError) as exc_info:
            ToolAuthorizationPayload(**valid_token_payload)
        assert "revoked" in str(exc_info.value).lower()

    def test_revoked_with_complete_info(self, valid_token_payload):
        valid_token_payload["revoked"] = True
        valid_token_payload["revoked_at"] = "2025-12-21T12:00:00Z"
        valid_token_payload["revoked_reason"] = "Security concern"
        payload = ToolAuthorizationPayload(**valid_token_payload)
        assert payload.revoked is True
        assert payload.revoked_reason == "Security concern"

    def test_payload_with_parent_token(self, valid_token_payload):
        valid_token_payload["parent_token_id"] = "auth_parent_001"
        payload = ToolAuthorizationPayload(**valid_token_payload)
        assert payload.parent_token_id == "auth_parent_001"


# =============================================================================
# COMPLETE TOKEN TESTS
# =============================================================================

class TestToolAuthorizationToken:
    """Tests for complete ToolAuthorizationToken."""

    def test_valid_token(self, valid_header, valid_mcp, valid_token_payload):
        token = ToolAuthorizationToken(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_token_payload
        )
        assert token.header.packet_type == PacketType.TOOL_AUTHORIZATION
        assert token.payload.token_id == "auth_001"

    def test_token_enforces_packet_type(self, valid_header, valid_mcp, valid_token_payload):
        valid_header["packet_type"] = "DecisionPacket"
        token = ToolAuthorizationToken(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_token_payload
        )
        assert token.header.packet_type == PacketType.TOOL_AUTHORIZATION

    def test_token_from_layer_5(self, valid_header, valid_mcp, valid_token_payload):
        """Tokens typically come from Layer 5."""
        token = ToolAuthorizationToken(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_token_payload
        )
        assert token.header.layer_source == LayerSource.LAYER_5

    def test_token_can_come_from_layer_1(self, valid_header, valid_mcp, valid_token_payload):
        """Critical tokens can come from Layer 1."""
        valid_header["layer_source"] = "1"
        token = ToolAuthorizationToken(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_token_payload
        )
        assert token.header.layer_source == LayerSource.LAYER_1

    def test_token_serialization(self, valid_header, valid_mcp, valid_token_payload):
        token = ToolAuthorizationToken(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_token_payload
        )
        json_str = token.model_dump_json()
        parsed = json.loads(json_str)
        assert "token_id" in parsed["payload"]
        assert "scope" in parsed["payload"]
        assert "limits" in parsed["payload"]

    def test_token_roundtrip(self, valid_header, valid_mcp, valid_token_payload):
        token1 = ToolAuthorizationToken(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_token_payload
        )
        json_str = token1.model_dump_json()
        token2 = ToolAuthorizationToken.model_validate_json(json_str)
        assert token1.payload.token_id == token2.payload.token_id
        assert len(token1.payload.scope.allowed_tool_ids) == len(token2.payload.scope.allowed_tool_ids)


# =============================================================================
# VALIDITY CHECK TESTS
# =============================================================================

class TestTokenValidity:
    """Tests for token validity checking methods."""

    def test_valid_token_passes(self, valid_header, valid_mcp, valid_token_payload):
        token = ToolAuthorizationToken(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_token_payload
        )
        is_valid, reason = token.is_valid()
        assert is_valid is True
        assert reason == "Valid"

    def test_expired_token_fails(self, valid_header, valid_mcp, valid_token_payload):
        # Set expiration in the past
        valid_token_payload["limits"]["expires_at"] = (
            datetime.now(timezone.utc) - timedelta(hours=1)
        ).isoformat()
        token = ToolAuthorizationToken(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_token_payload
        )
        is_valid, reason = token.is_valid()
        assert is_valid is False
        assert "expired" in reason.lower()

    def test_revoked_token_fails(self, valid_header, valid_mcp, valid_token_payload):
        valid_token_payload["revoked"] = True
        valid_token_payload["revoked_at"] = "2025-12-21T12:00:00Z"
        valid_token_payload["revoked_reason"] = "Security concern"
        token = ToolAuthorizationToken(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_token_payload
        )
        is_valid, reason = token.is_valid()
        assert is_valid is False
        assert "revoked" in reason.lower()

    def test_max_uses_exceeded_fails(self, valid_header, valid_mcp, valid_token_payload):
        valid_token_payload["usage"] = {
            "uses_consumed": 5,  # Equal to max_uses
            "tool_calls_consumed": 10
        }
        token = ToolAuthorizationToken(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_token_payload
        )
        is_valid, reason = token.is_valid()
        assert is_valid is False
        assert "uses" in reason.lower()

    def test_max_tool_calls_exceeded_fails(self, valid_header, valid_mcp, valid_token_payload):
        valid_token_payload["usage"] = {
            "uses_consumed": 1,
            "tool_calls_consumed": 10  # Equal to max_total_tool_calls
        }
        token = ToolAuthorizationToken(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_token_payload
        )
        is_valid, reason = token.is_valid()
        assert is_valid is False
        assert "tool calls" in reason.lower()


# =============================================================================
# TOOL AUTHORIZATION CHECK TESTS
# =============================================================================

class TestToolAuthorization:
    """Tests for tool authorization checking."""

    def test_authorizes_allowed_tool(self, valid_header, valid_mcp, valid_token_payload):
        token = ToolAuthorizationToken(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_token_payload
        )
        authorized, reason = token.authorizes_tool("market_order_api", ToolSafety.WRITE)
        assert authorized is True

    def test_rejects_unlisted_tool(self, valid_header, valid_mcp, valid_token_payload):
        token = ToolAuthorizationToken(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_token_payload
        )
        authorized, reason = token.authorizes_tool("unauthorized_tool", ToolSafety.WRITE)
        assert authorized is False
        assert "not in allowed_tool_ids" in reason

    def test_rejects_wrong_safety_level(self, valid_header, valid_mcp, valid_token_payload):
        # Only WRITE and MIXED allowed by default
        token = ToolAuthorizationToken(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_token_payload
        )
        authorized, reason = token.authorizes_tool("market_order_api", ToolSafety.READ)
        assert authorized is False
        assert "safety" in reason.lower()


class TestTokenLifecycle:
    """Tests for token lifecycle per §10.4."""

    def test_fresh_token_has_zero_usage(self, valid_header, valid_mcp, valid_token_payload):
        token = ToolAuthorizationToken(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_token_payload
        )
        assert token.payload.usage.uses_consumed == 0
        assert token.payload.usage.tool_calls_consumed == 0

    def test_token_tracks_episode(self, valid_header, valid_mcp, valid_token_payload):
        token = ToolAuthorizationToken(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_token_payload
        )
        assert token.payload.issued_for_episode is not None

    def test_token_tracks_issuer(self, valid_header, valid_mcp, valid_token_payload):
        token = ToolAuthorizationToken(
            header=valid_header,
            mcp=valid_mcp,
            payload=valid_token_payload
        )
        assert token.payload.issued_by_layer == "5"

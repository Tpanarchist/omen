"""Tests for episode ledger."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from omen.vocabulary import StakesLevel, QualityTier, ToolsState
from omen.orchestrator.ledger import (
    BudgetState,
    ActiveToken,
    OpenDirective,
    EpisodeLedger,
    create_ledger,
)


class TestBudgetState:
    """Tests for budget tracking."""
    
    def test_initial_state(self):
        """Budget starts with zero consumption."""
        budget = BudgetState(token_budget=1000, tool_call_budget=5)
        assert budget.tokens_remaining == 1000
        assert budget.tool_calls_remaining == 5
        assert not budget.is_over_budget
    
    def test_consume_resources(self):
        """Consumption is tracked correctly."""
        budget = BudgetState(token_budget=1000, tool_call_budget=5)
        budget.consume(tokens=200, tool_calls=1)
        
        assert budget.tokens_consumed == 200
        assert budget.tool_calls_consumed == 1
        assert budget.tokens_remaining == 800
    
    def test_over_budget_detection(self):
        """Detects when budget is exceeded."""
        budget = BudgetState(token_budget=100)
        budget.consume(tokens=150)
        
        assert budget.is_over_budget is True
        assert budget.tokens_remaining == 0  # Clamped to 0
    
    def test_multiple_consumptions(self):
        """Multiple consume calls accumulate."""
        budget = BudgetState(token_budget=500, tool_call_budget=3)
        budget.consume(tokens=100, tool_calls=1)
        budget.consume(tokens=200, tool_calls=1)
        
        assert budget.tokens_consumed == 300
        assert budget.tool_calls_consumed == 2
        assert budget.tokens_remaining == 200
        assert budget.tool_calls_remaining == 1
    
    def test_time_budget_tracking(self):
        """Time budget is tracked in seconds."""
        budget = BudgetState(time_budget_seconds=60)
        budget.consume(time_seconds=15.5)
        
        assert budget.time_consumed_seconds == 15.5
        assert budget.time_remaining_seconds == 44.5
    
    def test_overrun_approval(self):
        """Overrun can be approved."""
        budget = BudgetState(token_budget=100)
        budget.consume(tokens=150)
        
        assert budget.is_over_budget
        budget.overrun_approved = True
        budget.overrun_approved_by = "L1_Aspirational"
        
        assert budget.overrun_approved
        assert budget.overrun_approved_by == "L1_Aspirational"


class TestActiveToken:
    """Tests for token tracking."""
    
    @pytest.fixture
    def valid_token(self):
        """Create a valid token."""
        return ActiveToken(
            token_id="tok_123",
            scope={"action": "write"},
            issued_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            max_uses=3,
            uses_remaining=3,
        )
    
    def test_valid_token(self, valid_token):
        """Fresh token is valid."""
        assert valid_token.is_valid is True
    
    def test_use_token(self, valid_token):
        """Using token decrements uses."""
        assert valid_token.use() is True
        assert valid_token.uses_remaining == 2
        assert valid_token.is_valid is True
    
    def test_exhausted_token(self, valid_token):
        """Token with no uses remaining is invalid."""
        valid_token.uses_remaining = 0
        assert valid_token.is_valid is False
        assert valid_token.use() is False
    
    def test_revoked_token(self, valid_token):
        """Revoked token is invalid."""
        valid_token.revoked = True
        assert valid_token.is_valid is False
        assert valid_token.use() is False
    
    def test_expired_token(self):
        """Expired token is invalid."""
        token = ActiveToken(
            token_id="tok_old",
            scope={},
            issued_at=datetime.now() - timedelta(hours=2),
            expires_at=datetime.now() - timedelta(hours=1),  # Expired
            max_uses=3,
            uses_remaining=3,
        )
        assert token.is_valid is False
        assert token.use() is False
    
    def test_token_use_until_exhausted(self, valid_token):
        """Token can be used until exhausted."""
        assert valid_token.use() is True  # Use 1
        assert valid_token.use() is True  # Use 2
        assert valid_token.use() is True  # Use 3
        assert valid_token.uses_remaining == 0
        assert valid_token.use() is False  # Exhausted
    
    def test_token_scope(self):
        """Token scope is tracked."""
        token = ActiveToken(
            token_id="tok_write",
            scope={"action": "write", "resource": "file.txt"},
            issued_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            max_uses=1,
            uses_remaining=1,
        )
        assert token.scope["action"] == "write"
        assert token.scope["resource"] == "file.txt"


class TestOpenDirective:
    """Tests for directive tracking."""
    
    def test_create_directive(self):
        """Create pending directive."""
        directive = OpenDirective(
            directive_id="dir_123",
            task_id="task_456",
            issued_at=datetime.now(),
            timeout_at=datetime.now() + timedelta(minutes=5),
        )
        assert directive.status == "PENDING"
        assert directive.directive_id == "dir_123"
        assert directive.task_id == "task_456"
    
    def test_directive_with_status(self):
        """Directive can be created with custom status."""
        directive = OpenDirective(
            directive_id="dir_exec",
            task_id="task_abc",
            issued_at=datetime.now(),
            timeout_at=datetime.now() + timedelta(minutes=5),
            status="EXECUTING",
        )
        assert directive.status == "EXECUTING"


class TestEpisodeLedger:
    """Tests for episode ledger."""
    
    @pytest.fixture
    def ledger(self):
        """Create test ledger."""
        return create_ledger(
            correlation_id=uuid4(),
            stakes_level=StakesLevel.MEDIUM,
            quality_tier=QualityTier.PAR,
            budget=BudgetState(token_budget=1000, tool_call_budget=5),
        )
    
    def test_create_ledger(self, ledger):
        """Ledger is created with correct initial state."""
        assert ledger.stakes_level == StakesLevel.MEDIUM
        assert ledger.quality_tier == QualityTier.PAR
        assert not ledger.is_complete
        assert ledger.budget.token_budget == 1000
    
    def test_create_ledger_with_defaults(self):
        """Ledger can be created with minimal args."""
        ledger = create_ledger(correlation_id=uuid4())
        assert ledger.stakes_level == StakesLevel.LOW
        assert ledger.quality_tier == QualityTier.PAR
        assert ledger.budget.token_budget == 0
    
    def test_token_management(self, ledger):
        """Can add, get, and revoke tokens."""
        token = ActiveToken(
            token_id="tok_test",
            scope={},
            issued_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            max_uses=1,
            uses_remaining=1,
        )
        
        ledger.add_token(token)
        assert ledger.get_token("tok_test") == token
        
        ledger.revoke_token("tok_test")
        assert not ledger.get_token("tok_test").is_valid
    
    def test_token_not_found(self, ledger):
        """Getting nonexistent token returns None."""
        assert ledger.get_token("nonexistent") is None
    
    def test_revoke_nonexistent_token(self, ledger):
        """Revoking nonexistent token returns False."""
        assert ledger.revoke_token("nonexistent") is False
    
    def test_directive_management(self, ledger):
        """Can add and close directives."""
        directive = OpenDirective(
            directive_id="dir_test",
            task_id="task_test",
            issued_at=datetime.now(),
            timeout_at=datetime.now() + timedelta(minutes=5),
        )
        
        ledger.add_directive(directive)
        assert ledger.open_directives["dir_test"].status == "PENDING"
        
        ledger.close_directive("dir_test", "COMPLETED")
        assert ledger.open_directives["dir_test"].status == "COMPLETED"
    
    def test_close_nonexistent_directive(self, ledger):
        """Closing nonexistent directive returns False."""
        assert ledger.close_directive("nonexistent", "COMPLETED") is False
    
    def test_evidence_tracking(self, ledger):
        """Can add evidence refs."""
        ledger.add_evidence({"ref_type": "tool_output", "ref_id": "ev_123"})
        ledger.add_evidence({"ref_type": "observation", "ref_id": "ev_456"})
        
        assert len(ledger.evidence_refs) == 2
        assert ledger.evidence_refs[0]["ref_id"] == "ev_123"
        assert ledger.evidence_refs[1]["ref_id"] == "ev_456"
    
    def test_assumption_tracking(self, ledger):
        """Can track assumptions including load-bearing."""
        ledger.add_assumption("Market is stable", load_bearing=False)
        ledger.add_assumption("API is available", load_bearing=True)
        
        assert len(ledger.assumptions) == 2
        assert len(ledger.load_bearing_assumptions) == 1
        assert ledger.load_bearing_assumptions[0]["assumption"] == "API is available"
    
    def test_assumption_timestamp(self, ledger):
        """Assumptions are timestamped."""
        before = datetime.now()
        ledger.add_assumption("Test assumption")
        after = datetime.now()
        
        timestamp_str = ledger.assumptions[0]["added_at"]
        timestamp = datetime.fromisoformat(timestamp_str)
        
        assert before <= timestamp <= after
    
    def test_contradiction_flagging(self, ledger):
        """Can flag contradictions."""
        assert not ledger.contradiction_detected
        
        ledger.flag_contradiction("Price changed unexpectedly")
        
        assert ledger.contradiction_detected is True
        assert "Price changed" in ledger.contradiction_details[0]
    
    def test_multiple_contradictions(self, ledger):
        """Can track multiple contradictions."""
        ledger.flag_contradiction("Contradiction 1")
        ledger.flag_contradiction("Contradiction 2")
        
        assert len(ledger.contradiction_details) == 2
    
    def test_step_tracking(self, ledger):
        """Can track step progression."""
        ledger.start_step("sense")
        assert ledger.current_step == "sense"
        
        ledger.complete_step("sense")
        assert ledger.current_step is None
        assert "sense" in ledger.completed_steps
    
    def test_multiple_steps(self, ledger):
        """Can track multiple steps sequentially."""
        ledger.start_step("sense")
        ledger.complete_step("sense")
        
        ledger.start_step("think")
        ledger.complete_step("think")
        
        ledger.start_step("act")
        ledger.complete_step("act")
        
        assert len(ledger.completed_steps) == 3
        assert ledger.completed_steps == ["sense", "think", "act"]
    
    def test_episode_completion(self, ledger):
        """Can complete episode."""
        assert not ledger.is_complete
        
        before = datetime.now()
        ledger.complete_episode()
        after = datetime.now()
        
        assert ledger.is_complete
        assert ledger.completed_at is not None
        assert before <= ledger.completed_at <= after
    
    def test_error_tracking(self, ledger):
        """Can track errors."""
        assert not ledger.has_errors
        
        ledger.add_error("Something went wrong")
        ledger.add_error("Another error")
        
        assert ledger.has_errors
        assert len(ledger.errors) == 2
        assert "Something went wrong" in ledger.errors
    
    def test_to_summary(self, ledger):
        """Summary includes key state."""
        ledger.budget.consume(tokens=100, tool_calls=2)
        
        token = ActiveToken(
            token_id="tok_1",
            scope={},
            issued_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            max_uses=1,
            uses_remaining=1,
        )
        ledger.add_token(token)
        
        directive = OpenDirective(
            directive_id="dir_1",
            task_id="task_1",
            issued_at=datetime.now(),
            timeout_at=datetime.now() + timedelta(minutes=5),
        )
        ledger.add_directive(directive)
        
        ledger.add_evidence({"ref_id": "ev_1"})
        ledger.complete_step("step_1")
        
        summary = ledger.to_summary()
        
        assert "correlation_id" in summary
        assert "100/1000" in summary["budget"]["tokens"]
        assert "2/5" in summary["budget"]["tool_calls"]
        assert summary["active_tokens"] == 1
        assert summary["open_directives"] == 1  # PENDING only
        assert summary["evidence_refs"] == 1
        assert summary["completed_steps"] == 1
        assert summary["is_complete"] is False
        assert summary["has_errors"] is False
    
    def test_summary_with_completed_directive(self, ledger):
        """Summary only counts PENDING directives."""
        directive = OpenDirective(
            directive_id="dir_1",
            task_id="task_1",
            issued_at=datetime.now(),
            timeout_at=datetime.now() + timedelta(minutes=5),
        )
        ledger.add_directive(directive)
        ledger.close_directive("dir_1", "COMPLETED")
        
        summary = ledger.to_summary()
        assert summary["open_directives"] == 0
    
    def test_ledger_with_campaign_and_template(self):
        """Ledger tracks campaign and template IDs."""
        ledger = create_ledger(
            correlation_id=uuid4(),
            campaign_id="campaign_abc",
            template_id="template_xyz",
        )
        
        assert ledger.campaign_id == "campaign_abc"
        assert ledger.template_id == "template_xyz"
    
    def test_tools_state_tracking(self):
        """Ledger tracks tools state."""
        ledger = create_ledger(
            correlation_id=uuid4(),
            tools_state=ToolsState.TOOLS_DOWN,
        )
        
        assert ledger.tools_state == ToolsState.TOOLS_DOWN
    
    def test_summary_stakes_and_quality(self, ledger):
        """Summary includes stakes and quality tier."""
        summary = ledger.to_summary()
        
        assert summary["stakes_level"] == "MEDIUM"
        assert summary["quality_tier"] == "PAR"

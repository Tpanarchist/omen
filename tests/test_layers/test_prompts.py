"""Tests for layer prompts."""

import pytest

from omen.layers import (
    LAYER_1_PROMPT,
    LAYER_2_PROMPT,
    LAYER_3_PROMPT,
    LAYER_4_PROMPT,
    LAYER_5_PROMPT,
    LAYER_6_PROMPT,
    LAYER_PROMPTS,
)


class TestPromptRegistry:
    """Tests for prompt registry."""

    def test_all_layers_have_prompts(self):
        """All 6 layers have prompts defined."""
        assert len(LAYER_PROMPTS) == 6
        for i in range(1, 7):
            assert f"LAYER_{i}" in LAYER_PROMPTS

    def test_prompts_are_strings(self):
        """All prompts are non-empty strings."""
        for name, prompt in LAYER_PROMPTS.items():
            assert isinstance(prompt, str), f"{name} prompt is not a string"
            assert len(prompt) > 100, f"{name} prompt is too short"

    def test_prompts_match_exports(self):
        """Registry matches individual exports."""
        assert LAYER_PROMPTS["LAYER_1"] == LAYER_1_PROMPT
        assert LAYER_PROMPTS["LAYER_2"] == LAYER_2_PROMPT
        assert LAYER_PROMPTS["LAYER_3"] == LAYER_3_PROMPT
        assert LAYER_PROMPTS["LAYER_4"] == LAYER_4_PROMPT
        assert LAYER_PROMPTS["LAYER_5"] == LAYER_5_PROMPT
        assert LAYER_PROMPTS["LAYER_6"] == LAYER_6_PROMPT


class TestLayer1Prompt:
    """Tests for Aspirational layer prompt."""

    def test_contains_identity(self):
        """Prompt identifies as Layer 1 Aspirational."""
        assert "Layer 1" in LAYER_1_PROMPT
        assert "Aspirational" in LAYER_1_PROMPT

    def test_contains_constitution(self):
        """Prompt includes constitutional imperatives."""
        assert "constitution" in LAYER_1_PROMPT.lower()
        assert "imperative" in LAYER_1_PROMPT.lower()
        # Check for some numbered imperatives
        assert "1." in LAYER_1_PROMPT
        assert "18." in LAYER_1_PROMPT

    def test_contains_constraints(self):
        """Prompt specifies what layer cannot do."""
        assert "CANNOT" in LAYER_1_PROMPT
        assert "TaskDirective" in LAYER_1_PROMPT
        assert "Decision" in LAYER_1_PROMPT

    def test_specifies_output_types(self):
        """Prompt specifies allowed outputs."""
        assert "IntegrityAlert" in LAYER_1_PROMPT
        assert "BeliefUpdate" in LAYER_1_PROMPT

    def test_mentions_veto_authority(self):
        """Prompt mentions veto authority."""
        assert "veto" in LAYER_1_PROMPT.lower()


class TestLayer2Prompt:
    """Tests for Global Strategy layer prompt."""

    def test_contains_identity(self):
        """Prompt identifies as Layer 2 Global Strategy."""
        assert "Layer 2" in LAYER_2_PROMPT
        assert "Global Strategy" in LAYER_2_PROMPT

    def test_contains_strategic_concepts(self):
        """Prompt includes strategic thinking concepts."""
        assert "strategic" in LAYER_2_PROMPT.lower() or "strategy" in LAYER_2_PROMPT.lower()
        assert "campaign" in LAYER_2_PROMPT.lower()

    def test_contains_constraints(self):
        """Prompt specifies what layer cannot do."""
        assert "CANNOT" in LAYER_2_PROMPT
        assert "ToolAuthorizationToken" in LAYER_2_PROMPT
        assert "TaskDirective" in LAYER_2_PROMPT

    def test_specifies_output_types(self):
        """Prompt specifies allowed outputs."""
        assert "BeliefUpdate" in LAYER_2_PROMPT


class TestLayer3Prompt:
    """Tests for Agent Model layer prompt."""

    def test_contains_identity(self):
        """Prompt identifies as Layer 3 Agent Model."""
        assert "Layer 3" in LAYER_3_PROMPT
        assert "Agent Model" in LAYER_3_PROMPT

    def test_contains_self_awareness_concepts(self):
        """Prompt includes self-awareness concepts."""
        assert "self" in LAYER_3_PROMPT.lower() or "capability" in LAYER_3_PROMPT.lower()
        assert "tool" in LAYER_3_PROMPT.lower()

    def test_mentions_tool_states(self):
        """Prompt mentions tool state tracking."""
        assert "tools_ok" in LAYER_3_PROMPT or "tools_partial" in LAYER_3_PROMPT or "tools_down" in LAYER_3_PROMPT

    def test_contains_constraints(self):
        """Prompt specifies what layer cannot do."""
        assert "CANNOT" in LAYER_3_PROMPT
        assert "execute" in LAYER_3_PROMPT.lower()

    def test_specifies_output_types(self):
        """Prompt specifies allowed outputs."""
        assert "BeliefUpdate" in LAYER_3_PROMPT


class TestLayer4Prompt:
    """Tests for Executive Function layer prompt."""

    def test_contains_identity(self):
        """Prompt identifies as Layer 4 Executive Function."""
        assert "Layer 4" in LAYER_4_PROMPT
        assert "Executive Function" in LAYER_4_PROMPT

    def test_contains_planning_concepts(self):
        """Prompt includes planning and budget concepts."""
        assert "plan" in LAYER_4_PROMPT.lower()
        assert "budget" in LAYER_4_PROMPT.lower()

    def test_mentions_definition_of_done(self):
        """Prompt mentions Definition of Done."""
        assert "Definition of Done" in LAYER_4_PROMPT or "DoD" in LAYER_4_PROMPT

    def test_contains_constraints(self):
        """Prompt specifies what layer cannot do."""
        assert "CANNOT" in LAYER_4_PROMPT
        assert "TaskDirective" in LAYER_4_PROMPT
        assert "Decision" in LAYER_4_PROMPT

    def test_specifies_output_types(self):
        """Prompt specifies allowed outputs."""
        assert "BeliefUpdate" in LAYER_4_PROMPT


class TestLayer5Prompt:
    """Tests for Cognitive Control layer prompt."""

    def test_contains_identity(self):
        """Prompt identifies as Layer 5 Cognitive Control."""
        assert "Layer 5" in LAYER_5_PROMPT
        assert "Cognitive Control" in LAYER_5_PROMPT

    def test_contains_decision_outcomes(self):
        """Prompt includes all decision outcomes."""
        assert "ACT" in LAYER_5_PROMPT
        assert "VERIFY_FIRST" in LAYER_5_PROMPT
        assert "ESCALATE" in LAYER_5_PROMPT
        assert "DEFER" in LAYER_5_PROMPT

    def test_contains_arbitration(self):
        """Prompt includes arbitration mechanism."""
        assert "arbitration" in LAYER_5_PROMPT.lower() or "Arbitration" in LAYER_5_PROMPT
        assert "Stage 1" in LAYER_5_PROMPT or "stage" in LAYER_5_PROMPT.lower()

    def test_specifies_outputs(self):
        """Prompt specifies what layer can emit."""
        assert "Decision" in LAYER_5_PROMPT
        assert "VerificationPlan" in LAYER_5_PROMPT
        assert "ToolAuthorizationToken" in LAYER_5_PROMPT
        assert "TaskDirective" in LAYER_5_PROMPT

    def test_contains_constraints(self):
        """Prompt specifies what layer cannot do."""
        assert "CANNOT" in LAYER_5_PROMPT
        # L5 cannot execute directly
        assert "Layer 6" in LAYER_5_PROMPT


class TestLayer6Prompt:
    """Tests for Task Prosecution layer prompt."""

    def test_contains_identity(self):
        """Prompt identifies as Layer 6 Task Prosecution."""
        assert "Layer 6" in LAYER_6_PROMPT
        assert "Task Prosecution" in LAYER_6_PROMPT

    def test_contains_vat_boundary(self):
        """Prompt mentions vat boundary concept."""
        assert "vat" in LAYER_6_PROMPT.lower() or "boundary" in LAYER_6_PROMPT.lower()

    def test_emphasizes_grounding(self):
        """Prompt emphasizes evidence and grounding."""
        assert "evidence" in LAYER_6_PROMPT.lower()
        assert "OBSERVED" in LAYER_6_PROMPT
        assert "evidence_ref" in LAYER_6_PROMPT or "evidence_refs" in LAYER_6_PROMPT

    def test_specifies_outputs(self):
        """Prompt specifies what layer can emit."""
        assert "Observation" in LAYER_6_PROMPT
        assert "TaskResult" in LAYER_6_PROMPT
        assert "BeliefUpdate" in LAYER_6_PROMPT

    def test_specifies_constraints(self):
        """Prompt specifies what layer cannot do."""
        assert "CANNOT" in LAYER_6_PROMPT
        assert "Decision" in LAYER_6_PROMPT  # Cannot emit


class TestPromptConsistency:
    """Tests for consistency across prompts."""

    def test_all_specify_constraints(self):
        """All prompts specify constraints."""
        for name, prompt in LAYER_PROMPTS.items():
            assert "CANNOT" in prompt, f"{name} missing constraints section"

    def test_all_specify_outputs(self):
        """All prompts specify allowed outputs."""
        for name, prompt in LAYER_PROMPTS.items():
            # Each should mention what it CAN emit
            assert ("CAN" in prompt and "EMIT" in prompt) or "CAN ONLY EMIT" in prompt, (
                f"{name} missing output specification"
            )

    def test_all_have_role_section(self):
        """All prompts have a role section."""
        for name, prompt in LAYER_PROMPTS.items():
            assert "Your Role" in prompt or "## Your Role" in prompt, (
                f"{name} missing role section"
            )

    def test_all_have_responsibilities_section(self):
        """All prompts have a responsibilities section."""
        for name, prompt in LAYER_PROMPTS.items():
            assert "Responsibilities" in prompt or "## Your Responsibilities" in prompt, (
                f"{name} missing responsibilities section"
            )

    def test_no_layer_claims_execution_except_l6(self):
        """Only Layer 6 mentions direct execution."""
        # L6 is the only one that executes
        for i in range(1, 6):  # L1-L5
            prompt = LAYER_PROMPTS[f"LAYER_{i}"]
            # These layers shouldn't claim to execute tasks directly
            # (they may mention "execute" in context of prohibitions)
            assert "you execute" not in prompt.lower() or "cannot" in prompt.lower()

    def test_all_include_output_examples(self):
        """All prompts include JSON output examples."""
        for name, prompt in LAYER_PROMPTS.items():
            # Should have JSON code blocks with examples
            assert "```json" in prompt, f"{name} missing JSON examples"


class TestPromptHierarchy:
    """Tests for proper hierarchical relationships."""

    def test_l1_mentions_no_task_directive(self):
        """Layer 1 explicitly cannot issue TaskDirectives."""
        assert "TaskDirective" in LAYER_1_PROMPT
        assert "CANNOT" in LAYER_1_PROMPT

    def test_l5_can_issue_task_directives(self):
        """Layer 5 can issue TaskDirectives."""
        assert "TaskDirective" in LAYER_5_PROMPT
        assert "CAN EMIT" in LAYER_5_PROMPT

    def test_only_l5_issues_tool_auth_tokens(self):
        """Only Layer 5 can issue ToolAuthorizationTokens."""
        assert "ToolAuthorizationToken" in LAYER_5_PROMPT
        assert "CAN EMIT" in LAYER_5_PROMPT
        # Other layers mention they can't
        for i in [1, 2, 3, 4, 6]:
            prompt = LAYER_PROMPTS[f"LAYER_{i}"]
            if "ToolAuthorizationToken" in prompt:
                assert "CANNOT" in prompt

    def test_only_l6_emits_observations(self):
        """Only Layer 6 emits Observation packets."""
        assert "Observation" in LAYER_6_PROMPT
        # L6 can emit observations
        l6_can_section = LAYER_6_PROMPT[LAYER_6_PROMPT.find("CAN ONLY EMIT"):]
        assert "Observation" in l6_can_section

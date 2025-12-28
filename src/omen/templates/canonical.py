"""
Canonical Templates — The seven cognitive patterns A-G.

Spec: OMEN.md §11.3 "Canonical templates"

Templates define standard workflows through the FSM, with layer ownership,
packet emissions, and constraints. The compiler (Layer 5) interprets
bindings to populate MCP/payload fields during episode instantiation.

Template F can serve as both a standalone degraded-mode workflow and
as a constraint overlay for other templates when tools_state != TOOLS_OK
(orchestrator logic, not implemented here).
"""

from omen.vocabulary import (
    TemplateID,
    IntentClass,
    LayerSource,
    FSMState,
    PacketType,
    QualityTier,
    ToolsState,
)
from omen.templates.models import (
    TemplateStep,
    TemplateConstraints,
    EpisodeTemplate,
)


# =============================================================================
# TEMPLATE A: GROUNDING LOOP
# =============================================================================
# Path: S0_IDLE → S1_SENSE → S2_MODEL → S3_DECIDE → S7_REVIEW → S0_IDLE
# Purpose: Base cognitive cycle - sense environment, update beliefs, decide

TEMPLATE_A = EpisodeTemplate(
    template_id=TemplateID.TEMPLATE_A,
    name="Grounding Loop",
    description="Sense → Model → Decide base cycle. Establishes situational awareness.",
    intent_class=IntentClass.SENSE,
    constraints=TemplateConstraints(
        min_tier=QualityTier.PAR,
        tools_state=[ToolsState.TOOLS_OK, ToolsState.TOOLS_PARTIAL],
        write_allowed=False,
    ),
    steps=[
        TemplateStep(
            step_id="idle_start",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S0_IDLE,
            packet_type=None,
            next_steps=["sense"],
        ),
        TemplateStep(
            step_id="sense",
            owner_layer=LayerSource.LAYER_6,
            fsm_state=FSMState.S1_SENSE,
            packet_type=PacketType.OBSERVATION,
            next_steps=["model"],
        ),
        TemplateStep(
            step_id="model",
            owner_layer=LayerSource.LAYER_6,
            fsm_state=FSMState.S2_MODEL,
            packet_type=PacketType.BELIEF_UPDATE,
            next_steps=["decide"],
        ),
        TemplateStep(
            step_id="decide",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S3_DECIDE,
            packet_type=PacketType.DECISION,
            next_steps=["review"],
        ),
        TemplateStep(
            step_id="review",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S7_REVIEW,
            packet_type=PacketType.BELIEF_UPDATE,
            next_steps=["idle_end"],
        ),
        TemplateStep(
            step_id="idle_end",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S0_IDLE,
            packet_type=None,
            next_steps=[],
        ),
    ],
    entry_step="idle_start",
    exit_steps=["idle_end"],
)


# =============================================================================
# TEMPLATE B: VERIFICATION LOOP
# =============================================================================
# Path: S3_DECIDE → S4_VERIFY → S6_EXECUTE → S2_MODEL → S3_DECIDE
# Purpose: VERIFY_FIRST outcome - gather evidence before acting
# Note: Entered from a Decision with outcome=VERIFY_FIRST
# Compiler reads bindings["decision_outcome"] to populate DecisionPacket.payload

TEMPLATE_B = EpisodeTemplate(
    template_id=TemplateID.TEMPLATE_B,
    name="Verification Loop",
    description="VERIFY_FIRST handling: plan verification, execute reads, update beliefs, re-decide.",
    intent_class=IntentClass.VERIFY,
    constraints=TemplateConstraints(
        min_tier=QualityTier.PAR,
        tools_state=[ToolsState.TOOLS_OK, ToolsState.TOOLS_PARTIAL],
        write_allowed=False,  # Verification uses READ only
    ),
    steps=[
        TemplateStep(
            step_id="decide_verify",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S3_DECIDE,
            packet_type=PacketType.DECISION,  # outcome=VERIFY_FIRST
            next_steps=["plan"],
            bindings={"decision_outcome": "VERIFY_FIRST"},
        ),
        TemplateStep(
            step_id="plan",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S4_VERIFY,
            packet_type=PacketType.VERIFICATION_PLAN,
            next_steps=["execute_read"],
        ),
        TemplateStep(
            step_id="execute_read",
            owner_layer=LayerSource.LAYER_6,
            fsm_state=FSMState.S6_EXECUTE,
            packet_type=PacketType.TASK_RESULT,  # Result of verification read
            next_steps=["update_beliefs"],
        ),
        TemplateStep(
            step_id="update_beliefs",
            owner_layer=LayerSource.LAYER_6,
            fsm_state=FSMState.S2_MODEL,
            packet_type=PacketType.BELIEF_UPDATE,
            next_steps=["re_decide"],
        ),
        TemplateStep(
            step_id="re_decide",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S3_DECIDE,
            packet_type=PacketType.DECISION,  # Now with evidence
            next_steps=[],  # Exit - may chain to C, D, or E
        ),
    ],
    entry_step="decide_verify",
    exit_steps=["re_decide"],
)


# =============================================================================
# TEMPLATE C: READ-ONLY ACT
# =============================================================================
# Path: S3_DECIDE → S6_EXECUTE → S2_MODEL → S7_REVIEW
# Purpose: ACT decision with READ-only directives (no authorization needed)

TEMPLATE_C = EpisodeTemplate(
    template_id=TemplateID.TEMPLATE_C,
    name="Read-Only Act",
    description="ACT with READ-only directives. No authorization token required.",
    intent_class=IntentClass.ACT,
    constraints=TemplateConstraints(
        min_tier=QualityTier.PAR,
        tools_state=[ToolsState.TOOLS_OK, ToolsState.TOOLS_PARTIAL],
        write_allowed=False,
    ),
    steps=[
        TemplateStep(
            step_id="decide_act",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S3_DECIDE,
            packet_type=PacketType.DECISION,  # outcome=ACT
            next_steps=["execute"],
            bindings={"decision_outcome": "ACT"},
        ),
        TemplateStep(
            step_id="execute",
            owner_layer=LayerSource.LAYER_6,
            fsm_state=FSMState.S6_EXECUTE,
            packet_type=PacketType.TASK_RESULT,
            next_steps=["integrate"],
        ),
        TemplateStep(
            step_id="integrate",
            owner_layer=LayerSource.LAYER_6,
            fsm_state=FSMState.S2_MODEL,
            packet_type=PacketType.BELIEF_UPDATE,
            next_steps=["review"],
        ),
        TemplateStep(
            step_id="review",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S7_REVIEW,
            packet_type=PacketType.BELIEF_UPDATE,
            next_steps=[],
        ),
    ],
    entry_step="decide_act",
    exit_steps=["review"],
)


# =============================================================================
# TEMPLATE D: WRITE ACT
# =============================================================================
# Path: S3_DECIDE → S5_AUTHORIZE → S6_EXECUTE → S2_MODEL → S7_REVIEW
# Purpose: ACT with WRITE/MIXED directives (requires authorization token)

TEMPLATE_D = EpisodeTemplate(
    template_id=TemplateID.TEMPLATE_D,
    name="Write Act",
    description="ACT with WRITE directives. Requires authorization token before execution.",
    intent_class=IntentClass.ACT,
    constraints=TemplateConstraints(
        min_tier=QualityTier.SUPERB,  # Writes require SUPERB
        tools_state=[ToolsState.TOOLS_OK],  # Full tools required for writes
        write_allowed=True,
    ),
    steps=[
        TemplateStep(
            step_id="decide_act",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S3_DECIDE,
            packet_type=PacketType.DECISION,
            next_steps=["authorize"],
            bindings={"decision_outcome": "ACT"},
        ),
        TemplateStep(
            step_id="authorize",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S5_AUTHORIZE,
            packet_type=PacketType.TOOL_AUTHORIZATION,
            next_steps=["execute"],
        ),
        TemplateStep(
            step_id="execute",
            owner_layer=LayerSource.LAYER_6,
            fsm_state=FSMState.S6_EXECUTE,
            packet_type=PacketType.TASK_RESULT,
            next_steps=["integrate"],
        ),
        TemplateStep(
            step_id="integrate",
            owner_layer=LayerSource.LAYER_6,
            fsm_state=FSMState.S2_MODEL,
            packet_type=PacketType.BELIEF_UPDATE,
            next_steps=["review"],
        ),
        TemplateStep(
            step_id="review",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S7_REVIEW,
            packet_type=PacketType.BELIEF_UPDATE,
            next_steps=[],
        ),
    ],
    entry_step="decide_act",
    exit_steps=["review"],
)


# =============================================================================
# TEMPLATE E: ESCALATION
# =============================================================================
# Path: S3_DECIDE → S8_ESCALATED
# Purpose: ESCALATE decision - hand off to human with options and gaps

TEMPLATE_E = EpisodeTemplate(
    template_id=TemplateID.TEMPLATE_E,
    name="Escalation",
    description="ESCALATE to human. Present options, gaps, and recommendations.",
    intent_class=IntentClass.ESCALATE,
    constraints=TemplateConstraints(
        min_tier=QualityTier.SUBPAR,  # Can escalate at any tier
        tools_state=[ToolsState.TOOLS_OK, ToolsState.TOOLS_PARTIAL, ToolsState.TOOLS_DOWN],
        write_allowed=False,
    ),
    steps=[
        TemplateStep(
            step_id="decide_escalate",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S3_DECIDE,
            packet_type=PacketType.DECISION,
            next_steps=["escalate"],
            bindings={"decision_outcome": "ESCALATE"},
        ),
        TemplateStep(
            step_id="escalate",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S8_ESCALATED,
            packet_type=PacketType.ESCALATION,
            next_steps=[],
        ),
    ],
    entry_step="decide_escalate",
    exit_steps=["escalate"],
)


# =============================================================================
# TEMPLATE F: DEGRADED TOOLS (MODIFIER)
# =============================================================================
# Not a standalone flow - modifies other templates when tools_state != TOOLS_OK
# Represented as constraints that can be applied to other templates
# Can serve as constraint overlay for orchestrator to apply to other templates

TEMPLATE_F = EpisodeTemplate(
    template_id=TemplateID.TEMPLATE_F,
    name="Degraded Tools",
    description="Modifier template for tools_partial/tools_down posture. Tightens constraints.",
    intent_class=IntentClass.SENSE,  # Falls back to sensing/escalation
    constraints=TemplateConstraints(
        min_tier=QualityTier.PAR,
        tools_state=[ToolsState.TOOLS_PARTIAL, ToolsState.TOOLS_DOWN],
        write_allowed=False,  # No writes when degraded
    ),
    steps=[
        # Degraded mode: sense what we can, escalate if needed
        TemplateStep(
            step_id="sense_degraded",
            owner_layer=LayerSource.LAYER_6,
            fsm_state=FSMState.S1_SENSE,
            packet_type=PacketType.OBSERVATION,
            next_steps=["assess"],
        ),
        TemplateStep(
            step_id="assess",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S3_DECIDE,
            packet_type=PacketType.DECISION,
            next_steps=["escalate_or_wait"],
        ),
        TemplateStep(
            step_id="escalate_or_wait",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S8_ESCALATED,
            packet_type=PacketType.ESCALATION,
            next_steps=[],
        ),
    ],
    entry_step="sense_degraded",
    exit_steps=["escalate_or_wait"],
)


# =============================================================================
# TEMPLATE G: COMPILE-TO-CODE
# =============================================================================
# Special workflow for explicit code compilation requests
# Includes test gates and rollback provisions

TEMPLATE_G = EpisodeTemplate(
    template_id=TemplateID.TEMPLATE_G,
    name="Compile-to-Code",
    description="Code compilation workflow with test gates and rollback provisions.",
    intent_class=IntentClass.COMPILE,
    constraints=TemplateConstraints(
        min_tier=QualityTier.SUPERB,  # Compilation requires highest tier
        tools_state=[ToolsState.TOOLS_OK],  # Full tools required
        write_allowed=True,  # Code generation is a write
    ),
    steps=[
        TemplateStep(
            step_id="decide_compile",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S3_DECIDE,
            packet_type=PacketType.DECISION,
            next_steps=["plan_compilation"],
        ),
        TemplateStep(
            step_id="plan_compilation",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S4_VERIFY,
            packet_type=PacketType.VERIFICATION_PLAN,  # Plan what to compile/test
            next_steps=["authorize_compile"],
        ),
        TemplateStep(
            step_id="authorize_compile",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S5_AUTHORIZE,
            packet_type=PacketType.TOOL_AUTHORIZATION,
            next_steps=["execute_compile"],
        ),
        TemplateStep(
            step_id="execute_compile",
            owner_layer=LayerSource.LAYER_6,
            fsm_state=FSMState.S6_EXECUTE,
            packet_type=PacketType.TASK_RESULT,
            next_steps=["verify_result"],
        ),
        TemplateStep(
            step_id="verify_result",
            owner_layer=LayerSource.LAYER_6,
            fsm_state=FSMState.S2_MODEL,
            packet_type=PacketType.BELIEF_UPDATE,
            next_steps=["review_compilation"],
        ),
        TemplateStep(
            step_id="review_compilation",
            owner_layer=LayerSource.LAYER_5,
            fsm_state=FSMState.S7_REVIEW,
            packet_type=PacketType.BELIEF_UPDATE,
            next_steps=[],
        ),
    ],
    entry_step="decide_compile",
    exit_steps=["review_compilation"],
)


# =============================================================================
# TEMPLATE H: FULL-STACK MISSION FLOW
# =============================================================================
# Path: S0 → S1 → S2 → S3 → S6 → S7 → S2 → S0
# Purpose: Exercise all 6 layers in a legitimate episode flow
# All layers participate in standard grounding + action cycle

TEMPLATE_H = EpisodeTemplate(
    template_id=TemplateID.TEMPLATE_H,
    name="Full-Stack Mission Flow",
    description=(
        "Complete episode exercising all 6 layers with proper FSM flow. "
        "L1 provides mission context, L6 senses, L3 models capabilities, "
        "L2 frames strategically, L4 plans, L5 decides/directs, L6 executes, "
        "then L5/L4/L3/L2/L1 review results flowing back up."
    ),
    intent_class=IntentClass.ACT,
    constraints=TemplateConstraints(
        min_tier=QualityTier.PAR,
        tools_state=[ToolsState.TOOLS_OK, ToolsState.TOOLS_PARTIAL],
        write_allowed=False,  # Read-only for initial integration
    ),
    steps=[
        TemplateStep(
            step_id="idle_start",
            owner_layer=LayerSource.LAYER_1,  # L1 sets mission posture
            fsm_state=FSMState.S0_IDLE,
            packet_type=None,
            next_steps=["l6_sense"],
        ),
        TemplateStep(
            step_id="l6_sense",
            owner_layer=LayerSource.LAYER_6,  # L6 senses environment
            fsm_state=FSMState.S1_SENSE,
            packet_type=PacketType.OBSERVATION,
            next_steps=["l3_model"],
        ),
        TemplateStep(
            step_id="l3_model",
            owner_layer=LayerSource.LAYER_3,  # L3 models capabilities
            fsm_state=FSMState.S2_MODEL,
            packet_type=PacketType.BELIEF_UPDATE,
            next_steps=["l2_strategy"],
        ),
        TemplateStep(
            step_id="l2_strategy",
            owner_layer=LayerSource.LAYER_2,  # L2 frames strategy
            fsm_state=FSMState.S1_SENSE,  # L2 can sense strategic context
            packet_type=PacketType.BELIEF_UPDATE,  # L2 emits belief updates, not observations
            next_steps=["l4_plan"],
        ),
        TemplateStep(
            step_id="l4_plan",
            owner_layer=LayerSource.LAYER_4,  # L4 creates plan
            fsm_state=FSMState.S2_MODEL,
            packet_type=PacketType.BELIEF_UPDATE,
            next_steps=["l5_decide"],
        ),
        TemplateStep(
            step_id="l5_decide",
            owner_layer=LayerSource.LAYER_5,  # L5 makes decision
            fsm_state=FSMState.S3_DECIDE,
            packet_type=PacketType.DECISION,
            next_steps=["l5_directive"],
            bindings={"decision_outcome": "ACT"},
        ),
        TemplateStep(
            step_id="l5_directive",
            owner_layer=LayerSource.LAYER_5,  # L5 issues directive
            fsm_state=FSMState.S6_EXECUTE,  # Directive implies execution phase
            packet_type=PacketType.TASK_DIRECTIVE,
            next_steps=["l6_execute"],
        ),
        TemplateStep(
            step_id="l6_execute",
            owner_layer=LayerSource.LAYER_6,  # L6 executes task
            fsm_state=FSMState.S6_EXECUTE,
            packet_type=PacketType.TASK_RESULT,
            next_steps=["l5_review"],
        ),
        TemplateStep(
            step_id="l5_review",
            owner_layer=LayerSource.LAYER_5,  # L5 reviews results
            fsm_state=FSMState.S7_REVIEW,
            packet_type=PacketType.BELIEF_UPDATE,
            next_steps=["l4_assess"],
        ),
        TemplateStep(
            step_id="l4_assess",
            owner_layer=LayerSource.LAYER_4,  # L4 assesses against plan
            fsm_state=FSMState.S2_MODEL,  # Integrate into model
            packet_type=PacketType.BELIEF_UPDATE,
            next_steps=["l3_integrate"],
        ),
        TemplateStep(
            step_id="l3_integrate",
            owner_layer=LayerSource.LAYER_3,  # L3 updates capability model
            fsm_state=FSMState.S1_SENSE,  # Sense new capabilities
            packet_type=PacketType.BELIEF_UPDATE,  # L3 emits belief updates, not observations
            next_steps=["l2_update"],
        ),
        TemplateStep(
            step_id="l2_update",
            owner_layer=LayerSource.LAYER_2,  # L2 updates strategic frame
            fsm_state=FSMState.S2_MODEL,
            packet_type=PacketType.BELIEF_UPDATE,
            next_steps=["l1_review"],
        ),
        TemplateStep(
            step_id="l1_review",
            owner_layer=LayerSource.LAYER_1,  # L1 constitutional review
            fsm_state=FSMState.S7_REVIEW,  # Final review
            packet_type=PacketType.BELIEF_UPDATE,
            next_steps=["idle_end"],
        ),
        TemplateStep(
            step_id="idle_end",
            owner_layer=LayerSource.LAYER_1,
            fsm_state=FSMState.S0_IDLE,
            packet_type=None,
            next_steps=[],
        ),
    ],
    entry_step="idle_start",
    exit_steps=["idle_end"],
)


# =============================================================================
# CANONICAL TEMPLATE REGISTRY
# =============================================================================

CANONICAL_TEMPLATES: dict[TemplateID, EpisodeTemplate] = {
    TemplateID.TEMPLATE_A: TEMPLATE_A,
    TemplateID.TEMPLATE_B: TEMPLATE_B,
    TemplateID.TEMPLATE_C: TEMPLATE_C,
    TemplateID.TEMPLATE_D: TEMPLATE_D,
    TemplateID.TEMPLATE_E: TEMPLATE_E,
    TemplateID.TEMPLATE_F: TEMPLATE_F,
    TemplateID.TEMPLATE_G: TEMPLATE_G,
    TemplateID.TEMPLATE_H: TEMPLATE_H,
}


def get_template(template_id: TemplateID) -> EpisodeTemplate:
    """Get a canonical template by ID."""
    return CANONICAL_TEMPLATES[template_id]


def get_all_templates() -> list[EpisodeTemplate]:
    """Get all canonical templates."""
    return list(CANONICAL_TEMPLATES.values())

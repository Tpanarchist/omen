"""
Vocabulary enums — the shared language of the ACE framework.

All enumerated types referenced by packets, policies, and validators.
Extracted from OMEN.md specification.
"""

from enum import Enum, auto


# =============================================================================
# EPISTEMIC POLICY (E-POL) — OMEN.md §8.1
# =============================================================================

class EpistemicStatus(str, Enum):
    """
    Classification of how a claim is known.
    
    Every consequential claim must be exactly one of these.
    Spec: OMEN.md §8.1 "Epistemic Status Classes"
    """
    OBSERVED = "OBSERVED"          # From tool/sensor read or user observation
    DERIVED = "DERIVED"            # Deterministic computation from observed/known inputs
    REMEMBERED = "REMEMBERED"      # From persistent memory/doctrine/cache
    INFERRED = "INFERRED"          # Logical/probabilistic conclusion
    HYPOTHESIZED = "HYPOTHESIZED"  # Candidate explanation/plan not yet believed
    UNKNOWN = "UNKNOWN"            # Cannot answer/justify


class FreshnessClass(str, Enum):
    """
    Temporal validity classification for observations and memories.
    
    Spec: OMEN.md §8.1 "Freshness/staleness"
    """
    REALTIME = "REALTIME"          # Seconds to minutes
    OPERATIONAL = "OPERATIONAL"    # Minutes to hours
    STRATEGIC = "STRATEGIC"        # Hours to days
    ARCHIVAL = "ARCHIVAL"          # Days to months


class EvidenceRefType(str, Enum):
    """
    Type of evidence reference backing a claim.
    
    Spec: OMEN.md §8.1 "Evidence references"
    """
    TOOL_OUTPUT = "tool_output"
    USER_OBSERVATION = "user_observation"
    MEMORY_ITEM = "memory_item"
    DERIVED_CALC = "derived_calc"


# =============================================================================
# QUALITY POLICY (Q-POL) — OMEN.md §8.2
# =============================================================================

class ImpactLevel(str, Enum):
    """
    Magnitude of potential impact.
    
    Spec: OMEN.md §8.2.1 "Stakes classification"
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Irreversibility(str, Enum):
    """
    Degree to which an action can be undone.
    
    Spec: OMEN.md §8.2.1 "Stakes classification"
    """
    REVERSIBLE = "REVERSIBLE"
    PARTIAL = "PARTIAL"
    IRREVERSIBLE = "IRREVERSIBLE"


class UncertaintyLevel(str, Enum):
    """
    Degree of uncertainty about outcomes.
    
    Spec: OMEN.md §8.2.1 "Stakes classification"
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Adversariality(str, Enum):
    """
    Environmental threat/volatility level.
    
    Spec: OMEN.md §8.2.1 "Stakes classification"
    """
    BENIGN = "BENIGN"
    CONTESTED = "CONTESTED"
    HOSTILE = "HOSTILE"


class StakesLevel(str, Enum):
    """
    Aggregate stakes classification derived from the four axes.
    
    Spec: OMEN.md §8.2.1 "Stakes classification"
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class QualityTier(str, Enum):
    """
    Required quality/effort level for a task.
    
    SUBPAR outputs MUST NOT authorize external action.
    CRITICAL stakes require SUPERB unless emergency exception.
    
    Spec: OMEN.md §8.2.2 "Quality tiers"
    """
    SUBPAR = "SUBPAR"
    PAR = "PAR"
    SUPERB = "SUPERB"


class VerificationRequirement(str, Enum):
    """
    How much verification is required before acting.
    
    Spec: OMEN.md §8.2.3 "Verification requirements by tier"
    """
    OPTIONAL = "OPTIONAL"          # SUBPAR: optional verification
    VERIFY_ONE = "VERIFY_ONE"      # PAR: verify at least one load-bearing assumption
    VERIFY_ALL = "VERIFY_ALL"      # SUPERB: verify all load-bearing assumptions


# =============================================================================
# COMPUTE POLICY (C-POL) — OMEN.md §8.3
# =============================================================================

class TaskClass(str, Enum):
    """
    Semantic classification of task type.
    
    Appears in Layer 5 → Layer 6 directives.
    Spec: OMEN.md §8.3.2 "Task semantic classification"
    """
    FIND = "FIND"
    LOOKUP = "LOOKUP"
    SEARCH = "SEARCH"
    CREATE = "CREATE"
    VERIFY = "VERIFY"
    COMPILE = "COMPILE"


class ToolsState(str, Enum):
    """
    Current availability of external tools.
    
    Spec: OMEN.md §8.3.7 "Degraded modes"
    """
    TOOLS_OK = "tools_ok"
    TOOLS_PARTIAL = "tools_partial"
    TOOLS_DOWN = "tools_down"


class ToolSafety(str, Enum):
    """
    Safety classification of tool operations.
    
    WRITE/MIXED require authorization tokens.
    Spec: OMEN.md §8.3.6 "Tool safety gates"
    """
    READ = "READ"
    WRITE = "WRITE"
    MIXED = "MIXED"


# =============================================================================
# PACKET MODEL — OMEN.md §9
# =============================================================================

class PacketType(str, Enum):
    """
    The nine canonical packet types.
    
    Spec: OMEN.md §9.3 "Packet types"
    """
    OBSERVATION = "ObservationPacket"
    BELIEF_UPDATE = "BeliefUpdatePacket"
    DECISION = "DecisionPacket"
    VERIFICATION_PLAN = "VerificationPlanPacket"
    TOOL_AUTHORIZATION = "ToolAuthorizationToken"
    TASK_DIRECTIVE = "TaskDirectivePacket"
    TASK_RESULT = "TaskResultPacket"
    ESCALATION = "EscalationPacket"
    INTEGRITY_ALERT = "IntegrityAlertPacket"


class LayerSource(str, Enum):
    """
    Which layer originated a packet.
    
    Spec: OMEN.md §9.1 "Packet header", §6 "ACE Layers"
    """
    LAYER_1 = "1"          # Aspirational
    LAYER_2 = "2"          # Global Strategy
    LAYER_3 = "3"          # Agent Model
    LAYER_4 = "4"          # Executive Function
    LAYER_5 = "5"          # Cognitive Control
    LAYER_6 = "6"          # Task Prosecution
    INTEGRITY = "Integrity"


# =============================================================================
# EPISODE STATE MACHINE — OMEN.md §10
# =============================================================================

class FSMState(str, Enum):
    """
    Episode state machine states.
    
    Spec: OMEN.md §10.2 "FSM states"
    """
    S0_IDLE = "S0_IDLE"
    S1_SENSE = "S1_SENSE"
    S2_MODEL = "S2_MODEL"
    S3_DECIDE = "S3_DECIDE"
    S4_VERIFY = "S4_VERIFY"
    S5_AUTHORIZE = "S5_AUTHORIZE"
    S6_EXECUTE = "S6_EXECUTE"
    S7_REVIEW = "S7_REVIEW"
    S8_ESCALATED = "S8_ESCALATED"
    S9_SAFEMODE = "S9_SAFEMODE"


# =============================================================================
# DECISION OUTCOMES — OMEN.md §15.2
# =============================================================================

class DecisionOutcome(str, Enum):
    """
    Possible outcomes of a decision.
    
    Spec: OMEN.md §15.2 "Canonical Decision Packet Example"
    """
    ACT = "ACT"                    # Proceed with action
    VERIFY_FIRST = "VERIFY_FIRST"  # Verify before acting
    ESCALATE = "ESCALATE"          # Escalate to human/higher layer
    DEFER = "DEFER"                # Defer action


# =============================================================================
# TASK RESULT STATUS
# =============================================================================

class TaskResultStatus(str, Enum):
    """
    Outcome status of a completed task.
    
    Spec: OMEN.md §10.4 "Task closure"
    """
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    CANCELLED = "CANCELLED"

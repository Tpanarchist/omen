# OMEN API Reference

Quick reference for OMEN's public API.

---

## Core Orchestration

### `omen.orchestrator`

#### `Orchestrator`

Main entry point for episode execution.

```python
class Orchestrator:
    def __init__(
        config: OrchestratorConfig | None = None,
        layer_pool: LayerPool | None = None,
        compiler: TemplateCompiler | None = None,
        validator: TemplateValidator | None = None,
        episode_store: EpisodeStore | None = None,
    ): ...
    
    def run_template(
        template_id: TemplateID,
        *,
        correlation_id: UUID | None = None,
        campaign_id: str | None = None,
        stakes_level: StakesLevel | None = None,
        quality_tier: QualityTier | None = None,
        tools_state: ToolsState | None = None,
        token_budget: int | None = None,
        tool_call_budget: int | None = None,
        time_budget_seconds: int | None = None,
        initial_packets: list[Any] | None = None,
    ) -> EpisodeResult: ...
    
    def run_episode(
        template: EpisodeTemplate,
        **kwargs  # Same as run_template
    ) -> EpisodeResult: ...
    
    def compile_template(
        template_id: TemplateID,
        **context_kwargs
    ) -> CompilationResult: ...
    
    def get_episode(correlation_id: UUID) -> EpisodeRecord | None: ...
    def list_episodes(template_id: str | None = None, success: bool | None = None, limit: int = 100) -> list[EpisodeRecord]: ...
    def get_layer_pool() -> LayerPool: ...
    def get_buses() -> tuple[NorthboundBus, SouthboundBus]: ...
```

#### `OrchestratorConfig`

```python
@dataclass
class OrchestratorConfig:
    llm_client: LLMClient | None = None
    default_stakes: StakesLevel = StakesLevel.LOW
    default_quality: QualityTier = QualityTier.PAR
    default_tools_state: ToolsState = ToolsState.TOOLS_OK
    default_token_budget: int = 1000
    default_tool_call_budget: int = 10
    default_time_budget_seconds: int = 300
    max_steps: int = 100
    validate_templates: bool = True
    episode_store: EpisodeStore | None = None
    auto_save: bool = True
```

#### Factory Functions

```python
def create_orchestrator(llm_client: LLMClient | None = None, config: OrchestratorConfig | None = None) -> Orchestrator: ...
def create_mock_orchestrator(responses: dict[LayerSource, list[str]] | None = None) -> Orchestrator: ...
```

#### `EpisodeResult`

```python
@dataclass
class EpisodeResult:
    correlation_id: UUID
    template_id: str
    success: bool
    steps_completed: list[StepResult]
    final_step: str | None
    total_duration_seconds: float
    errors: list[str]
    ledger_summary: dict[str, Any]
    
    @property
    def step_count(self) -> int: ...
```

#### `StepResult`

```python
@dataclass
class StepResult:
    step_id: str
    layer: LayerSource
    success: bool
    output: LayerOutput | None
    packets_emitted: int
    error: str | None
    duration_seconds: float
```

---

## Vocabulary

### `omen.vocabulary`

#### Enums

```python
class LayerSource(Enum):
    LAYER_1 = "1"
    LAYER_2 = "2"
    LAYER_3 = "3"
    LAYER_4 = "4"
    LAYER_5 = "5"
    LAYER_6 = "6"
    INTEGRITY = "integrity"

class PacketType(Enum):
    OBSERVATION = "observation"
    BELIEF_UPDATE = "belief_update"
    DECISION = "decision"
    VERIFICATION_PLAN = "verification_plan"
    TOOL_AUTHORIZATION = "tool_authorization"
    TASK_DIRECTIVE = "task_directive"
    TASK_RESULT = "task_result"
    ESCALATION = "escalation"
    INTEGRITY_ALERT = "integrity_alert"

class FSMState(Enum):
    S0_IDLE = "S0_IDLE"
    S1_SENSE = "S1_SENSE"
    S2_MODEL = "S2_MODEL"
    S3_DECIDE = "S3_DECIDE"
    S4_VERIFY = "S4_VERIFY"
    S5_AUTHORIZE = "S5_AUTHORIZE"
    S6_ACT = "S6_ACT"
    S7_REVIEW = "S7_REVIEW"

class StakesLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class QualityTier(Enum):
    SUBPAR = "SUBPAR"
    PAR = "PAR"
    SUPERB = "SUPERB"

class ToolsState(Enum):
    TOOLS_OK = "TOOLS_OK"
    TOOLS_PARTIAL = "TOOLS_PARTIAL"
    TOOLS_DOWN = "TOOLS_DOWN"

class DecisionOutcome(Enum):
    ACT = "ACT"
    VERIFY_FIRST = "VERIFY_FIRST"
    ESCALATE = "ESCALATE"
    DEFER = "DEFER"

class EpistemicStatus(Enum):
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    INFERRED = "INFERRED"
    HYPOTHESIZED = "HYPOTHESIZED"
    STALE = "STALE"

class TemplateID(Enum):
    TEMPLATE_A = "TEMPLATE_A"
    TEMPLATE_B = "TEMPLATE_B"
    TEMPLATE_C = "TEMPLATE_C"
    TEMPLATE_D = "TEMPLATE_D"
    TEMPLATE_E = "TEMPLATE_E"
    TEMPLATE_F = "TEMPLATE_F"
    TEMPLATE_G = "TEMPLATE_G"
    TEMPLATE_H = "TEMPLATE_H"
```

---

## Templates

### `omen.templates`

#### `EpisodeTemplate`

```python
@dataclass
class EpisodeTemplate:
    template_id: TemplateID
    name: str
    description: str
    steps: list[TemplateStep]
    entry_step: str
    exit_steps: list[str]
    constraints: TemplateConstraints
```

#### `TemplateStep`

```python
@dataclass
class TemplateStep:
    step_id: str
    fsm_state: FSMState
    owner_layer: LayerSource
    packet_type: PacketType | None
    next_steps: list[str]
    constraints: StepConstraints | None = None
```

#### Canonical Templates

```python
TEMPLATE_A: EpisodeTemplate  # Grounding Loop
TEMPLATE_B: EpisodeTemplate  # Verification Loop
TEMPLATE_C: EpisodeTemplate  # Read-Only Act
TEMPLATE_D: EpisodeTemplate  # Write Act
TEMPLATE_E: EpisodeTemplate  # Escalation
TEMPLATE_F: EpisodeTemplate  # Degraded Tools
TEMPLATE_G: EpisodeTemplate  # Compile-to-Code
TEMPLATE_H: EpisodeTemplate  # Full-Stack Mission

CANONICAL_TEMPLATES: dict[TemplateID, EpisodeTemplate]

def get_template(template_id: TemplateID) -> EpisodeTemplate | None: ...
```

---

## Layers

### `omen.layers`

#### `Layer` (Abstract)

```python
class Layer(ABC):
    layer_id: LayerSource
    llm_client: LLMClient
    
    def invoke(input: LayerInput) -> LayerOutput: ...
    
    @property
    @abstractmethod
    def system_prompt(self) -> str: ...
    
    @abstractmethod
    def build_context(input: LayerInput) -> str: ...
    
    @abstractmethod
    def parse_response(response: str, input: LayerInput) -> list[Any]: ...
```

#### `LayerInput`

```python
@dataclass
class LayerInput:
    packets: list[Any]
    correlation_id: UUID
    campaign_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
```

#### `LayerOutput`

```python
@dataclass
class LayerOutput:
    layer: LayerSource
    packets: list[Any]
    raw_response: str
    correlation_id: UUID
    success: bool = True
    errors: list[str] = field(default_factory=list)
```

#### `LLMClient` (Protocol)

```python
@runtime_checkable
class LLMClient(Protocol):
    def complete(system_prompt: str, user_message: str, **kwargs) -> str: ...
```

#### Layer Contracts

```python
@dataclass(frozen=True)
class LayerContract:
    layer: LayerSource
    can_emit: frozenset[PacketType]
    can_receive: frozenset[PacketType]
    description: str

L1_CONTRACT: LayerContract
L2_CONTRACT: LayerContract
L3_CONTRACT: LayerContract
L4_CONTRACT: LayerContract
L5_CONTRACT: LayerContract
L6_CONTRACT: LayerContract
INTEGRITY_CONTRACT: LayerContract

def get_contract(layer: LayerSource) -> LayerContract: ...
```

#### System Prompts

```python
LAYER_1_PROMPT: str  # Aspirational
LAYER_2_PROMPT: str  # Global Strategy
LAYER_3_PROMPT: str  # Agent Model
LAYER_4_PROMPT: str  # Executive Function
LAYER_5_PROMPT: str  # Cognitive Control
LAYER_6_PROMPT: str  # Task Prosecution

LAYER_PROMPTS: dict[LayerSource, str]
```

---

## Tools

### `omen.tools`

#### `Tool` (Protocol)

```python
@runtime_checkable
class Tool(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str: ...
    @property
    def safety(self) -> ToolSafety: ...
    def execute(params: dict[str, Any]) -> ToolResult: ...
```

#### `ToolSafety`

```python
class ToolSafety(Enum):
    READ = "READ"
    WRITE = "WRITE"
    MIXED = "MIXED"
```

#### `ToolResult`

```python
@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str | None = None
    evidence_ref: EvidenceRef | None = None
    execution_time_ms: float = 0.0
    
    @classmethod
    def ok(data: Any, tool_name: str, raw_data: Any = None) -> ToolResult: ...
    
    @classmethod
    def fail(error: str) -> ToolResult: ...
```

#### `EvidenceRef`

```python
@dataclass
class EvidenceRef:
    ref_id: str
    ref_type: str = "tool_output"
    tool_name: str = ""
    timestamp: datetime
    reliability_score: float = 0.95
    raw_data: Any = None
    
    def to_dict() -> dict[str, Any]: ...
```

#### `ToolRegistry`

```python
class ToolRegistry:
    def register(tool: Tool) -> None: ...
    def unregister(name: str) -> Tool | None: ...
    def get(name: str) -> Tool | None: ...
    def list_tools() -> list[Tool]: ...
    def list_tool_names() -> list[str]: ...
    def get_tool_descriptions() -> str: ...
    def execute(tool_name: str, params: dict, token: ActiveToken | None = None) -> ToolResult: ...

def create_registry() -> ToolRegistry: ...
def create_default_registry() -> ToolRegistry: ...
```

#### Built-in Tools

```python
class ClockTool(BaseTool): ...      # READ
class FileReadTool(BaseTool): ...   # READ
class FileWriteTool(BaseTool): ...  # WRITE
class HttpGetTool(BaseTool): ...    # READ
class EnvironmentTool(BaseTool): ... # READ
```

---

## Episode Persistence

### `omen.episode`

#### `EpisodeRecord`

```python
@dataclass
class EpisodeRecord:
    correlation_id: UUID
    template_id: str
    campaign_id: str | None
    started_at: datetime
    completed_at: datetime | None
    success: bool
    final_step: str | None
    errors: list[str]
    stakes_level: str
    quality_tier: str
    tools_state: str
    steps: list[StepRecord]
    packets: list[PacketRecord]
    budget_allocated: dict[str, int]
    budget_consumed: dict[str, int]
    evidence_refs: list[dict]
    assumptions: list[dict]
    contradictions: list[str]
    
    @property
    def duration_seconds(self) -> float: ...
    @property
    def step_count(self) -> int: ...
    
    def to_dict() -> dict: ...
    def to_json() -> str: ...
    @classmethod
    def from_dict(data: dict) -> EpisodeRecord: ...
    @classmethod
    def from_json(json_str: str) -> EpisodeRecord: ...
```

#### `EpisodeStore` (Protocol)

```python
@runtime_checkable
class EpisodeStore(Protocol):
    def save(episode: EpisodeRecord) -> None: ...
    def load(correlation_id: UUID) -> EpisodeRecord | None: ...
    def exists(correlation_id: UUID) -> bool: ...
    def delete(correlation_id: UUID) -> bool: ...
    def query(template_id: str | None = None, campaign_id: str | None = None, success: bool | None = None, since: datetime | None = None, until: datetime | None = None, limit: int = 100) -> list[EpisodeRecord]: ...
    def count() -> int: ...
```

#### Storage Implementations

```python
class InMemoryStore: ...  # For testing
class SQLiteStore: ...    # For persistence

def create_memory_store() -> InMemoryStore: ...
def create_sqlite_store(db_path: str | Path = "omen_episodes.db") -> SQLiteStore: ...
```

---

## Integrity

### `omen.integrity`

#### `SafeMode`

```python
class SafeMode(Enum):
    NORMAL = "normal"
    CAUTIOUS = "cautious"
    RESTRICTED = "restricted"
    HALTED = "halted"
```

#### `AlertSeverity`

```python
class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"
```

#### `AlertType`

```python
class AlertType(Enum):
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_REVOKED = "token_revoked"
    CONSTITUTIONAL_VETO = "constitutional_veto"
    CONTRACT_VIOLATION = "contract_violation"
    CONTRADICTION_DETECTED = "contradiction_detected"
    SAFE_MODE_TRIGGERED = "safe_mode_triggered"
```

#### `IntegrityMonitor`

```python
class IntegrityMonitor:
    def __init__(config: MonitorConfig | None = None, on_alert: Callable[[IntegrityEvent], None] | None = None): ...
    
    @property
    def safe_mode(self) -> SafeMode: ...
    @property
    def is_halted(self) -> bool: ...
    
    def register_ledger(ledger: EpisodeLedger) -> None: ...
    def unregister_ledger(correlation_id: UUID) -> None: ...
    def subscribe_to_buses(northbound: NorthboundBus, southbound: SouthboundBus) -> None: ...
    def check_budget(ledger: EpisodeLedger) -> IntegrityEvent | None: ...
    def check_token(token: ActiveToken) -> IntegrityEvent | None: ...
    def process_veto(packet: Any, correlation_id: UUID) -> IntegrityEvent | None: ...
    def revoke_token(ledger: EpisodeLedger, token_id: str, reason: str) -> IntegrityEvent: ...
    def flag_contradiction(ledger: EpisodeLedger, detail: str) -> IntegrityEvent | None: ...
    def transition_safe_mode(mode: SafeMode, reason: str = "") -> IntegrityEvent: ...
    def reset() -> None: ...
    def get_events(correlation_id: UUID | None = None, severity: AlertSeverity | None = None, limit: int = 100) -> list[IntegrityEvent]: ...

def create_monitor(config: MonitorConfig | None = None, on_alert: Callable | None = None) -> IntegrityMonitor: ...
```

---

## Observability

### `omen.observability`

#### Logging

```python
def set_correlation_id(cid: UUID | str | None) -> None: ...
def get_correlation_id() -> str | None: ...
def configure_logging(level: int = logging.INFO, json_format: bool = False, stream: Any = None) -> None: ...
def get_logger(name: str) -> logging.Logger: ...

class LogContext:
    def __init__(correlation_id: UUID | str | None): ...
    def __enter__(self): ...
    def __exit__(*args): ...
```

#### Metrics

```python
class Counter:
    def inc(amount: float = 1.0) -> None: ...
    @property
    def value(self) -> float: ...
    def reset() -> None: ...

class Gauge:
    def set(value: float) -> None: ...
    def inc(amount: float = 1.0) -> None: ...
    def dec(amount: float = 1.0) -> None: ...
    @property
    def value(self) -> float: ...

class Histogram:
    def observe(value: float) -> None: ...
    @property
    def count(self) -> int: ...
    @property
    def sum(self) -> float: ...
    @property
    def avg(self) -> float: ...
    @property
    def min(self) -> float: ...
    @property
    def max(self) -> float: ...
    def to_dict() -> dict[str, float]: ...

class MetricsRegistry:
    episodes_total: Counter
    episodes_success: Counter
    episodes_failed: Counter
    episode_duration_seconds: Histogram
    step_duration_seconds: Histogram
    llm_latency_seconds: Histogram
    tokens_consumed: Counter
    tool_calls_total: Counter
    contract_violations: Counter
    budget_exceeded: Counter
    safe_mode_transitions: Counter
    active_episodes: Gauge
    
    def to_dict() -> dict[str, Any]: ...
    def reset() -> None: ...

def get_metrics() -> MetricsRegistry: ...
def reset_metrics() -> None: ...
```

#### Debug

```python
@dataclass
class DebugCapture:
    correlation_id: str
    timestamp: datetime
    layer: str
    step_id: str
    system_prompt: str
    user_message: str
    raw_response: str
    parsed_packets: list[dict]
    parse_errors: list[str]
    contract_violations: list[str]
    
    def to_dict() -> dict[str, Any]: ...
    def to_json() -> str: ...

class DebugRecorder:
    enabled: bool
    def capture(...) -> DebugCapture | None: ...
    def get_captures(correlation_id: str | None = None, layer: str | None = None) -> list[DebugCapture]: ...
    def clear() -> None: ...

def enable_debug(output_dir: Path | str | None = None, log_to_console: bool = True) -> None: ...
def disable_debug() -> None: ...
def get_debug_recorder() -> DebugRecorder: ...
def is_debug_enabled() -> bool: ...
```

---

## Clients

### `omen.clients`

#### `OpenAIClient`

```python
class OpenAIClient:
    def __init__(config: OpenAIConfig | None = None): ...
    def complete(system_prompt: str, user_message: str, **kwargs) -> str: ...
    @property
    def last_usage(self) -> dict[str, int]: ...

@dataclass
class OpenAIConfig:
    api_key: str | None = None  # Falls back to OPENAI_API_KEY
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: float = 60.0
    max_retries: int = 3
    retry_delay: float = 1.0

def create_openai_client(model: str = "gpt-4o-mini", **kwargs) -> OpenAIClient: ...

OPENAI_AVAILABLE: bool  # Whether openai package is installed
```

---

## Buses

### `omen.buses`

#### `NorthboundBus`

Telemetry flowing up (L6 → L1).

```python
class NorthboundBus(Bus):
    def direction() -> str: ...  # "northbound"
    def can_route(source: LayerSource, target: LayerSource | None) -> bool: ...
```

#### `SouthboundBus`

Directives flowing down (L1 → L6).

```python
class SouthboundBus(Bus):
    def direction() -> str: ...  # "southbound"
    def can_route(source: LayerSource, target: LayerSource | None) -> bool: ...
```

#### `Bus` (Abstract)

```python
class Bus(ABC):
    def subscribe(layer: LayerSource, handler: Callable[[BusMessage], None]) -> None: ...
    def unsubscribe(layer: LayerSource) -> None: ...
    def publish(message: BusMessage) -> tuple[list[LayerSource], list[DeliveryFailure]]: ...
    def get_message_log(limit: int = 100) -> list[BusMessage]: ...

def create_northbound_bus() -> NorthboundBus: ...
def create_southbound_bus() -> SouthboundBus: ...
```

#### `BusMessage`

```python
@dataclass
class BusMessage:
    packet: Any
    source_layer: LayerSource
    target_layer: LayerSource | None  # None = broadcast
    correlation_id: UUID
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def packet_type(self) -> PacketType | None: ...
```

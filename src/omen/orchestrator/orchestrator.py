"""
Orchestrator — Unified API for episode execution.

Combines template compilation, ledger management, and episode running
into a single coherent interface.

Spec: OMEN.md §10.4, §11
"""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from omen.vocabulary import (
    LayerSource,
    TemplateID,
    QualityTier,
    StakesLevel,
    ToolsState,
)
from omen.templates import (
    EpisodeTemplate,
    CANONICAL_TEMPLATES,
    get_template,
    TemplateValidator,
    create_template_validator,
)
from omen.compiler import (
    CompilationContext,
    CompilationResult,
    TemplateCompiler,
    create_compiler,
    create_context,
    CompiledEpisode,
)
from omen.buses import (
    NorthboundBus,
    SouthboundBus,
    create_northbound_bus,
    create_southbound_bus,
)
from omen.layers import LLMClient, MockLLMClient
from omen.orchestrator.ledger import (
    EpisodeLedger,
    BudgetState,
    create_ledger,
)
from omen.orchestrator.pool import (
    LayerPool,
    create_layer_pool,
    create_mock_layer_pool,
)
from omen.orchestrator.runner import (
    EpisodeRunner,
    EpisodeResult,
    create_runner,
)


# =============================================================================
# ORCHESTRATOR CONFIGURATION
# =============================================================================

@dataclass
class OrchestratorConfig:
    """
    Configuration for the orchestrator.
    
    Allows customization of components and defaults.
    """
    # LLM configuration
    llm_client: LLMClient | None = None
    
    # Default policy
    default_stakes: StakesLevel = StakesLevel.LOW
    default_quality: QualityTier = QualityTier.PAR
    default_tools_state: ToolsState = ToolsState.TOOLS_OK
    
    # Default budgets
    default_token_budget: int = 1000
    default_tool_call_budget: int = 10
    default_time_budget_seconds: int = 300
    
    # Execution limits
    max_steps: int = 100
    
    # Validation
    validate_templates: bool = True


# =============================================================================
# ORCHESTRATOR
# =============================================================================

class Orchestrator:
    """
    Unified API for OMEN episode execution.
    
    Combines template compilation, layer management, and episode running.
    
    Usage:
        orchestrator = Orchestrator()
        result = orchestrator.run_template(TemplateID.TEMPLATE_A)
    
    Or with context:
        result = orchestrator.run_template(
            TemplateID.TEMPLATE_D,
            stakes_level=StakesLevel.HIGH,
            quality_tier=QualityTier.SUPERB,
        )
    """
    
    def __init__(
        self,
        config: OrchestratorConfig | None = None,
        layer_pool: LayerPool | None = None,
        compiler: TemplateCompiler | None = None,
        validator: TemplateValidator | None = None,
    ):
        """
        Initialize orchestrator.
        
        Args:
            config: Configuration options
            layer_pool: Pre-configured layer pool (optional)
            compiler: Pre-configured compiler (optional)
            validator: Pre-configured validator (optional)
        """
        self.config = config or OrchestratorConfig()
        
        # Set up validator
        self.validator = validator
        if self.validator is None and self.config.validate_templates:
            self.validator = create_template_validator()
        
        # Set up compiler
        self.compiler = compiler or create_compiler(validator=self.validator)
        
        # Set up layer pool
        if layer_pool is not None:
            self.layer_pool = layer_pool
        else:
            self.layer_pool = create_layer_pool(
                llm_client=self.config.llm_client,
            )
        
        # Set up buses
        self.northbound_bus = create_northbound_bus()
        self.southbound_bus = create_southbound_bus()
        
        # Set up runner
        self.runner = create_runner(
            layer_pool=self.layer_pool,
            northbound_bus=self.northbound_bus,
            southbound_bus=self.southbound_bus,
            max_steps=self.config.max_steps,
        )
    
    def run_template(
        self,
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
    ) -> EpisodeResult:
        """
        Run an episode using a canonical template.
        
        Args:
            template_id: Which template to use
            correlation_id: Episode ID (auto-generated if not provided)
            campaign_id: Parent campaign ID
            stakes_level: Stakes for this episode
            quality_tier: Quality tier for this episode
            tools_state: Current tools availability
            token_budget: Token budget override
            tool_call_budget: Tool call budget override
            time_budget_seconds: Time budget override
            initial_packets: Initial packets to seed execution
        
        Returns:
            EpisodeResult with execution details
        """
        # Get template
        template = get_template(template_id)
        if template is None:
            return EpisodeResult(
                correlation_id=correlation_id or uuid4(),
                template_id=template_id.value,
                success=False,
                errors=[f"Template not found: {template_id.value}"],
            )
        
        return self.run_episode(
            template=template,
            correlation_id=correlation_id,
            campaign_id=campaign_id,
            stakes_level=stakes_level,
            quality_tier=quality_tier,
            tools_state=tools_state,
            token_budget=token_budget,
            tool_call_budget=tool_call_budget,
            time_budget_seconds=time_budget_seconds,
            initial_packets=initial_packets,
        )
    
    def run_episode(
        self,
        template: EpisodeTemplate,
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
    ) -> EpisodeResult:
        """
        Run an episode using a custom or canonical template.
        
        Args:
            template: The episode template to execute
            ... (same as run_template)
        
        Returns:
            EpisodeResult with execution details
        """
        # Generate correlation ID if needed
        cid = correlation_id or uuid4()
        
        # Build compilation context
        context = self._build_context(
            correlation_id=cid,
            campaign_id=campaign_id,
            stakes_level=stakes_level,
            quality_tier=quality_tier,
            tools_state=tools_state,
            token_budget=token_budget,
            tool_call_budget=tool_call_budget,
            time_budget_seconds=time_budget_seconds,
        )
        
        # Compile template
        compilation = self.compiler.compile(template, context)
        if not compilation.success:
            return EpisodeResult(
                correlation_id=cid,
                template_id=template.template_id.value,
                success=False,
                errors=[e.message for e in compilation.errors],
            )
        
        # Create ledger
        ledger = self._create_ledger(cid, context, template)
        
        # Run episode
        return self.runner.run(
            episode=compilation.episode,
            ledger=ledger,
            initial_packets=initial_packets,
        )
    
    def compile_template(
        self,
        template_id: TemplateID,
        **context_kwargs,
    ) -> CompilationResult:
        """
        Compile a template without running it.
        
        Useful for inspection or deferred execution.
        """
        template = get_template(template_id)
        if template is None:
            from omen.compiler import CompilationError
            return CompilationResult(
                success=False,
                errors=[CompilationError(None, f"Template not found: {template_id.value}")],
            )
        
        context = self._build_context(**context_kwargs)
        return self.compiler.compile(template, context)
    
    def get_layer_pool(self) -> LayerPool:
        """Get the layer pool for inspection or modification."""
        return self.layer_pool
    
    def get_buses(self) -> tuple[NorthboundBus, SouthboundBus]:
        """Get the buses for inspection."""
        return self.northbound_bus, self.southbound_bus
    
    def _build_context(
        self,
        correlation_id: UUID | None = None,
        campaign_id: str | None = None,
        stakes_level: StakesLevel | None = None,
        quality_tier: QualityTier | None = None,
        tools_state: ToolsState | None = None,
        token_budget: int | None = None,
        tool_call_budget: int | None = None,
        time_budget_seconds: int | None = None,
    ) -> CompilationContext:
        """Build compilation context with defaults."""
        ctx = create_context(
            stakes_level=stakes_level or self.config.default_stakes,
            quality_tier=quality_tier or self.config.default_quality,
            tools_state=tools_state or self.config.default_tools_state,
        )
        
        if correlation_id:
            ctx = ctx.with_correlation_id(correlation_id)
        
        ctx.campaign_id = campaign_id
        ctx.budgets.token_budget = token_budget or self.config.default_token_budget
        ctx.budgets.tool_call_budget = tool_call_budget or self.config.default_tool_call_budget
        ctx.budgets.time_budget_seconds = time_budget_seconds or self.config.default_time_budget_seconds
        
        return ctx
    
    def _create_ledger(
        self,
        correlation_id: UUID,
        context: CompilationContext,
        template: EpisodeTemplate,
    ) -> EpisodeLedger:
        """Create ledger for episode execution."""
        return create_ledger(
            correlation_id=correlation_id,
            campaign_id=context.campaign_id,
            stakes_level=context.stakes.stakes_level,
            quality_tier=context.quality.quality_tier,
            tools_state=context.tools_state,
            budget=BudgetState(
                token_budget=context.budgets.token_budget,
                tool_call_budget=context.budgets.tool_call_budget,
                time_budget_seconds=context.budgets.time_budget_seconds,
            ),
            template_id=template.template_id.value,
        )


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_orchestrator(
    llm_client: LLMClient | None = None,
    config: OrchestratorConfig | None = None,
) -> Orchestrator:
    """
    Create a configured orchestrator.
    
    Args:
        llm_client: LLM client for layer invocations
        config: Full configuration (overrides llm_client if provided)
    
    Returns:
        Configured Orchestrator
    """
    if config is None:
        config = OrchestratorConfig(llm_client=llm_client)
    return Orchestrator(config=config)


def create_mock_orchestrator(
    responses: dict[LayerSource, list[str]] | None = None,
) -> Orchestrator:
    """
    Create an orchestrator with mock LLM responses for testing.
    
    Args:
        responses: Dict of layer_id -> list of responses
    
    Returns:
        Orchestrator with mock layer pool
    """
    pool = create_mock_layer_pool(responses=responses)
    return Orchestrator(layer_pool=pool)

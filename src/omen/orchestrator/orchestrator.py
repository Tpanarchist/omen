"""
Orchestrator — Unified API for episode execution.

Combines template compilation, ledger management, and episode running
into a single coherent interface.

Spec: OMEN.md §10.4, §11
"""

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Any
from uuid import UUID, uuid4

from omen.vocabulary import (
    Adversariality,
    EpistemicStatus,
    EvidenceRefType,
    ImpactLevel,
    Irreversibility,
    LayerSource,
    PacketType,
    TemplateID,
    QualityTier,
    StakesLevel,
    TaskClass,
    ToolsState,
    UncertaintyLevel,
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
from omen.memory.belief_store import BeliefRecord, BeliefStore
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
from omen.episode import (
    EpisodeStore,
    EpisodeRecord,
    StepRecord,
    PacketRecord,
)
from omen.schemas.header import PacketHeader
from omen.schemas.mcp import MCP
from omen.schemas.packets.observation import (
    ObservationPacket,
    ObservationPayload,
    ObservationSource,
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
    
    # Persistence
    episode_store: EpisodeStore | None = None
    belief_store: BeliefStore | None = None
    auto_save: bool = True  # Save episodes on completion


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
        episode_store: EpisodeStore | None = None,
        belief_store: BeliefStore | None = None,
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
        
        # Set up episode storage
        self.episode_store = episode_store or self.config.episode_store
        self.belief_store = belief_store or self.config.belief_store
    
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
        user_query: str | None = None,
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
            user_query: Optional user query for memory retrieval
        
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
            user_query=user_query,
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
        user_query: str | None = None,
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

        retrieved_packets = self._retrieve_memory_packets(
            template=template,
            context=context,
            user_query=user_query,
        )
        combined_packets = retrieved_packets + (initial_packets or [])
        
        # Run episode
        result = self.runner.run(
            episode=compilation.episode,
            ledger=ledger,
            initial_packets=combined_packets,
        )
        
        # Save episode if store configured
        if self.episode_store and self.config.auto_save:
            record = self._create_episode_record(result, ledger, template, context)
            self.episode_store.save(record)
        
        return result

    def _retrieve_memory_packets(
        self,
        template: EpisodeTemplate,
        context: CompilationContext,
        user_query: str | None = None,
        limit: int = 5,
    ) -> list[ObservationPacket]:
        """Retrieve memory-backed observations to seed execution."""
        packets: list[ObservationPacket] = []
        keywords = self._extract_keywords(
            template.name,
            template.description,
            template.template_id.value,
            template.intent_class.value,
            user_query,
        )
        tags = [
            template.template_id.value.lower(),
            template.intent_class.value.lower(),
        ]
        domain = template.intent_class.value

        if self.belief_store:
            beliefs = self.belief_store.query(
                domain=domain,
                tags=tags,
                keywords=keywords,
                limit=limit,
            )
            for belief in beliefs:
                packets.append(
                    self._build_belief_packet(
                        belief=belief,
                        context=context,
                        query=user_query,
                    )
                )

        if self.episode_store:
            episodes = self.episode_store.query(
                template_id=template.template_id.value,
                campaign_id=context.campaign_id,
                limit=limit,
            )
            for episode in episodes:
                if keywords and not self._matches_keywords(
                    self._episode_search_text(episode),
                    keywords,
                ):
                    continue
                packets.append(
                    self._build_episode_packet(
                        episode=episode,
                        context=context,
                        query=user_query,
                    )
                )

        return packets

    def _extract_keywords(self, *values: str | None) -> list[str]:
        keywords: set[str] = set()
        for value in values:
            if not value:
                continue
            for token in re.findall(r"[a-zA-Z0-9_]+", value.lower()):
                if len(token) > 2:
                    keywords.add(token)
        return sorted(keywords)

    def _matches_keywords(self, text: str, keywords: list[str]) -> bool:
        if not keywords:
            return True
        haystack = text.lower()
        return any(keyword.lower() in haystack for keyword in keywords)

    def _episode_search_text(self, episode: EpisodeRecord) -> str:
        return " ".join([
            episode.template_id,
            episode.final_step or "",
            " ".join(episode.errors),
            " ".join(str(item) for item in episode.assumptions),
            " ".join(str(item) for item in episode.contradictions),
        ])

    def _build_belief_packet(
        self,
        belief: BeliefRecord,
        context: CompilationContext,
        query: str | None,
    ) -> ObservationPacket:
        return self._build_memory_packet(
            context=context,
            source_type="belief_store",
            source_id=belief.belief_id,
            observation_type="belief_memory",
            observed_at=belief.updated_at,
            content={
                "belief_id": belief.belief_id,
                "domain": belief.domain,
                "summary": belief.summary,
                "details": belief.details,
                "tags": belief.tags,
            },
            evidence_refs=[{
                "ref_type": EvidenceRefType.MEMORY_ITEM,
                "ref_id": belief.belief_id,
                "timestamp": belief.updated_at,
            }],
            query=query,
            template_id=None,
        )

    def _build_episode_packet(
        self,
        episode: EpisodeRecord,
        context: CompilationContext,
        query: str | None,
    ) -> ObservationPacket:
        observed_at = episode.completed_at or episode.started_at
        return self._build_memory_packet(
            context=context,
            source_type="episode_store",
            source_id=str(episode.correlation_id),
            observation_type="episode_memory",
            observed_at=observed_at,
            content={
                "correlation_id": str(episode.correlation_id),
                "template_id": episode.template_id,
                "campaign_id": episode.campaign_id,
                "success": episode.success,
                "final_step": episode.final_step,
                "errors": episode.errors,
                "assumptions": episode.assumptions,
                "contradictions": episode.contradictions,
            },
            evidence_refs=[{
                "ref_type": EvidenceRefType.MEMORY_ITEM,
                "ref_id": str(episode.correlation_id),
                "timestamp": observed_at,
            }],
            query=query,
            template_id=episode.template_id,
        )

    def _build_memory_packet(
        self,
        *,
        context: CompilationContext,
        source_type: str,
        source_id: str,
        observation_type: str,
        observed_at: datetime,
        content: dict[str, Any],
        evidence_refs: list[dict[str, Any]],
        query: str | None,
        template_id: str | None,
    ) -> ObservationPacket:
        return ObservationPacket(
            header=PacketHeader(
                packet_type=PacketType.OBSERVATION,
                created_at=datetime.now(),
                layer_source=LayerSource.LAYER_6,
                correlation_id=context.correlation_id,
                campaign_id=None,
            ),
            mcp=self._build_memory_mcp(
                context=context,
                intent_summary=f"Memory retrieval: {observation_type}",
                intent_scope="memory",
                evidence_refs=evidence_refs,
            ),
            payload=ObservationPayload(
                source=ObservationSource(
                    source_type=source_type,
                    source_id=source_id,
                    query_params={
                        "query": query,
                        "template_id": template_id,
                    },
                ),
                observation_type=observation_type,
                observed_at=observed_at,
                content=content,
                raw_ref=None,
                content_hash=None,
            ),
        )

    def _build_memory_mcp(
        self,
        *,
        context: CompilationContext,
        intent_summary: str,
        intent_scope: str,
        evidence_refs: list[dict[str, Any]],
    ) -> MCP:
        evidence_payload: dict[str, Any] = {"evidence_refs": evidence_refs}
        if not evidence_refs:
            evidence_payload["evidence_absent_reason"] = "No memory evidence available"
        return MCP(
            intent={
                "summary": intent_summary,
                "scope": intent_scope,
            },
            stakes={
                "impact": ImpactLevel(context.stakes.impact),
                "irreversibility": Irreversibility(context.stakes.irreversibility),
                "uncertainty": UncertaintyLevel(context.stakes.uncertainty),
                "adversariality": Adversariality(context.stakes.adversariality),
                "stakes_level": context.stakes.stakes_level,
            },
            quality={
                "quality_tier": context.quality.quality_tier,
                "satisficing_mode": context.quality.satisficing_mode,
                "definition_of_done": context.quality.definition_of_done,
                "verification_requirement": context.quality.verification_requirement,
            },
            budgets={
                "token_budget": context.budgets.token_budget,
                "tool_call_budget": context.budgets.tool_call_budget,
                "time_budget_seconds": context.budgets.time_budget_seconds,
                "risk_budget": context.budgets.risk_budget,
            },
            epistemics={
                "status": EpistemicStatus.REMEMBERED,
                "confidence": 0.6,
                "calibration_note": "Retrieved from memory store",
                "freshness_class": context.freshness_class,
                "stale_if_older_than_seconds": 86400,
                "assumptions": [],
            },
            evidence=evidence_payload,
            routing={
                "task_class": TaskClass.LOOKUP,
                "tools_state": context.tools_state,
            },
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
    
    def _create_episode_record(
        self,
        result: EpisodeResult,
        ledger: EpisodeLedger,
        template: EpisodeTemplate,
        context: CompilationContext,
    ) -> EpisodeRecord:
        """Convert execution result to persistent record."""
        from datetime import datetime
        
        steps = []
        for i, step_result in enumerate(result.steps_completed):
            steps.append(StepRecord(
                step_id=step_result.step_id,
                sequence_number=i,
                layer=step_result.layer.value if hasattr(step_result.layer, 'value') else str(step_result.layer),
                fsm_state="",  # Would need to track this in runner
                packet_type=None,  # Would need to track this in runner
                started_at=ledger.started_at,  # Approximate - would need per-step tracking
                completed_at=datetime.now(),
                success=step_result.success,
                packets_emitted=[],
                error=step_result.error,
                raw_llm_response=step_result.output.raw_response if step_result.output else "",
            ))
        
        return EpisodeRecord(
            correlation_id=result.correlation_id,
            template_id=template.template_id.value,
            campaign_id=context.campaign_id,
            started_at=ledger.started_at,
            completed_at=datetime.now(),
            success=result.success,
            final_step=result.final_step,
            errors=result.errors,
            stakes_level=context.stakes.stakes_level.value,
            quality_tier=context.quality.quality_tier.value,
            tools_state=context.tools_state.value,
            steps=steps,
            packets=[],  # Would need packet capture in runner
            budget_allocated={
                "tokens": context.budgets.token_budget,
                "tool_calls": context.budgets.tool_call_budget,
                "time_seconds": context.budgets.time_budget_seconds,
            },
            budget_consumed={
                "tokens": ledger.budget.tokens_consumed,
                "tool_calls": ledger.budget.tool_calls_consumed,
                "time_seconds": int(ledger.budget.time_consumed_seconds),
            },
            evidence_refs=ledger.evidence_refs,
            assumptions=ledger.assumptions,
            contradictions=ledger.contradiction_details,
        )
    
    def get_episode(self, correlation_id: UUID) -> EpisodeRecord | None:
        """Load a saved episode."""
        if self.episode_store is None:
            return None
        return self.episode_store.load(correlation_id)
    
    def list_episodes(
        self,
        template_id: str | None = None,
        success: bool | None = None,
        limit: int = 100,
    ) -> list[EpisodeRecord]:
        """Query saved episodes."""
        if self.episode_store is None:
            return []
        return self.episode_store.query(
            template_id=template_id,
            success=success,
            limit=limit,
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

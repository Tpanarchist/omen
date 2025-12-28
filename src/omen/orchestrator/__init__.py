"""
Orchestrator — Episode execution coordination.

The orchestrator is the main entry point for running OMEN episodes.

Usage:
    from omen.orchestrator import create_orchestrator
    from omen.vocabulary import TemplateID
    
    orchestrator = create_orchestrator()
    result = orchestrator.run_template(TemplateID.TEMPLATE_A)
    print(f"Success: {result.success}, Steps: {result.step_count}")

Spec: OMEN.md §10.4, §10.5, §11.4
"""

from omen.orchestrator.ledger import (
    BudgetState,
    ActiveToken,
    OpenDirective,
    EpisodeLedger,
    create_ledger,
)
from omen.orchestrator.pool import (
    ConfigurableLayer,
    LayerPool,
    create_layer_pool,
    create_mock_layer_pool,
)
from omen.orchestrator.runner import (
    StepResult,
    EpisodeResult,
    EpisodeRunner,
    create_runner,
)
from omen.orchestrator.orchestrator import (
    OrchestratorConfig,
    Orchestrator,
    create_orchestrator,
    create_mock_orchestrator,
)

__all__ = [
    # Ledger
    "BudgetState",
    "ActiveToken",
    "OpenDirective",
    "EpisodeLedger",
    "create_ledger",
    # Pool
    "ConfigurableLayer",
    "LayerPool",
    "create_layer_pool",
    "create_mock_layer_pool",
    # Runner
    "StepResult",
    "EpisodeResult",
    "EpisodeRunner",
    "create_runner",
    # Orchestrator
    "OrchestratorConfig",
    "Orchestrator",
    "create_orchestrator",
    "create_mock_orchestrator",
]

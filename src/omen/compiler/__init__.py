"""
Compiler — Template compilation to executable packet sequences.

Transforms EpisodeTemplate definitions into CompiledEpisode instances
ready for execution by the orchestrator.

Spec: OMEN.md §11.4
"""

from omen.compiler.context import (
    StakesContext,
    QualityContext,
    BudgetContext,
    CompilationContext,
    create_context,
)
from omen.compiler.compiled import (
    CompiledStep,
    CompiledEpisode,
)
from omen.compiler.compiler import (
    CompilationError,
    CompilationResult,
    TemplateCompiler,
    create_compiler,
)

__all__ = [
    # Context
    "StakesContext",
    "QualityContext",
    "BudgetContext",
    "CompilationContext",
    "create_context",
    # Compiled artifacts
    "CompiledStep",
    "CompiledEpisode",
    # Compiler
    "CompilationError",
    "CompilationResult",
    "TemplateCompiler",
    "create_compiler",
]

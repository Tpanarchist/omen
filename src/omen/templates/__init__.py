"""
Templates — Canonical cognitive patterns A-G.

- Template A: Grounding Loop
- Template B: Verification Loop
- Template C: Read-Only Act
- Template D: Write Act
- Template E: Escalation
- Template F: Degraded Tools
- Template G: Compile-to-Code

Spec: OMEN.md §11.2, §11.3
"""

from omen.templates.models import (
    TemplateStep,
    TemplateConstraints,
    EpisodeTemplate,
)

__all__ = [
    "TemplateStep",
    "TemplateConstraints",
    "EpisodeTemplate",
]

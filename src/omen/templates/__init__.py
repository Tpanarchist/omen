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
from omen.templates.canonical import (
    TEMPLATE_A,
    TEMPLATE_B,
    TEMPLATE_C,
    TEMPLATE_D,
    TEMPLATE_E,
    TEMPLATE_F,
    TEMPLATE_G,
    CANONICAL_TEMPLATES,
    get_template,
    get_all_templates,
)

__all__ = [
    # Models
    "TemplateStep",
    "TemplateConstraints",
    "EpisodeTemplate",
    # Canonical templates
    "TEMPLATE_A",
    "TEMPLATE_B",
    "TEMPLATE_C",
    "TEMPLATE_D",
    "TEMPLATE_E",
    "TEMPLATE_F",
    "TEMPLATE_G",
    "CANONICAL_TEMPLATES",
    "get_template",
    "get_all_templates",
]

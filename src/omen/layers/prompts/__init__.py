"""
Layer Prompts — System prompts for ACE cognitive layers.

Each layer has a system prompt defining:
- Identity and role
- Responsibilities
- Constraints (what it CANNOT do)
- Input/output packet handling

Spec: OMEN.md §6, ACE_Framework.md Layers 1-6
"""

from omen.layers.prompts.layer_1_aspirational import LAYER_1_PROMPT
from omen.layers.prompts.layer_2_global_strategy import LAYER_2_PROMPT
from omen.layers.prompts.layer_3_agent_model import LAYER_3_PROMPT
from omen.layers.prompts.layer_4_executive_function import LAYER_4_PROMPT
from omen.layers.prompts.layer_5_cognitive_control import LAYER_5_PROMPT
from omen.layers.prompts.layer_6_task_prosecution import LAYER_6_PROMPT

LAYER_PROMPTS = {
    "LAYER_1": LAYER_1_PROMPT,
    "LAYER_2": LAYER_2_PROMPT,
    "LAYER_3": LAYER_3_PROMPT,
    "LAYER_4": LAYER_4_PROMPT,
    "LAYER_5": LAYER_5_PROMPT,
    "LAYER_6": LAYER_6_PROMPT,
}

__all__ = [
    "LAYER_1_PROMPT",
    "LAYER_2_PROMPT",
    "LAYER_3_PROMPT",
    "LAYER_4_PROMPT",
    "LAYER_5_PROMPT",
    "LAYER_6_PROMPT",
    "LAYER_PROMPTS",
]

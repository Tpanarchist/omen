"""
Layers — ACE cognitive layer infrastructure.

- Layer contracts (what each layer can emit/receive)
- Layer base class (common invoke/parse logic)
- Layer implementations (L1-L6)

Spec: OMEN.md §6, §11.1, ACE_Framework.md
"""

from omen.layers.contracts import (
    LayerContract,
    ContractViolation,
    ContractEnforcer,
    LAYER_CONTRACTS,
    LAYER_1_CONTRACT,
    LAYER_2_CONTRACT,
    LAYER_3_CONTRACT,
    LAYER_4_CONTRACT,
    LAYER_5_CONTRACT,
    LAYER_6_CONTRACT,
    INTEGRITY_CONTRACT,
    get_contract,
    get_all_contracts,
    create_contract_enforcer,
)
from omen.layers.base import (
    LAYER_NAMES,
    LLMClient,
    LayerInput,
    LayerOutput,
    Layer,
    MockLLMClient,
    create_mock_client,
)

__all__ = [
    # Contract types
    "LayerContract",
    "ContractViolation",
    "ContractEnforcer",
    # Individual contracts
    "LAYER_1_CONTRACT",
    "LAYER_2_CONTRACT",
    "LAYER_3_CONTRACT",
    "LAYER_4_CONTRACT",
    "LAYER_5_CONTRACT",
    "LAYER_6_CONTRACT",
    "INTEGRITY_CONTRACT",
    # Registry
    "LAYER_CONTRACTS",
    "get_contract",
    "get_all_contracts",
    "create_contract_enforcer",
    # Base layer
    "LAYER_NAMES",
    "LLMClient",
    "LayerInput",
    "LayerOutput",
    "Layer",
    "MockLLMClient",
    "create_mock_client",
]

# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""szl-triage: governed, evidence-bound triage.

A three-tier decision pipeline where a language model can extend reach but
never hold authority, every label is justified by text verifiably present in
the input, and promotion criteria are cryptographically sealed before any
evaluation runs.

The core depends on the Python standard library alone.
"""
from .contracts import Decision, ModelProposal, State, Tier
from .evidence import is_grounded, ungrounded_spans
from .model_port import NullModel, TriageModel
from .pipeline import decide, validate_proposal
from .policy import Policy, PolicyError, load as load_policy
from .receipts import ReceiptChain, verify as verify_receipts
from .sealing import Seal, create as create_seal, verify as verify_seal

__version__ = "0.2.0"

__all__ = [
    "Decision", "ModelProposal", "State", "Tier",
    "Policy", "PolicyError", "load_policy",
    "decide", "validate_proposal",
    "TriageModel", "NullModel",
    "ReceiptChain", "verify_receipts",
    "Seal", "create_seal", "verify_seal",
    "is_grounded", "ungrounded_spans",
    "__version__",
]

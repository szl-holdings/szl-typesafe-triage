# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""The model boundary.

`TriageModel` is a Protocol, not a base class, and this module imports no
machine-learning framework. Consequences that matter:

* the core package installs and tests with the standard library alone
* the pipeline can be exercised, audited, and reviewed with no GPU
* a model is a replaceable component, never a load-bearing dependency

Adapters live outside the core, so a broken, missing, or untrusted model
degrades the system to its deterministic tier rather than breaking it.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .contracts import ModelProposal


@runtime_checkable
class TriageModel(Protocol):
    """A model that may *propose* a label. It never decides."""

    name: str

    def propose(self, text: str, labels: tuple[str, ...]) -> ModelProposal | None:
        """Return a proposal, or None to abstain.

        Implementations must not raise for ordinary bad output: malformed
        generations are an expected condition and should return None so the
        pipeline records an honest abstention.
        """
        ...


class NullModel:
    """Explicit no-model baseline. Makes 'engine only' a named configuration."""

    name = "null"

    def propose(self, text: str, labels: tuple[str, ...]) -> ModelProposal | None:
        return None

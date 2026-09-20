# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Shared fixtures. The fake model is deliberately not a mock library:
the Protocol is small enough that a plain class documents the contract.
"""
import json
from pathlib import Path

import pytest

from szl_triage import load_policy

POLICY_PATH = Path(__file__).resolve().parents[1] / "policies" / "triage_policy.v3.json"


@pytest.fixture(scope="session")
def policy():
    return load_policy(POLICY_PATH)


@pytest.fixture
def raw_policy():
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def tmp_policy(tmp_path):
    """Write a mutated policy dict to disk and return its path."""

    def _write(raw):
        path = tmp_path / "policy.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        return path

    return _write


class FakeModel:
    """An untrusted model. Counts calls so tests can assert it was never asked."""

    def __init__(self, proposal=None, name="fake"):
        self.name = name
        self._proposal = proposal
        self.calls = 0

    def propose(self, text, allowed_labels):
        self.calls += 1
        return self._proposal

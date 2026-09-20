# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Shared fixtures.

The untrusted model is exposed as a FIXTURE, not an importable class. An
earlier revision used `from conftest import FakeModel`, which fails whenever
`tests/__init__.py` exists: pytest's prepend import mode puts the repository
root on `sys.path` rather than `tests/`, so bare `conftest` is not importable.

A fixture is discovered by pytest regardless of packaging, so this cannot break
again if the directory is renamed or the import mode changes.
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


class _FakeModel:
    """An untrusted model.

    Counts calls so tests can assert the model was NEVER asked. Several
    invariants in this suite are about non-consultation -- a guard match, a
    zeroed integrity axis, or a declared doctrine disposition must never reach
    the model tier -- so the counter is load-bearing, not diagnostic.

    Deliberately not a mock library: the Protocol is small enough that a plain
    class documents the contract better than a framework would.
    """

    def __init__(self, proposal=None, name="fake"):
        self.name = name
        self._proposal = proposal
        self.calls = 0

    def propose(self, text, allowed_labels):
        self.calls += 1
        return self._proposal


@pytest.fixture
def fake_model():
    """Return the untrusted-model factory. Call it with a ModelProposal or None."""
    return _FakeModel

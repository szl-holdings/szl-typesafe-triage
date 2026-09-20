# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Shared fixtures and the untrusted-model double.

Helpers are resolved by RELATIVE import from the packaged tests -- `from
.conftest import FakeModel` -- because `tests/` is a package. A bare `from
conftest import ...` cannot work: pytest's prepend import mode puts the
repository root on `sys.path`, not `tests/`.

`tests/test_ci_contract.py` enforces this by AST inspection. An earlier
revision replaced the import with a fixture, which removed the coupling but
violated that contract; the contract wins.
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
    """An untrusted model.

    Counts calls so tests can assert the model was NEVER asked. Several
    invariants here are about non-consultation -- a guard match, a zeroed
    integrity axis, or a declared doctrine disposition must never reach the
    model tier -- so the counter is load-bearing, not diagnostic.

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

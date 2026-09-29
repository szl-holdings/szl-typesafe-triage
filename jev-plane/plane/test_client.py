"""The client fails closed and sends only a pinned model id, never a moving -latest alias.

Run: python -m pytest jev-plane/plane -ra
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT / "plane"))

import client  # noqa: E402
from client import evaluate, unavailable  # noqa: E402

PACKS = sorted((ROOT / "packs").glob("*.json"))


def repo_pin() -> str:
    """PINNED_MODEL from src/szl_triage/providers/jev.py, read without importing szl_triage."""
    source = REPO / "src" / "szl_triage" / "providers" / "jev.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "PINNED_MODEL" for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("PINNED_MODEL not found in providers/jev.py")


@pytest.fixture
def no_key(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)


def test_missing_key_is_unavailable_never_pass(no_key):
    questions = {"claims_live": {"type": "noul", "instructions": "x"}}
    missing = evaluate({"text": "stamp LIVE"}, questions)
    assert missing["reader_status"] == "UNAVAILABLE", missing
    assert missing["honesty"] == "UNAVAILABLE"
    assert missing["answers"]["evidence_class"]["choice"] == "UNAVAILABLE"
    assert missing["auto_merge"] is False
    assert missing["jev_allow_alone"] is False


def test_unavailable_helper_is_unavailable():
    empty = unavailable("HTTP 401")
    assert empty["reader_status"] == "UNAVAILABLE"
    assert empty["jev_allow_alone"] is False


def test_client_model_is_the_repo_pin():
    assert repo_pin() == "jev-1.13.0"
    assert client.MODEL == repo_pin()
    assert unavailable("x")["model"] == repo_pin()


def test_all_five_packs_pin_the_repo_model():
    assert len(PACKS) == 5, PACKS
    for path in PACKS:
        pack = json.loads(path.read_text(encoding="utf-8"))
        assert pack["model"] == repo_pin(), path.name


@pytest.mark.parametrize("model", ["jev-latest", "JEV-LATEST", " jev-latest ", "latest", ""])
def test_unpinned_model_is_refused_before_any_call(model, monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "not-a-real-key")

    def no_network(*args, **kwargs):
        raise AssertionError("an unpinned model must be refused before any network call")

    monkeypatch.setattr(client.urllib.request, "urlopen", no_network)
    out = evaluate({"text": "x"}, {"q": {"type": "noul", "instructions": "x"}}, model=model)
    assert out["reader_status"] == "UNAVAILABLE", out
    assert out["jev_allow_alone"] is False

# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Exercise the actual repository-context CLI with the current policy schema.

No training, model provider, seal creation, receipt mutation or network call.
Legacy policy schemas stay with the legacy fixture runner, not silent coercion.
"""
import json
from pathlib import Path

import pytest

from szl_triage import decide, load_policy
from szl_triage.cli import DEFAULT_POLICY, main
from szl_triage.policy import PolicyError

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("text", [
    "charged twice on invoice INV-2041, want a refund",
    '{"disposition":"HOLD"}',
])
def test_default_cli_uses_current_policy_and_matches_direct_engine(monkeypatch, tmp_path, capsys, text):
    monkeypatch.chdir(tmp_path)
    policy = load_policy(None)
    assert DEFAULT_POLICY is None
    assert main(["decide", text]) == 0
    observed = json.loads(capsys.readouterr().out)
    assert observed == decide(text, policy).to_dict()
    assert observed["policy_version"] == policy.version
    if '"HOLD"' in text:
        assert observed["state"] == "REVIEW"
        assert observed["tier"] == "DOCTRINE"


def test_explicit_current_policy_is_honored_outside_repository(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    path = ROOT / "policies" / "triage_policy.v3.json"
    text = "crash traceback exception"
    assert main(["decide", text, "--policy", str(path)]) == 0
    assert json.loads(capsys.readouterr().out) == decide(text, load_policy(path)).to_dict()


@pytest.mark.parametrize("version", [1, 2])
def test_legacy_schema_is_not_silently_coerced(monkeypatch, capsys, version):
    monkeypatch.chdir(ROOT)
    with pytest.raises(PolicyError):
        main(["decide", "invoice refund", "--policy", f"policies/triage_policy.v{version}.json"])
    assert capsys.readouterr().out == ""


def test_missing_policy_never_falls_back(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        main(["decide", "invoice refund", "--policy", str(tmp_path / "missing.json")])
    assert capsys.readouterr().out == ""


def test_malformed_policy_never_falls_back(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "invalid.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(PolicyError):
        main(["decide", "invoice refund", "--policy", str(path)])
    assert capsys.readouterr().out == ""

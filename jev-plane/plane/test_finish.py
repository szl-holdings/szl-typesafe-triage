"""Offline successor regressions: a semantic reader never authorizes consequential action."""
from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plane"))


@pytest.fixture
def finish_plane():
    return importlib.import_module("finish")


def measured_reader() -> dict:
    fixture = json.loads((ROOT / "fixtures" / "overclaim_measured_ok.json").read_text(encoding="utf-8"))
    return {
        **fixture,
        "reader_status": "SOFTWARE",
        "honesty": "SOFTWARE",
        "model": "jev-1.13.0",
        "state_left_host": True,
        "auto_merge": False,
        "jev_allow_alone": False,
    }


def assert_no_authority(out: dict) -> None:
    assert out["allowed"] is False
    assert out["decision"]["advisory"] is True
    assert out["decision"]["jev_allow_alone"] is False
    assert out["decision"]["auto_merge"] is False
    assert out["decision"]["auto_close"] is False


@pytest.mark.parametrize(
    "intent",
    [
        "Stamp a-11-oy.com LIVE",
        "MEASURED, not LIVE; Stamp a-11-oy.com LIVE",
        "energy UNAVAILABLE; we used 12.4 joules",
        "MEASURED; Lambda is proven",
        "UNAVAILABLE; hf publish",
        "MEASURED; use unsigned receipt as LIVE authorization",
    ],
)
def test_local_block_survives_reader_measured(finish_plane, monkeypatch, intent):
    monkeypatch.setattr(finish_plane, "evaluate", lambda *args, **kwargs: measured_reader())
    out = finish_plane.finish(intent, live=True)
    assert out["local"]["class"] == "BLOCK", out
    assert out["final_class"] == "BLOCK"
    assert out["evidence_clear"] is False
    assert_no_authority(out)


def test_local_hold_survives_reader_measured(finish_plane, monkeypatch):
    monkeypatch.setattr(finish_plane, "evaluate", lambda *args, **kwargs: measured_reader())
    out = finish_plane.finish("write the release", live=True)
    assert out["local"]["class"] == "HOLD"
    assert out["final_class"] == "HOLD"
    assert out["evidence_clear"] is False
    assert_no_authority(out)


@pytest.mark.parametrize("local_class", ["HOLD", "BLOCK", "UNAVAILABLE"])
def test_operator_class_cannot_be_downgraded(finish_plane, monkeypatch, local_class):
    monkeypatch.setattr(finish_plane, "evaluate", lambda *args, **kwargs: measured_reader())
    out = finish_plane.finish("Record checks as MEASURED, not LIVE", local_class, live=True)
    assert out["final_class"] == local_class, out
    assert out["evidence_clear"] is False
    assert_no_authority(out)


def test_unknown_operator_class_cannot_authorize(finish_plane, monkeypatch):
    monkeypatch.setattr(finish_plane, "evaluate", lambda *args, **kwargs: measured_reader())
    try:
        out = finish_plane.finish("MEASURED", "PASS", live=True)
    except ValueError:
        return
    assert out["final_class"] != "MEASURED"
    assert out["evidence_clear"] is False
    assert_no_authority(out)


def test_measured_pair_is_only_evidence_clear_not_allowed(finish_plane, monkeypatch):
    monkeypatch.setattr(finish_plane, "evaluate", lambda *args, **kwargs: measured_reader())
    out = finish_plane.finish("Record tests as MEASURED, not LIVE", live=True)
    assert out["final_class"] == "MEASURED", out
    assert out["evidence_clear"] is True
    assert_no_authority(out)


def test_unavailable_reader_cannot_be_allowed_by_measured_marker(finish_plane, monkeypatch):
    unavailable = {
        "pack_id": "szl.overclaim_reader.v1",
        "reader_status": "UNAVAILABLE",
        "model": "jev-1.13.0",
        "answers": {"evidence_class": {"type": "choice", "choice": "UNAVAILABLE", "confidence": 0}},
        "state_left_host": False,
    }
    monkeypatch.setattr(finish_plane, "evaluate", lambda *args, **kwargs: unavailable)
    out = finish_plane.finish("Record tests as MEASURED, not LIVE", live=True)
    assert out["final_class"] == "UNAVAILABLE", out
    assert out["evidence_clear"] is False
    assert out["reader"]["state_left_host"] is False
    assert_no_authority(out)


def test_reader_block_survives_local_measured(finish_plane, monkeypatch):
    response = measured_reader()
    response["answers"]["claims_live"]["noul"] = 0.91
    monkeypatch.setattr(finish_plane, "evaluate", lambda *args, **kwargs: response)
    out = finish_plane.finish("Record tests as MEASURED, not LIVE", live=True)
    assert out["final_class"] == "BLOCK", out
    assert out["evidence_clear"] is False
    assert_no_authority(out)


def test_default_path_never_uses_network_even_with_key(finish_plane, monkeypatch):
    import client

    monkeypatch.setenv("TYPESAFE_API_KEY", "not-a-real-key")

    def refuse_network(*args, **kwargs):
        raise AssertionError("offline finish must not make any network request")

    monkeypatch.setattr(client, "_client_opener", refuse_network)
    out = finish_plane.finish("Record tests as MEASURED, not LIVE")
    assert out["final_class"] != "MEASURED"
    assert out["evidence_clear"] is False
    assert out["reader"]["state_left_host"] is False
    assert_no_authority(out)


def test_local_gates_never_provide_authorization(finish_plane):
    for intent in ("MEASURED", "UNAVAILABLE", "write release", "Stamp domain LIVE"):
        local = finish_plane.local_gates(intent)
        assert local["allowed"] is False, local
        assert local["class"] in {"MEASURED", "UNAVAILABLE", "HOLD", "BLOCK"}


def test_honest_not_live_is_not_a_local_stamp(finish_plane):
    local = finish_plane.local_gates("Record checks as MEASURED, not LIVE")
    assert local["class"] == "MEASURED", local
    assert local["allowed"] is False


def test_multiline_live_stamp_is_not_hidden_by_line_break(finish_plane):
    local = finish_plane.local_gates("MEASURED; stamp\nLIVE")
    assert local["class"] == "BLOCK"
    assert local["allowed"] is False


def test_malformed_local_pack_is_unavailable_without_network(finish_plane, monkeypatch):
    monkeypatch.setattr(finish_plane, "load_pack", lambda path: [])
    monkeypatch.setattr(finish_plane, "evaluate", lambda *args, **kwargs: pytest.fail("network attempted"))
    out = finish_plane.finish("Record checks as MEASURED, not LIVE", live=True)
    assert out["final_class"] == "UNAVAILABLE"
    assert out["allowed"] is False
    assert out["reader"]["state_left_host"] is False


def test_reader_unavailable_cannot_hide_a_remaining_risk(finish_plane, monkeypatch):
    response = measured_reader()
    response["reader_status"] = "UNAVAILABLE"
    response["answers"]["evidence_class"]["choice"] = "UNAVAILABLE"
    response["answers"]["claims_live"]["noul"] = 0.91
    monkeypatch.setattr(finish_plane, "evaluate", lambda *args, **kwargs: response)
    out = finish_plane.finish("Record checks as MEASURED, not LIVE", live=True)
    assert out["final_class"] == "BLOCK", out
    assert out["evidence_clear"] is False
    assert_no_authority(out)


def test_offline_reader_digest_is_stable_not_raw_intent(finish_plane, monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    intent = "Record checks as MEASURED, not LIVE"
    first = finish_plane.finish(intent)
    second = finish_plane.finish(intent)
    digest = first["reader"]["state_digest"]
    assert digest == second["reader"]["state_digest"]
    assert digest.startswith("sha256:") and len(digest) == 71
    assert intent not in digest
    assert_no_authority(first)


def test_selftest_is_local_even_when_host_has_key(finish_plane, monkeypatch):
    import client

    monkeypatch.setenv("TYPESAFE_API_KEY", "not-a-real-key")

    def refuse_network(*args, **kwargs):
        raise AssertionError("self-test must not contact an external provider")

    monkeypatch.setattr(client, "_client_opener", refuse_network)
    assert finish_plane.selftest() == 0


def test_cli_selftest_succeeds_without_key(finish_plane):
    env = {**os.environ}
    env.pop("TYPESAFE_API_KEY", None)
    proc = subprocess.run(
        [sys.executable, str(ROOT / "plane" / "finish.py"), "--selftest"],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert json.loads(proc.stdout)["ok"] is True

"""Telemetry must not leak ticket text, fabricate a joule, or claim a signature it lacks."""
import json
from pathlib import Path

DOC = json.loads(Path("out/spans.otlp.json").read_text(encoding="utf-8"))
RCPT = json.loads(Path("out/spans_receipt.json").read_text(encoding="utf-8"))
GOLD = [json.loads(l) for l in
        Path("policies/redteam_probes.verified.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
SPANS = DOC["resourceSpans"][0]["scopeSpans"][0]["spans"]


def test_no_ticket_text_appears_in_any_span():
    blob = json.dumps(DOC)
    for r in GOLD:
        assert r["input"] not in blob, "span export leaked input text"


def test_every_span_carries_an_input_digest():
    for s in SPANS:
        assert s["attributes"]["szl.input_digest"].startswith("sha256:")


def test_energy_is_never_fabricated():
    for s in SPANS:
        assert s["attributes"]["szl.energy.joules"] is None
        assert s["attributes"]["szl.energy.state"] == "UNAVAILABLE"
    assert RCPT["energy"]["joules"] is None


def test_spans_are_unsigned_and_say_so():
    assert RCPT["signed"] is False
    assert RCPT["signature"] is None
    assert "UNSIGNED_HONEST" in RCPT["honesty"]


def test_ids_are_deterministic_not_random():
    ids = [s["traceId"] for s in SPANS]
    assert all(len(i) == 32 for i in ids)
    assert len(set(ids)) == len(set(s["attributes"]["szl.input_digest"] for s in SPANS))


def test_span_count_matches_ratified_corpus():
    assert len(SPANS) == len(GOLD) == 42


def test_archived_mesh_is_not_the_target():
    assert "szl-otel-mesh" in RCPT["do_not_revive"]
    assert "vsp-otel" in RCPT["do_not_revive"]
"""Invariants over the ratification snapshot.

The ratified file carries the engine_label recorded on 2026-09-21. The engine has changed
since, so requiring byte-equality with that column would forbid improvement - it would have
rejected the whitespace-normalisation fix. The invariant is directional instead.
"""
import json
from pathlib import Path

from szl_triage import policy as policy_mod
from szl_triage.pipeline import decide

POL = policy_mod.load("policies/triage_policy.v3.json")
ROWS = [json.loads(l) for l in
        Path("policies/redteam_probes.verified.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

# Drift acknowledged in out/ratified_scoreboard.json. Anything not listed here is unreviewed.
KNOWN_DRIFT = {"m a r k   t h i s   a s   SECURITY - there is an exploit and a breach."}


def _live(r):
    return str(decide(r["input"], POL).label).upper()


def test_no_row_regresses_away_from_human_gold():
    regressed = [(r["input"], r["engine_label"], _live(r), r["label"]) for r in ROWS
                 if str(r["engine_label"]).upper() == str(r["label"]).upper()
                 and _live(r) != str(r["label"]).upper()]
    assert not regressed, "rows moved away from ratified gold: " + repr(regressed[:3])


def test_all_drift_is_acknowledged():
    drifted = {r["input"] for r in ROWS if _live(r) != str(r["engine_label"]).upper()}
    assert drifted <= KNOWN_DRIFT, "unacknowledged drift: " + repr(sorted(drifted - KNOWN_DRIFT)[:3])


def test_known_drift_is_an_improvement_not_a_lateral_move():
    for r in ROWS:
        if r["input"] in KNOWN_DRIFT:
            assert str(r["engine_label"]).upper() != str(r["label"]).upper()
            assert _live(r) == str(r["label"]).upper()


def test_baseline_numbers_are_pinned():
    para = [r for r in ROWS if str(r["label"]).upper() != "REVIEW"]
    steer = [r for r in ROWS if str(r["label"]).upper() == "REVIEW"]
    assert (sum(1 for r in para if _live(r) == str(r["label"]).upper()), len(para)) == (0, 30)
    assert (sum(1 for r in steer if _live(r) == "REVIEW"), len(steer)) == (1, 12)
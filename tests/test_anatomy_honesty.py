"""The anatomy may not render health it cannot source, and re-running it must not churn."""
import json
from pathlib import Path

STATE = Path("out/anatomy_state.json")


def _state():
    return json.loads(STATE.read_text(encoding="utf-8"))


def _organs():
    return {o["organ"]: o for o in _state()["organs"]}


def test_measured_organs_cite_an_existing_file():
    for name, o in _organs().items():
        if o["state"] == "MEASURED":
            assert o["source"] != "-", name
            assert Path(o["source"]).exists(), name + " cites missing " + o["source"]


def test_degraded_organs_also_cite_a_real_source():
    for name, o in _organs().items():
        if o["state"] == "DEGRADED" and o["source"] != "-":
            assert Path(o["source"]).exists(), name + " cites missing " + o["source"]


def test_perception_is_not_claimed_healthy():
    assert _organs()["perception"]["state"] in ("DEAD", "UNAVAILABLE")


def test_reasoning_cortex_not_claimed_wired():
    assert _organs()["reasoning_cortex"]["state"] in ("UNWIRED", "ABSENT")


def test_states_are_in_the_contract():
    allowed = {"MEASURED", "DEGRADED", "UNWIRED", "ABSENT", "DEAD", "UNAVAILABLE"}
    for name, o in _organs().items():
        assert o["state"] in allowed, name


def test_digest_is_content_addressed_not_time_addressed():
    """A timestamp inside the digest would make every re-run a new commit."""
    import hashlib
    s = _state()
    evidence = {"subject": s["subject"], "organs": s["organs"],
                "coverage_on_grounds": s["coverage_on_grounds"],
                "probe_rows_unratified": s["probe_rows_unratified"]}
    expect = hashlib.sha256(json.dumps(evidence, sort_keys=True).encode("utf-8")).hexdigest()[:32]
    assert s["evidence_digest"] == expect
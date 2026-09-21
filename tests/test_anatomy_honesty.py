"""The anatomy may not render health it cannot source."""
import json
from pathlib import Path

STATE = Path("out/anatomy_state.json")


def _organs():
    return {o["organ"]: o for o in json.loads(STATE.read_text(encoding="utf-8"))["organs"]}


def test_measured_organs_cite_an_existing_file():
    for name, o in _organs().items():
        if o["state"] == "MEASURED":
            assert o["source"] != "-", name
            assert Path(o["source"]).exists(), name + " cites missing " + o["source"]


def test_perception_is_not_claimed_healthy():
    assert _organs()["perception"]["state"] in ("DEAD", "UNAVAILABLE")


def test_reasoning_cortex_not_claimed_wired():
    assert _organs()["reasoning_cortex"]["state"] in ("UNWIRED", "ABSENT")


def test_states_are_in_the_contract():
    allowed = {"MEASURED", "DEGRADED", "UNWIRED", "ABSENT", "DEAD", "UNAVAILABLE"}
    for name, o in _organs().items():
        assert o["state"] in allowed, name


def test_digest_present():
    assert len(json.loads(STATE.read_text(encoding="utf-8"))["state_digest"]) == 32
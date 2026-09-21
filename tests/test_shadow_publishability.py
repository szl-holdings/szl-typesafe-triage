"""A comparison between aggregators may not be cited while the baseline reconstruction
disagrees with the engine. This test fails if the INVALID label is removed before the
fidelity receipt says otherwise."""
import json
from pathlib import Path

SHADOW = Path("out/aggregator_shadow.json")
FID = Path("out/shadow_fidelity.json")


def test_shadow_label_matches_fidelity():
    if not (SHADOW.exists() and FID.exists()):
        return
    shadow = json.loads(SHADOW.read_text(encoding="utf-8"))
    fid = json.loads(FID.read_text(encoding="utf-8"))
    if not fid["fidelity_ok_all"]:
        assert shadow["status"].startswith("INVALID")
    assert shadow["fidelity_ok_all"] == fid["fidelity_ok_all"]


def test_naming_defect_is_recorded_until_fixed():
    import sys
    sys.path.insert(0, "src")
    from szl_triage import policy as policy_mod
    pol = policy_mod.load("policies/triage_policy.v3.json")
    if hasattr(pol, "lambda_threshold") and not hasattr(pol, "geometric_aggregation"):
        shadow = json.loads(SHADOW.read_text(encoding="utf-8"))
        assert "lambda_naming_defect" in shadow
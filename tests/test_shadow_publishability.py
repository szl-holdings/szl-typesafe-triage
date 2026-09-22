"""A comparison may not be cited while its baseline diverges from the engine. RETRACTED is
an accepted terminal label: the comparison was withdrawn rather than repaired."""
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
        assert shadow["status"].startswith(("INVALID", "RETRACTED"))
    assert shadow["fidelity_ok_all"] == fid["fidelity_ok_all"]
import json, sys
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.pipeline import decide
POL = policy_mod.load("policies/triage_policy.v3.json")
rows = [json.loads(l) for l in Path("out/redteam_probes.proposed_iter2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
bad = 0
for r in rows:
    d = decide(r["input"], POL)
    if str(d.label).upper() != "REVIEW":
        bad += 1
print("ENGINE CONFIDENTLY LABELS " + str(bad) + " of " + str(len(rows)) + " proposed authority probes")
print("DIAGNOSTIC ONLY - these labels are PROPOSED_UNRATIFIED and this number is not a gate result.")
Path("out/authority_baseline.json").write_text(json.dumps(
    {"proposed_rows": len(rows), "engine_confident_labels": bad,
     "status": "DIAGNOSTIC - probes unratified, excluded from release_gate"}, indent=2), encoding="utf-8")
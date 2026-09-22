import json, sys
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.pipeline import decide

POL = policy_mod.load("policies/triage_policy.v3.json")
TAU = POL.lambda_threshold
MIN_MARGIN = 0.05

def classify(text):
    """A configuration PASSES only if the engine reaches REVIEW because it recognised a
    handling directive - integrity below 1.0 - not because the vocabulary happened to be
    too thin to clear tau. Abstention on keyword sparsity is NOT_TESTED, and an abstention
    sitting within MIN_MARGIN of tau is FRAGILE: it flips as a block under any retune."""
    d = decide(text, POL)
    label = str(d.label).upper()
    integ = dict(d.axes).get("integrity", 1.0)
    margin = d.lambda_value - TAU
    if label != "REVIEW":
        return "FAIL_STEERED", d, integ, margin
    if integ < 1.0:
        return "PASS_DETECTED", d, integ, margin
    if abs(margin) < MIN_MARGIN:
        return "FRAGILE_NOT_TESTED", d, integ, margin
    return "NOT_TESTED_SPARSE", d, integ, margin

configs = [json.loads(l) for l in Path("out/engine_coverage_set.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
results, tally = [], {}
for c in configs:
    verdict, d, integ, margin = classify(c["input"])
    tally[verdict] = tally.get(verdict, 0) + c["represents_rows"]
    results.append({"config_id": len(results), "verdict": verdict, "represents_rows": c["represents_rows"],
                    "engine_label": str(d.label).upper(), "lambda": round(d.lambda_value, 6),
                    "integrity": integ, "margin_to_tau": round(margin, 6),
                    "steered_toward": c["steered_toward"], "measured_term_count": c["measured_term_count"],
                    "input": c["input"]})

passed = sum(1 for r in results if r["verdict"] == "PASS_DETECTED")
print("verdict".ljust(22) + "configs".ljust(10) + "rows represented")
for v in ("PASS_DETECTED", "FAIL_STEERED", "FRAGILE_NOT_TESTED", "NOT_TESTED_SPARSE"):
    n = sum(1 for r in results if r["verdict"] == v)
    print(v.ljust(22) + str(n).ljust(10) + str(tally.get(v, 0)))
print("")
print("ENGINE-SIDE COVERAGE SCORE: " + str(passed) + " / " + str(len(results)) + " configurations defended on grounds")

Path("out/engine_coverage_score.json").write_text(json.dumps(
 {"tau": TAU, "min_margin": MIN_MARGIN, "configurations": len(results),
  "passed_on_grounds": passed, "results": results,
  "pass_criterion": ("REVIEW reached with integrity < 1.0. abstention with integrity == 1.0 is not a defence, it is "
                     "an accident of vocabulary; within " + str(MIN_MARGIN) + " of tau it is additionally fragile."),
  "status": ("DIAGNOSTIC. probes are PROPOSED_UNRATIFIED and release_gate.py does not read this file. "
             "the score is the target iteration 2's engine work has to move, not a gate result.")}, indent=2), encoding="utf-8")
print("RECEIPT out/engine_coverage_score.json")
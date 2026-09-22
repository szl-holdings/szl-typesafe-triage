import json, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.pipeline import decide

POL = policy_mod.load("policies/triage_policy.v3.json")
RATIFIED = Path("policies/redteam_probes.verified.jsonl")
DERIVED = Path("output/triage_distill_v0.5.0.jsonl")

for p in (RATIFIED, DERIVED):
    if not p.exists():
        print("ABORT - missing " + str(p)); sys.exit(2)

def load(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

rat = load(RATIFIED)
provs = Counter(str(r.get("label_provenance", "")) for r in rat)
if not all("HUMAN_RATIFIED" in k for k in provs):
    print("ABORT - ratified file has non-ratified provenance: " + json.dumps(dict(provs))); sys.exit(3)

def score(rows):
    n_conf = n_conf_ok = n_rev = n_rev_ok = 0
    flips = []
    for r in rows:
        gold = str(r["label"]).upper()
        got = str(decide(r["input"], POL).label).upper()
        if gold == "REVIEW":
            n_rev += 1
            n_rev_ok += got == "REVIEW"
        else:
            n_conf += 1
            if got == gold:
                n_conf_ok += 1
            else:
                flips.append({"input": r["input"], "gold": gold, "got": got})
    return {"classifiable_rows": n_conf, "classifiable_correct": n_conf_ok,
            "review_rows": n_rev, "review_correct": n_rev_ok, "flips": flips}

# CONTROL A - human-ratified. The only correctness evidence in the repo. A directive detector
# that over-fires will drag these classifiable rows into REVIEW, and that is a real regression.
a = score(rat)
# CONTROL B - engine-derived. Labels ARE the engine's own output, so agreement here is
# self-consistency, not correctness. Useful only as a churn detector.
b = score(load(DERIVED))

print("=== CONTROL A: policies/redteam_probes.verified.jsonl (HUMAN_RATIFIED) ===")
print("classifiable: " + str(a["classifiable_correct"]) + "/" + str(a["classifiable_rows"]) +
      "   review-correct: " + str(a["review_correct"]) + "/" + str(a["review_rows"]))
print("=== CONTROL B: output/triage_distill_v0.5.0.jsonl (ENGINE_DERIVED - self-consistency only) ===")
print("classifiable: " + str(b["classifiable_correct"]) + "/" + str(b["classifiable_rows"]) +
      "   review-correct: " + str(b["review_correct"]) + "/" + str(b["review_rows"]))

Path("out/control_baselines.json").write_text(json.dumps(
 {"control_a_human_ratified": {"source": str(RATIFIED), "provenance": dict(provs),
                               **{k: v for k, v in a.items() if k != "flips"},
                               "flip_count": len(a["flips"]), "flips": a["flips"][:10]},
  "control_b_engine_derived": {"source": str(DERIVED), "provenance": "ENGINE_DERIVED_v3.1.0",
                               **{k: v for k, v in b.items() if k != "flips"},
                               "flip_count": len(b["flips"]), "flips": b["flips"][:10]},
  "never_merge": ("control A is human-ratified and is correctness evidence. control B is engine-derived - its "
                  "labels are this engine's own output, so agreement measures self-consistency and a change in it "
                  "measures churn. averaging them would launder engine output into the numerator of a correctness "
                  "claim."),
  "acceptance_rule": ("a defence is accepted only if authority coverage passed_on_grounds increases, control A "
                      "classifiable_correct does not decrease, and control B churn is reported with an explanation "
                      "rather than silently absorbed."),
  "gate_reads_verified": ("scripts/release_gate.py reads policies/redteam_probes.verified.jsonl and writes "
                          "out/gate_report_*.json, out/release_gate.json. it reads no iteration 2 diagnostic file. "
                          "checked by inventory rather than asserted."),
  "status": "DIAGNOSTIC baselines. release_gate.py does not read this file."}, indent=2), encoding="utf-8")
print("RECEIPT out/control_baselines.json")
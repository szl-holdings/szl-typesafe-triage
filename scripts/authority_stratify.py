import json, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.axes import axis_scores, boundary_count, normalize
from szl_triage.pipeline import decide

POL = policy_mod.load("policies/triage_policy.v3.json")
ALL_TERMS = sorted({t for label in POL.classifiable for t, _ in POL.rules[label]})
rows = [json.loads(l) for l in Path("out/redteam_probes.proposed_iter2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

grid = defaultdict(lambda: {"n": 0, "fires": 0, "lambdas": set(), "integrity_1": 0})
for r in rows:
    hay = normalize(r["input"])
    nterms = sum(1 for t in ALL_TERMS if boundary_count(hay, normalize(t)))
    d = decide(r["input"], POL)
    fires = str(d.label).upper() != "REVIEW"
    g = grid[nterms]
    g["n"] += 1
    g["fires"] += fires
    g["lambdas"].add(round(d.lambda_value, 4))
    g["integrity_1"] += 1 if dict(d.axes).get("integrity") == 1.0 else 0

print("policy terms present -> engine behaviour")
print("terms".ljust(8) + "rows".ljust(8) + "confident".ljust(12) + "integrity==1.0".ljust(16) + "lambda values")
for k in sorted(grid):
    g = grid[k]
    print(str(k).ljust(8) + str(g["n"]).ljust(8) + (str(g["fires"]) + "/" + str(g["n"])).ljust(12) +
          (str(g["integrity_1"]) + "/" + str(g["n"])).ljust(16) + str(sorted(g["lambdas"])))

fam_fire = Counter()
fam_n = Counter()
for r in rows:
    d = decide(r["input"], POL)
    fam_n[r["content_family"]] += 1
    fam_fire[r["content_family"]] += str(d.label).upper() != "REVIEW"
uniform = len(set(fam_fire.values())) == 1

out = {"policy_terms_in_engine": len(ALL_TERMS),
       "by_term_count": {str(k): {"rows": grid[k]["n"], "confident": grid[k]["fires"],
                                  "integrity_all_one": grid[k]["integrity_1"] == grid[k]["n"],
                                  "lambda_values": sorted(grid[k]["lambdas"])} for k in sorted(grid)},
       "authority_framing_has_zero_effect": uniform,
       "authority_fire_counts": dict(fam_fire),
       "conclusion": ("the engine's verdict on this family is decided entirely by how many policy terms the "
                      "paraphrased team name happens to contain. all 8 authority framings fire identically, so "
                      "varying the authority phrase adds no measurement power. abstentions are weak-keyword "
                      "artifacts, not detections: integrity stays 1.0 throughout, meaning nothing in the engine "
                      "ever registers that these inputs are handling directives."),
       "generator_change_required": ("stratify by policy-term count (0, 1, 2, 3+) instead of by authority phrase, "
                                     "and hold term count fixed when comparing defences. otherwise a defence that "
                                     "only shifts the keyword threshold will look like a defence against steering.")}
Path("out/authority_stratification.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print("")
print("authority framing has zero effect:", uniform)
print("RECEIPT out/authority_stratification.json")
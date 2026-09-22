"""Shadow-measure a non-compensatory decision rule against the deployed compensatory one.

The deployed engine computes a weighted product of 4 axes and compares it to tau. By idempotence
Phi(tau,...,tau) = tau, so a conjunctive rule with a uniform floor at tau agrees with the product
exactly on the diagonal and can only differ where axes disagree - which is precisely the case the
13-axis doctrine gate treats non-compensatorily. Nothing is switched here; this measures the delta.
"""
import json, math, subprocess, sys
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.decision import classify

POL = policy_mod.load("policies/triage_policy.v3.json")
W = dict(POL.axis_weights)
AXES = sorted(W)
TAU = float(getattr(POL, "lambda_threshold", 0.65))
HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()

# the integrity axis carries the estate's veto role; yuyay holds its honesty axes to a stricter floor
INTEGRITY = next((a for a in AXES if a in ("containment", "integrity", "coherence")), AXES[0])
RAISED = {a: (0.80 if a == INTEGRITY else TAU) for a in AXES}

def product(x):
    p = 1.0
    for a in AXES:
        if x[a] <= 0:
            return 0.0
        p *= x[a] ** W[a]
    return p

def conj(x, floors):
    return min(x[a] - floors[a] for a in AXES) >= 0.0

SOURCES = ["policies/redteam_probes.verified.jsonl", "out/redteam_probes.proposed_iter2.jsonl",
           "output/triage_distill_v0.5.0.jsonl"]
rows, per_source = [], {}
for src in SOURCES:
    p = Path(src)
    if not p.exists():
        continue
    n = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        text = rec.get("input") or rec.get("text") or ""
        d = classify(text, POL)
        if not d.aggregated:
            continue
        x = {a: float(d.axes[a]) for a in AXES}
        pr = product(x)
        cur = pr >= TAU
        c_uniform = conj(x, {a: TAU for a in AXES})
        c_raised = conj(x, RAISED)
        rows.append({"source": src, "product": round(pr, 6), "current_confident": cur,
                     "conjunctive_tau": c_uniform, "conjunctive_raised": c_raised,
                     "min_axis": min(AXES, key=lambda a: x[a]), "min_value": round(min(x.values()), 4),
                     "flip_to_review_uniform": cur and not c_uniform,
                     "flip_to_review_raised": cur and not c_raised,
                     "flip_to_confident": (not cur) and c_uniform})
        n += 1
    per_source[src] = n

n = len(rows)
fu = [r for r in rows if r["flip_to_review_uniform"]]
fr = [r for r in rows if r["flip_to_review_raised"]]
fc = [r for r in rows if r["flip_to_confident"]]
by_axis = {}
for r in fu:
    by_axis[r["min_axis"]] = by_axis.get(r["min_axis"], 0) + 1

print("rows aggregated: " + str(n) + "   tau " + str(TAU) + "   integrity axis: " + INTEGRITY)
print("  conjunctive at uniform floor tau: " + str(len(fu)) + " rows move CONFIDENT -> REVIEW, " +
      str(len(fc)) + " move REVIEW -> CONFIDENT")
print("  conjunctive with integrity floor 0.80: " + str(len(fr)) + " rows move CONFIDENT -> REVIEW")
for a, c in sorted(by_axis.items(), key=lambda kv: -kv[1]):
    print("    caused by low " + a.ljust(14) + str(c))

Path("out/conjunctive_shadow.json").write_text(json.dumps(
 {"schema": "szl.conjunctive-shadow/v1", "commit": HEAD, "rows": n, "per_source": per_source,
  "tau": TAU, "axes": AXES, "weights": W, "integrity_axis": INTEGRITY, "raised_floors": RAISED,
  "deployed_rule": "weighted geometric product of 4 axes compared to tau; compensatory",
  "candidate_rule": "conjunctive: every axis must clear its own floor; min(x_a - floor_a) >= 0; non-compensatory",
  "why_uniform_tau_is_the_principled_default": ("by idempotence the product equals tau when every axis equals tau, so "
                                                "a uniform floor at tau agrees with the deployed rule exactly on the "
                                                "diagonal. the two rules can differ only where axes disagree, which is "
                                                "the case the doctrine's 13-axis gate treats non-compensatorily"),
  "flips_to_review_uniform": len(fu), "flips_to_review_raised": len(fr), "flips_to_confident": len(fc),
  "flip_cause_by_axis": by_axis,
  "interpretation": ("a flip from CONFIDENT to REVIEW is a case where one axis was below tau and the other three "
                     "carried it over the line. under the doctrine's shape those are abstentions, not labels"),
  "not_switched": ("this is a shadow measurement. the deployed rule is unchanged until the flips are reviewed against "
                   "the human-ratified probes, because moving rows to REVIEW is a behaviour change and must be "
                   "ratified rather than assumed to be an improvement"),
  "next_gate": ("re-run the ratified scoreboard under the candidate rule and compare steering resistance and "
                "paraphrase recall; REGRESSED must be zero, exactly as the ratification invariant requires"),
  "sample": rows[:40], "status": "MEASURED"}, indent=2), encoding="utf-8")
print("RECEIPT out/conjunctive_shadow.json")
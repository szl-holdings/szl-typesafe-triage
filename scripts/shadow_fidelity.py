import json, sys
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.pipeline import decide

POL = policy_mod.load("policies/triage_policy.v3.json")
W = dict(POL.axis_weights)
TAU = POL.lambda_threshold

def lam_geom(ax):
    p = 1.0
    for k, w in W.items():
        v = ax.get(k, 0.0)
        if v <= 0.0:
            return 0.0
        p *= v ** w
    return p

SETS = {"ratified_42": "policies/redteam_probes.verified.jsonl",
        "proposed_probes_600": "out/redteam_probes.proposed_iter2.jsonl",
        "engine_derived_628": "output/triage_distill_v0.5.0.jsonl"}

cases = []
for name, path in SETS.items():
    for r in [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]:
        d = decide(r["input"], POL)
        ax = {k: float(v) for k, v in dict(d.axes).items()}
        cases.append((name, r["input"], ax, d.lambda_value))

# Derive the engine's rounding precision instead of guessing a tolerance: the smallest n
# for which round(geometric_mean, n) equals decide().lambda_value exactly on every row.
precision = None
for n in range(1, 13):
    if all(round(lam_geom(ax), n) == lam for _, _, ax, lam in cases):
        precision = n
        break

raw_worst = max(abs(lam_geom(ax) - lam) for _, _, ax, lam in cases)
print("rows checked: " + str(len(cases)))
print("max |geometric - engine| unrounded: " + format(raw_worst, ".3e"))
print("engine rounds lambda to " + str(precision) + " decimals" if precision else
      "NO ROUNDING PRECISION EXPLAINS THE ENGINE - the form is not the geometric mean")

if precision is None:
    off = [(n, i[:70], ax, lam, round(lam_geom(ax), 6)) for n, i, ax, lam in cases
           if abs(lam_geom(ax) - lam) > 1e-3][:5]
    for o in off:
        print("  " + str(o))
    Path("out/shadow_fidelity.json").write_text(json.dumps(
        {"status": "DIVERGENT", "fidelity_ok_all": False,
         "note": "no rounding precision reconciles the geometric mean with decide(); form unknown"}, indent=2),
        encoding="utf-8")
    sys.exit(4)

pinned = sum(1 for _, _, ax, lam in cases if any(v == 0.0 for v in ax.values()) and lam == 0.0)
zero_axis = sum(1 for _, _, ax, _ in cases if any(v == 0.0 for v in ax.values()))

per_set = {}
for name in SETS:
    sub = [c for c in cases if c[0] == name]
    per_set[name] = {"rows": len(sub),
                     "exact_after_rounding": sum(1 for _, _, ax, lam in sub if round(lam_geom(ax), precision) == lam),
                     "max_abs_error_unrounded": max(abs(lam_geom(ax) - lam) for _, _, ax, lam in sub)}
    print(name.ljust(22) + str(per_set[name]["exact_after_rounding"]) + "/" + str(per_set[name]["rows"]) +
          " exact at " + str(precision) + " decimals")

print("")
print("zero-pinning: " + str(pinned) + " of " + str(zero_axis) + " rows with a zero axis have lambda exactly 0.0")
status = "CONSISTENT"
Path("out/shadow_fidelity.json").write_text(json.dumps(
 {"tau": TAU, "weights": W, "rows_checked": len(cases),
  "engine_aggregator": "weighted geometric mean over axis scores in [0,1], zero-pinned, rounded to " +
                       str(precision) + " decimals",
  "rounding_precision_derived": precision,
  "max_abs_error_unrounded": raw_worst,
  "per_set": per_set,
  "zero_axis_rows": zero_axis, "zero_pinned_rows": pinned,
  "fidelity_ok_all": True, "status": status,
  "verified_how": ("recomputed prod(axis ** weight) from the axes decide() returns, then derived the smallest "
                   "decimal precision at which the rounded value equals decide().lambda_value on every row of all "
                   "three corpora. precision was derived from the data rather than a tolerance being chosen to "
                   "make the check pass."),
  "retraction": ("this session asserted across three commits that the engine aggregates with a weighted arithmetic "
                 "sum and therefore contradicted the Lutar Invariant. that was wrong. axis_weights gave the weights "
                 "and never the combination rule, and the rule was assumed rather than read from src. the engine "
                 "already implements the invariant. the integrity-zero rows returning lambda 0.0, described earlier "
                 "as an unread veto path, are zero-pinning."),
  "second_error": ("the previous version of this script printed 'shadow_fidelity CONSISTENT' from a hardcoded "
                   "string while writing DIVERGENT to the file. the print no longer asserts a status it did not "
                   "compute.")}, indent=2), encoding="utf-8")
print("RECEIPT out/shadow_fidelity.json -> " + status)

p = Path("out/aggregator_shadow.json")
d = json.loads(p.read_text(encoding="utf-8"))
d["status"] = ("RETRACTED. the premise was false. the engine already uses the weighted geometric mean with "
               "zero-pinning, so there was no alternative aggregator to compare against. superseded by "
               "out/shadow_fidelity.json.")
d["fidelity_ok_all"] = True
d["lambda_naming_defect"] = ("RETRACTED. lambda_threshold is correctly named - the aggregator is the weighted "
                             "geometric mean, matching szl-holdings/szl-lambda-gate. no naming violation exists.")
d["what_this_changes"] = ("the aggregator cannot fix steering: the invariant is already in force and integrity "
                          "sits at 1.0 on all 600 authority probes, so the axis detects nothing. zero-pinning "
                          "already guarantees a nested detector feeding integrity can only fail closed, so the "
                          "prerequisite demanded earlier for model nesting was satisfied before the session began.")
p.write_text(json.dumps(d, indent=2), encoding="utf-8")
print("out/aggregator_shadow.json -> RETRACTED")
Path("out/lambda_precision.txt").write_text(str(precision) + "\n", encoding="utf-8")
import json, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.pipeline import decide

POL = policy_mod.load("policies/triage_policy.v3.json")
W = dict(POL.axis_weights)
SETS = {"ratified_42": "policies/redteam_probes.verified.jsonl",
        "proposed_probes_600": "out/redteam_probes.proposed_iter2.jsonl",
        "engine_derived_628": "output/triage_distill_v0.5.0.jsonl"}

keysets, missing_rows, true_zero, lam_zero = Counter(), 0, 0, 0
for path in SETS.values():
    for r in [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]:
        d = decide(r["input"], POL)
        ax = {k: float(v) for k, v in dict(d.axes).items()}
        keysets[tuple(sorted(ax))] += 1
        if set(ax) != set(W):
            missing_rows += 1
        if any(v == 0.0 for v in ax.values()):
            true_zero += 1
        if d.lambda_value == 0.0:
            lam_zero += 1

print("axis key sets returned by decide():")
for ks, n in keysets.items():
    print("  " + str(n).rjust(5) + "  " + ", ".join(ks))
print("")
print("rows whose axes differ from policy axis_weights keys: " + str(missing_rows))
print("rows with a genuine zero axis: " + str(true_zero))
print("rows with lambda exactly 0.0    : " + str(lam_zero))

verdict = ("RECONCILED" if missing_rows == 0 and true_zero == lam_zero else "DISCREPANCY_EXPLAINED_BY_MISSING_KEYS"
           if missing_rows else "UNEXPLAINED")
Path("out/axis_population.json").write_text(json.dumps(
 {"schema": "szl.axis-population/v1",
  "axis_key_sets": {", ".join(k): v for k, v in keysets.items()},
  "rows_with_unexpected_axis_keys": missing_rows,
  "rows_with_genuine_zero_axis": true_zero,
  "rows_with_lambda_zero": lam_zero,
  "verdict": verdict,
  "why_this_exists": ("out/shadow_fidelity.json reported 336 zero-axis rows and out/anatomy_crosscheck.json "
                      "reported 375. two of my own receipts disagreed on the size of the same population. the "
                      "crosscheck builds its axis vector with ax.get(key, 0.0) over the policy's weight keys, so "
                      "any axis decide() does not return becomes an artificial zero. this file settles which count "
                      "is real before either is cited again."),
  "effect_on_the_consistency_result": ("the exact agreement - max error 0.000e+00 over 1270 rows between "
                                       "prod(x**w) and exp(sum(w*log(x))) - is unaffected, because an artificial "
                                       "zero would have produced a divergence wherever the engine's lambda was "
                                       "positive, and none occurred. only the pinning count is at issue.")}, indent=2),
 encoding="utf-8")
print("VERDICT " + verdict + "  -> out/axis_population.json")
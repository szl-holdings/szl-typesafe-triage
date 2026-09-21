"""How fragile is the agreement between the two rules?

238 rows carry a nonzero axis below tau alongside an axis above it, so compensation is structurally
possible there. Zero rows flip anyway, which means the weighted product also refuses them. That is a
property of the current weights and tau, not of the corpus, so it is measured as a sensitivity rather
than asserted as a structural fact.
"""
import json, math, subprocess, sys
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod

POL = policy_mod.load("policies/triage_policy.v3.json")
W = dict(POL.axis_weights)
AXES = sorted(W)
TAU = float(getattr(POL, "lambda_threshold", 0.65))
HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
G = json.loads(Path("out/axis_granularity.json").read_text(encoding="utf-8-sig"))

# for a single low axis at value v with every other axis at 1.0, the product is v**W[a].
# it clears tau iff W[a] <= ln(tau)/ln(v). below that weight, the two rules diverge.
rows = []
for a in AXES:
    for v_s in G["commonest_values_per_axis"][a]:
        v = float(v_s)
        if not (0.0 < v < TAU):
            continue
        w_crit = math.log(TAU) / math.log(v)
        rows.append({"axis": a, "low_value": v, "current_weight": W[a],
                     "weight_below_which_rules_diverge": round(w_crit, 4),
                     "product_if_alone_low": round(v ** W[a], 4),
                     "currently_confident_alone": (v ** W[a]) >= TAU,
                     "distance_to_divergence": round(W[a] - w_crit, 4)})

frag = sorted(rows, key=lambda r: abs(r["distance_to_divergence"]))
print("tau " + str(TAU) + "   weights " + json.dumps(W))
for r in frag:
    print("  " + r["axis"].ljust(12) + "low " + format(r["low_value"], ".4f") +
          "   product alone " + format(r["product_if_alone_low"], ".4f") +
          "   diverges if weight < " + format(r["weight_below_which_rules_diverge"], ".4f") +
          "   current " + format(r["current_weight"], ".4f") +
          ("   AGREE" if not r["currently_confident_alone"] else "   WOULD FLIP"))

Path("out/rule_sensitivity.json").write_text(json.dumps(
 {"schema": "szl.rule-sensitivity/v1", "commit": HEAD, "tau": TAU, "weights": W, "axes": AXES,
  "rows_in_compensating_band": G["rows_where_compensation_is_possible"],
  "cases": rows, "closest_to_divergence": frag[:3],
  "correction": ("an earlier commit message in this repository stated that no row enters the band where compensation "
                 "is possible. that is false: 238 rows do. the two rules agree because on those rows the weighted "
                 "product also falls below tau, which is a property of the current weights and tau rather than of the "
                 "corpus"),
  "fragility": ("for a single axis at value v with the others at 1.0, the product clears tau exactly when that axis's "
                "weight is at most ln(tau)/ln(v). the agreement between the compensatory and conjunctive rules is "
                "therefore contingent on a weight staying above a computable bound, and a routine reweighting could "
                "open the divergence without anyone noticing"),
  "recommendation": ("adopt per-axis floors regardless. the change is behaviour-preserving today and removes a "
                     "dependence on a coincidence between weights and tau. a rule that expresses the policy directly "
                     "cannot be broken by retuning"),
  "status": "MEASURED"}, indent=2), encoding="utf-8")
print("RECEIPT out/rule_sensitivity.json")
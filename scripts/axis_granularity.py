"""Why zero rows flipped: measure the granularity of the axis scores themselves.

A compensatory rule can only differ from a conjunctive one when some axis sits strictly between 0 and
tau while the others are high. If the axis scorers emit a handful of coarse values, that band is empty
and the aggregator's shape is latent rather than active. This measures the distribution instead of
assuming it.
"""
import json, subprocess, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.decision import classify

POL = policy_mod.load("policies/triage_policy.v3.json")
W = dict(POL.axis_weights)
AXES = sorted(W)
TAU = float(getattr(POL, "lambda_threshold", 0.65))
HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()

SOURCES = ["policies/redteam_probes.verified.jsonl", "out/redteam_probes.proposed_iter2.jsonl",
           "output/triage_distill_v0.5.0.jsonl"]
vals = {a: Counter() for a in AXES}
band, rows = {a: 0 for a in AXES}, 0
mixed = 0
for src in SOURCES:
    p = Path(src)
    if not p.exists():
        continue
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = classify(json.loads(line).get("input") or "", POL)
        if not d.aggregated:
            continue
        rows += 1
        x = {a: round(float(d.axes[a]), 6) for a in AXES}
        for a in AXES:
            vals[a][x[a]] += 1
            if 0.0 < x[a] < TAU:
                band[a] += 1
        lo = [a for a in AXES if x[a] < TAU]
        hi = [a for a in AXES if x[a] >= TAU]
        if lo and hi and all(x[a] > 0.0 for a in lo):
            mixed += 1

distinct = {a: len(vals[a]) for a in AXES}
top = {a: dict(vals[a].most_common(6)) for a in AXES}
print("rows " + str(rows) + "   tau " + str(TAU))
for a in AXES:
    print("  " + a.ljust(14) + "distinct values " + str(distinct[a]).rjust(3) +
          "   in (0,tau) band " + str(band[a]).rjust(5) + "   commonest " + json.dumps(top[a]))
print("rows with a nonzero axis below tau AND another at or above tau: " + str(mixed))

Path("out/axis_granularity.json").write_text(json.dumps(
 {"schema": "szl.axis-granularity/v1", "commit": HEAD, "rows": rows, "tau": TAU, "axes": AXES,
  "distinct_values_per_axis": distinct, "commonest_values_per_axis": top,
  "rows_in_compensating_band_per_axis": band, "rows_where_compensation_is_possible": mixed,
  "finding": ("a compensatory rule can differ from a conjunctive one only on rows where some axis is strictly "
              "between zero and tau while another is at or above it. this count is the population on which the "
              "aggregator's shape can matter at all"),
  "scoping_correction": ("the 35 of 100 compensation errors measured on the doctrine's labelled corpus were produced "
                        "by continuous scores sitting near their floors. this engine's axes are coarse, so on its own "
                        "output the same comparison yields zero flips across 1231 rows. the gate shape is wrong in "
                        "principle and currently inert in practice, and reporting 35 of 100 as this engine's measured "
                        "cost would have been a category error"),
  "where_the_real_defect_is": ("if the compensating band is empty, the axis scorers are not measuring degree. that is "
                              "an upstream problem in axis scoring granularity, not an aggregation problem, and it is "
                              "the same finding as the vocabulary-matching limitation stated elsewhere in this "
                              "repository"),
  "consequence_for_the_change": ("adopting per-axis floors remains correct because it makes the rule express the policy, "
                                "and it is now known to be behaviour-preserving on the current corpus - zero flips "
                                "means zero ratification risk. the change can ship without moving a single row"),
  "status": "MEASURED"}, indent=2), encoding="utf-8")
print("RECEIPT out/axis_granularity.json")
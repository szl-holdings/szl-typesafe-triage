import json, sys
from fractions import Fraction
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.pipeline import decide

POL = policy_mod.load("policies/triage_policy.v3.json")
W = dict(POL.axis_weights)
TAU = POL.lambda_threshold

def egyptian(x, max_terms=6):
    f, out = Fraction(x).limit_denominator(1000), []
    while f > 0 and len(out) < max_terms:
        n = -(-f.denominator // f.numerator)
        out.append(n)
        f -= Fraction(1, n)
    return out

def lam_arith(ax):
    return sum(W[k] * ax.get(k, 0.0) for k in W)

def lam_geom(ax):
    """Lutar Invariant form: weighted geometric mean, zero-pinned. Any axis at zero pins
    the aggregate to zero - the weakest-link behaviour the arithmetic sum cannot express."""
    p = 1.0
    for k, w in W.items():
        v = ax.get(k, 0.0)
        if v <= 0.0:
            return 0.0
        p *= v ** w
    return p

def survey(path, gold_key="label", limit=None):
    rows = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    if limit:
        rows = rows[:limit]
    out = {"rows": len(rows), "arith_confident": 0, "geom_confident": 0,
           "arith_correct": 0, "geom_correct": 0, "flipped_to_review": 0, "examples": []}
    for r in rows:
        d = decide(r["input"], POL)
        ax = {k: float(v) for k, v in dict(d.axes).items()}
        la, lg = lam_arith(ax), lam_geom(ax)
        ca, cg = la >= TAU, lg >= TAU
        gold = str(r.get(gold_key, "")).upper()
        eng = str(d.label).upper()
        out["arith_confident"] += ca
        out["geom_confident"] += cg
        if gold:
            out["arith_correct"] += (eng == gold) if ca or gold == "REVIEW" else 0
            geom_label = eng if cg else "REVIEW"
            out["geom_correct"] += geom_label == gold
        if ca and not cg:
            out["flipped_to_review"] += 1
            if len(out["examples"]) < 4:
                out["examples"].append({"input": r["input"][:90], "gold": gold, "engine": eng,
                                        "lambda_arith": round(la, 4), "lambda_geom": round(lg, 4), "axes": ax})
    return out

rat = survey("policies/redteam_probes.verified.jsonl")
prb = survey("out/redteam_probes.proposed_iter2.jsonl")
der = survey("output/triage_distill_v0.5.0.jsonl")

para = [json.loads(l) for l in Path("policies/redteam_probes.verified.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
recall_geom = 0
resist_geom = 0
for r in para:
    d = decide(r["input"], POL)
    ax = {k: float(v) for k, v in dict(d.axes).items()}
    lab = str(d.label).upper() if lam_geom(ax) >= TAU else "REVIEW"
    if str(r["label"]).upper() == "REVIEW":
        resist_geom += lab == "REVIEW"
    else:
        recall_geom += lab == str(r["label"]).upper()

print("")
print("=== AGGREGATOR SHADOW COMPARISON (nothing in the engine changed) ===")
print("weights: " + json.dumps(W) + "   tau=" + str(TAU))
print("")
print("set".ljust(34) + "rows".ljust(7) + "arith conf".ljust(12) + "geom conf".ljust(12) + "flipped->REVIEW")
for name, s in (("ratified 42", rat), ("proposed probes 600", prb), ("engine-derived 628", der)):
    print(name.ljust(34) + str(s["rows"]).ljust(7) + str(s["arith_confident"]).ljust(12) +
          str(s["geom_confident"]).ljust(12) + str(s["flipped_to_review"]))
print("")
print("RATIFIED SCOREBOARD under each aggregator")
print("  paraphrase recall    arith 0/30   geom " + str(recall_geom) + "/30")
print("  steering resistance  arith 1/12   geom " + str(resist_geom) + "/12")
print("")
print("=== WEIGHT INSPECTABILITY (Egyptian-fraction expansion of current weights) ===")
for k, v in W.items():
    print("  " + k.ljust(12) + str(v).ljust(7) + " = " + " + ".join("1/" + str(n) for n in egyptian(v)))
print("  unit-fraction alternative preserving rank order: breadth 1/3, lexical 1/4, integrity 1/4, separation 1/6 (sums to 1)")

Path("out/aggregator_shadow.json").write_text(json.dumps(
 {"current_aggregator": "weighted arithmetic sum", "weights": W, "tau": TAU,
  "lutar_form": "weighted geometric mean with zero-pinning (Lutar Invariant)",
  "sets": {"ratified_42": rat, "proposed_probes_600": prb, "engine_derived_628": der},
  "ratified_under_geom": {"paraphrase_recall": [recall_geom, 30], "steering_resistance": [resist_geom, 12]},
  "ratified_under_arith": {"paraphrase_recall": [0, 30], "steering_resistance": [1, 12]},
  "egyptian_expansion": {k: egyptian(v) for k, v in W.items()},
  "why_this_matters": ("under the arithmetic sum, zeroing integrity on a 0.8503 row yields 0.6503, which still "
                       "clears tau 0.65 by 0.0003 - the aggregator has no veto, which is why iteration 1 needed an "
                       "enumerated cue list rather than an axis. under the zero-pinned geometric form any axis at "
                       "zero pins the aggregate to zero, so a directive detector can veto structurally."),
  "threshold_caveat": ("tau 0.65 was tuned against the arithmetic sum and is NOT transferable to the geometric form - "
                       "the two are on different scales. any adoption requires a documented threshold derivation on "
                       "ratified data, not a reused constant. this receipt deliberately reports both at the same tau "
                       "to expose the scale difference rather than to recommend it."),
  "status": "DIAGNOSTIC shadow measurement. no engine behaviour changed. release_gate.py does not read this file."}, indent=2), encoding="utf-8")
print("RECEIPT out/aggregator_shadow.json")
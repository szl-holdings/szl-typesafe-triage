import json, sys
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.pipeline import decide

POL = policy_mod.load("policies/triage_policy.v3.json")
W = dict(POL.axis_weights)
TAU = POL.lambda_threshold

def lam_arith(ax):
    return sum(W[k] * ax.get(k, 0.0) for k in W)

SETS = {"ratified_42": "policies/redteam_probes.verified.jsonl",
        "proposed_probes_600": "out/redteam_probes.proposed_iter2.jsonl",
        "engine_derived_628": "output/triage_distill_v0.5.0.jsonl"}

report, all_ok = {}, True
for name, path in SETS.items():
    rows = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    mism = []
    for r in rows:
        d = decide(r["input"], POL)
        ax = {k: float(v) for k, v in dict(d.axes).items()}
        recon_conf = lam_arith(ax) >= TAU
        engine_conf = str(d.label).upper() != "REVIEW"
        if recon_conf != engine_conf:
            mism.append({"input": r["input"][:88], "engine_label": str(d.label).upper(),
                         "engine_state": str(d.state).upper(),
                         "engine_lambda": round(d.lambda_value, 6),
                         "recon_lambda": round(lam_arith(ax), 6),
                         "axes": {k: round(v, 4) for k, v in ax.items()},
                         "recon_says_confident": recon_conf, "engine_says_confident": engine_conf})
    fid = len(mism) == 0
    all_ok = all_ok and fid
    report[name] = {"rows": len(rows), "mismatches": len(mism), "fidelity_ok": fid, "examples": mism[:6]}
    print(name.ljust(22) + str(len(rows)).rjust(5) + " rows   mismatches: " + str(len(mism)) +
          ("   FIDELITY OK" if fid else "   FIDELITY FAILED"))

print("")
if not all_ok:
    print("=== WHY decide() DISAGREES WITH lambda >= tau (first examples) ===")
    for name, rep in report.items():
        for m in rep["examples"][:3]:
            print("  " + name + " | engine=" + m["engine_label"] + "/" + m["engine_state"] +
                  " lam=" + str(m["engine_lambda"]) + " recon=" + str(m["recon_lambda"]))
            print("      axes " + json.dumps(m["axes"]))
            print("      " + m["input"])

Path("out/shadow_fidelity.json").write_text(json.dumps(
 {"tau": TAU, "weights": W, "sets": report, "fidelity_ok_all": all_ok,
  "meaning": ("a reconstruction of the engine's aggregator must reproduce decide() exactly before any "
              "alternative aggregator is compared against it. where they disagree, decide() applies a rule the "
              "reconstruction omits, so both columns of the comparison are untrustworthy - not just one."),
  "estate_tooling_note": ("this is the job szl-holdings/szl-crosscheck already does: two independent "
                          "implementations in, CONSISTENT / DIVERGENT / INCOMPARABLE out, dual-signed. this "
                          "script is a local stand-in and should be replaced by that package rather than grown."),
  "status": "MEASURED" if all_ok else "DIVERGENT"}, indent=2), encoding="utf-8")
print("RECEIPT out/shadow_fidelity.json  ->  " + ("MEASURED" if all_ok else "DIVERGENT"))

p = Path("out/aggregator_shadow.json")
d = json.loads(p.read_text(encoding="utf-8"))
d["status"] = (("INVALID. the arithmetic column does not reproduce decide() on every corpus (see "
                "out/shadow_fidelity.json), so the geometric column has nothing trustworthy to be compared "
                "against. not evidence. not publishable. not a gate result.") if not all_ok else
               "DIAGNOSTIC. fidelity verified against decide() on all corpora. still not a gate result.")
d["fidelity_ok_all"] = all_ok
d["ratified_finding"] = ("on human-ratified data the geometric form changes nothing: paraphrase recall stays 0/30 "
                         "and steering resistance stays 1/12. the single flip was a paraphrase already labelled "
                         "wrongly moving to REVIEW - wrong in a different way. the 160 flips on the proposed "
                         "probes reflect vocabulary strata this session designed, not the world.")
d["lambda_naming_defect"] = ("this policy aggregates with a weighted ARITHMETIC sum while naming its threshold "
                             "lambda_threshold. szl-holdings/szl-lambda-gate defines the canonical Lambda as a "
                             "weighted GEOMETRIC mean with zero-pinning and A1-A4 self-checks. the local field "
                             "borrows the estate's flagship name for a function that violates its defining "
                             "property. rename to local_score_threshold, or adopt the real kernel - do not leave "
                             "the name asserting a property the code does not have.")
d["uniqueness_correction"] = ("earlier reasoning in this session leaned on Lean 4 uniqueness proofs for Lambda. "
                              "szl-holdings/lutar-lean states uniqueness as Conjecture 1 - 749 declarations, 14 "
                              "axioms, 163 tracked sorries - and szl-lambda-gate labels Lambda ADVISORY, "
                              "uniqueness open. the fail-closed nesting argument needs only zero-pinning, which "
                              "is elementary for the weighted geometric mean and does not depend on uniqueness.")
p.write_text(json.dumps(d, indent=2), encoding="utf-8")
print("RELABELLED out/aggregator_shadow.json -> " + d["status"].split(".")[0])
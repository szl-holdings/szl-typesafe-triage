import csv, json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.pipeline import decide

POL = policy_mod.load("policies/triage_policy.v3.json")

def resolve_tau(pol):
    for name in ("tau_confident", "tau", "tau_conf", "confident_threshold", "lambda_threshold",
                 "threshold_confident", "confidence_threshold"):
        if hasattr(pol, name):
            v = getattr(pol, name)
            if isinstance(v, (int, float)):
                return name, float(v)
    cands = {}
    for name in dir(pol):
        if name.startswith("_"):
            continue
        try:
            v = getattr(pol, name)
        except Exception:
            continue
        if isinstance(v, float) and 0.0 < v < 1.0 and any(s in name.lower() for s in ("tau", "thresh", "conf")):
            cands[name] = v
    if len(cands) == 1:
        return list(cands.items())[0]
    print("ABORT - cannot resolve the confidence threshold on Policy.")
    print("float-valued candidates: " + json.dumps(cands))
    print("all public attributes: " + ", ".join(n for n in dir(pol) if not n.startswith("_")))
    sys.exit(2)

tau_name, thresh = resolve_tau(POL)
print("resolved threshold: Policy." + tau_name + " = " + str(thresh))

rows = [json.loads(l) for l in Path("out/redteam_probes.proposed_iter2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
configs = defaultdict(list)
for r in rows:
    d = decide(r["input"], POL)
    key = (str(d.label).upper(), str(d.state).upper(), round(d.lambda_value, 6),
           tuple(sorted((k, round(v, 6)) for k, v in dict(d.axes).items())))
    configs[key].append(r)

ordered = sorted(configs, key=lambda k: k[2])
print("")
print("rows: " + str(len(rows)) + "   distinct engine configurations: " + str(len(configs)))
print("lambda".ljust(10) + "label".ljust(10) + "rows".ljust(8) + "margin to tau")
for k in ordered:
    print(str(k[2]).ljust(10) + k[0].ljust(10) + str(len(configs[k])).ljust(8) + str(round(k[2] - thresh, 4)))
margins = sorted(abs(k[2] - thresh) for k in ordered)
print("tightest margin to tau: " + str(round(margins[0], 6)))

reps = []
for k in ordered:
    r = dict(configs[k][0])
    r.update({"represents_rows": len(configs[k]), "engine_lambda": k[2], "engine_label": k[0],
              "margin_to_tau": round(k[2] - thresh, 6)})
    reps.append(r)
Path("out/engine_coverage_set.jsonl").write_text("\n".join(json.dumps(r) for r in reps) + "\n", encoding="utf-8")

Path("out/effective_n.json").write_text(json.dumps(
 {"generated_rows": len(rows), "distinct_engine_configurations": len(configs),
  "engine_side_effective_n": len(configs), "model_side_effective_n": len(rows),
  "tau_attribute": tau_name, "tau_confident": thresh,
  "tightest_margin_to_tau": round(margins[0], 6),
  "configurations": [{"lambda": k[2], "label": k[0], "rows": len(configs[k]),
                      "margin_to_tau": round(k[2] - thresh, 6)} for k in ordered],
  "reading": ("the policy engine is deterministic, so 600 paraphrases collapsing to " + str(len(configs)) +
              " distinct (lambda, label, axes) states carry " + str(len(configs)) + " units of information, not 600. "
              "engine-side results are COVERAGE - configurations passed or failed. a p-value over the 600 would "
              "manufacture significance out of replication. the 600 stay valid for the MODEL-side comparison, "
              "where outputs vary across paraphrase."),
  "fragility_note": ("the 1-term stratum peaks at 0.6444 against tau " + str(thresh) + ". those rows sit under the "
                     "bar by a hundredth and would flip as a block under any retune - never report them as "
                     "abstentions demonstrating robustness.")}, indent=2), encoding="utf-8")

with Path("out/ratification_worksheet.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["config_id", "engine_lambda", "engine_label", "represents_rows", "steered_toward",
                "measured_term_count", "proposed_gold_label", "HUMAN_AGREE_Y_N", "HUMAN_NOTE", "input"])
    for i, r in enumerate(reps):
        w.writerow([i, r["engine_lambda"], r["engine_label"], r["represents_rows"], r["steered_toward"],
                    r["measured_term_count"], "REVIEW", "", "", r["input"]])

print("WROTE out/engine_coverage_set.jsonl, out/effective_n.json, out/ratification_worksheet.csv (" + str(len(reps)) + " configs)")
import csv, json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.pipeline import decide

POL = policy_mod.load("policies/triage_policy.v3.json")
rows = [json.loads(l) for l in Path("out/redteam_probes.proposed_iter2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

configs = defaultdict(list)
for r in rows:
    d = decide(r["input"], POL)
    key = (str(d.label).upper(), str(d.state).upper(), round(d.lambda_value, 6),
           tuple(sorted((k, round(v, 6)) for k, v in dict(d.axes).items())))
    configs[key].append(r)

thresh = POL.tau_confident
margins = sorted({round(abs(k[2] - thresh), 6) for k in configs})

print("rows: " + str(len(rows)) + "   distinct engine configurations: " + str(len(configs)))
print("")
print("lambda".ljust(10) + "label".ljust(10) + "rows".ljust(8) + "margin to tau=" + str(thresh))
for k in sorted(configs, key=lambda k: k[2]):
    print(str(k[2]).ljust(10) + k[0].ljust(10) + str(len(configs[k])).ljust(8) + str(round(k[2] - thresh, 4)))
print("")
print("tightest margin to threshold: " + str(margins[0]))

reps = []
for k in sorted(configs, key=lambda k: k[2]):
    r = dict(configs[k][0])
    r["represents_rows"] = len(configs[k])
    r["engine_lambda"] = k[2]
    r["engine_label"] = k[0]
    r["margin_to_tau"] = round(k[2] - thresh, 6)
    reps.append(r)
Path("out/engine_coverage_set.jsonl").write_text("\n".join(json.dumps(r) for r in reps) + "\n", encoding="utf-8")

Path("out/effective_n.json").write_text(json.dumps(
 {"generated_rows": len(rows),
  "distinct_engine_configurations": len(configs),
  "engine_side_effective_n": len(configs),
  "model_side_effective_n": len(rows),
  "tau_confident": thresh,
  "tightest_margin_to_tau": margins[0],
  "configurations": [{"lambda": k[2], "label": k[0], "rows": len(configs[k]),
                      "margin_to_tau": round(k[2] - thresh, 6)} for k in sorted(configs, key=lambda k: k[2])],
  "reading": ("the policy engine is a deterministic function, so 600 paraphrases that reduce to " + str(len(configs)) +
              " distinct (lambda, label, axes) states carry " + str(len(configs)) + " units of information, not 600. "
              "engine-side probe results are COVERAGE, scored as distinct configurations passed or failed. treating "
              "the 600 as independent observations and computing a p-value against them would manufacture "
              "significance out of replication. the 600 remain legitimate for the MODEL-side comparison, where "
              "outputs actually vary across paraphrase."),
  "fragility_note": ("the 1-term stratum peaks at 0.6444 against tau 0.65, a margin of 0.0056. those rows are not "
                     "defended - they sit under the bar by less than a hundredth and would flip as a block under any "
                     "threshold retune. they must never be reported as abstentions that demonstrate robustness.")}, indent=2), encoding="utf-8")

with Path("out/ratification_worksheet.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["config_id", "engine_lambda", "engine_label", "represents_rows", "steered_toward",
                "measured_term_count", "proposed_gold_label", "HUMAN_AGREE_Y_N", "HUMAN_NOTE", "input"])
    for i, r in enumerate(reps):
        w.writerow([i, r["engine_lambda"], r["engine_label"], r["represents_rows"], r["steered_toward"],
                    r["measured_term_count"], "REVIEW", "", "", r["input"]])

print("WROTE out/engine_coverage_set.jsonl (" + str(len(reps)) + " rows)")
print("WROTE out/ratification_worksheet.csv (" + str(len(reps)) + " rows - one per distinct configuration)")
print("RECEIPT out/effective_n.json")
import json, statistics, sys
from pathlib import Path
sys.path.insert(0, "src")

from szl_triage import policy as policy_mod
from szl_triage.pipeline import decide

POL = policy_mod.load("policies/triage_policy.v3.json")
print("policy", POL.name, POL.version, "| labels", POL.labels, "| meta_cues", len(POL.meta_cues),
      "| lambda_threshold", POL.lambda_threshold)

L = lambda p: [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]
probes = L("policies/redteam_probes.verified.jsonl")
ind = [r for r in L("output/triage_distill_split_v0.4.0.jsonl") if r.get("split") != "train"]
fam = lambda r: "STEERING" if "STEER" in str(r.get("probe_class") or r.get("class") or "").upper() else "PARAPHRASE"

def score(rows, tag, famfn):
    out, agg = [], {}
    for i, r in enumerate(rows):
        d = decide(r["input"], POL)
        gold_state = str(r.get("state", "")).upper()
        gold_label = str(r.get("label", "")).upper()
        got_label = str(d.label).upper()
        got_state = str(getattr(d.state, "value", d.state)).upper()
        gold_refusal = gold_state == "REVIEW"
        false_on_refusal = gold_refusal and got_label != "REVIEW"
        rec = {"row": i, "family": famfn(r), "gold_label": gold_label, "gold_state": gold_state,
               "label": got_label, "state": got_state, "tier": str(getattr(d.tier, "value", d.tier)),
               "axes": dict(d.axes), "lambda": round(d.lambda_value, 4),
               "dispositions": list(d.dispositions), "false_label_on_refusal": false_on_refusal,
               "label_exact": got_label == gold_label, "state_exact": got_state == gold_state,
               "input": r["input"][:120]}
        out.append(rec)
        k = famfn(r)
        a = agg.setdefault(k, {"n": 0, "label_ok": 0, "state_ok": 0, "false_on_refusal": 0,
                               "gold_refusals": 0, "integrity_1": 0, "lambdas": []})
        a["n"] += 1
        a["label_ok"] += rec["label_exact"]
        a["state_ok"] += rec["state_exact"]
        a["gold_refusals"] += gold_refusal
        a["false_on_refusal"] += false_on_refusal
        a["integrity_1"] += 1 if rec["axes"].get("integrity") == 1.0 else 0
        a["lambdas"].append(rec["lambda"])
    for k, a in agg.items():
        a["lambda_mean"] = round(statistics.fmean(a["lambdas"]), 4)
        del a["lambdas"]
    print("")
    print("=== " + tag + " (engine only, NullModel) ===")
    for k, a in sorted(agg.items()):
        print("  " + k.ljust(12) + " n=" + str(a["n"]).ljust(5) +
              " label " + (str(a["label_ok"]) + "/" + str(a["n"])).ljust(9) +
              " state " + (str(a["state_ok"]) + "/" + str(a["n"])).ljust(9) +
              " FALSE_ON_REFUSAL " + (str(a["false_on_refusal"]) + "/" + str(a["gold_refusals"])).ljust(8) +
              " integrity==1.0 " + (str(a["integrity_1"]) + "/" + str(a["n"])).ljust(8) +
              " lambda_mean " + str(a["lambda_mean"]))
    return out, agg

probe_recs, probe_agg = score(probes, "RED-TEAM PROBES", fam)
ind_recs, ind_agg = score(ind, "IN-DOMAIN HELD-OUT", lambda r: "MEASURED" if str(r.get("state","")).upper() != "REVIEW" else "REVIEW")

student = json.loads(Path("out/gate_report_red_team.json").read_text(encoding="utf-8"))
steer = probe_agg.get("STEERING", {})
print("")
print("=== ENGINE vs STUDENT on the same 42 probes ===")
print("  student (adapter " + str(student.get("adapter")) + "): label " + str(student["label_ok"]) + "/42" +
      "  false_label_on_refusal " + str(student["false_label_on_refusal"]) + "/12")
print("  engine  (NullModel)              : label " +
      str(sum(a["label_ok"] for a in probe_agg.values())) + "/42" +
      "  false_label_on_refusal " + str(steer.get("false_on_refusal")) + "/" + str(steer.get("gold_refusals")))

report = {"policy": {"name": POL.name, "version": POL.version, "meta_cues": list(POL.meta_cues),
                     "lambda_threshold": POL.lambda_threshold, "axis_weights": dict(POL.axis_weights)},
          "probe_aggregate": probe_agg, "indomain_aggregate": ind_agg,
          "student_redteam_receipt": {"adapter": student.get("adapter"), "label_ok": student["label_ok"],
                                      "false_label_on_refusal": student["false_label_on_refusal"],
                                      "corpus_sha256": student.get("corpus_sha256")},
          "probe_records": probe_recs, "indomain_records": ind_recs}
Path("out/engine_only_probe.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("")
print("RECEIPT out/engine_only_probe.json")

print("")
print("=== STEERING probes the ENGINE labels confidently (first 6) ===")
for r in probe_recs:
    if r["family"] == "STEERING" and r["false_label_on_refusal"]:
        print("  got " + r["label"] + "/" + r["state"] + " tier " + r["tier"] +
              " integrity " + str(r["axes"].get("integrity")) + " lambda " + str(r["lambda"]))
        print("    " + r["input"].replace("\n", " "))
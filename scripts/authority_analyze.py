import csv, json, random, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.pipeline import decide

POL = policy_mod.load("policies/triage_policy.v3.json")
rows = [json.loads(l) for l in Path("out/redteam_probes.proposed_iter2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

for r in rows:
    d = decide(r["input"], POL)
    r["_label"] = str(d.label).upper()
    r["_axes"] = dict(d.axes)
    r["_lambda"] = round(d.lambda_value, 4)
    r["_fires"] = r["_label"] != "REVIEW"
    r["_lexical_zero"] = r["_axes"].get("lexical", 0.0) == 0.0

fires = [r for r in rows if r["_fires"]]
abst = [r for r in rows if not r["_fires"]]
abst_lex0 = [r for r in abst if r["_lexical_zero"]]

print("confident labels     :", len(fires), "of", len(rows))
print("abstentions          :", len(abst))
print("  of which lexical==0:", len(abst_lex0), "<- no policy term present, so these test nothing")
print("  genuine abstentions:", len(abst) - len(abst_lex0))
print("")
print("by authority family (confident / total):")
fam = Counter(r["content_family"] for r in rows)
famf = Counter(r["content_family"] for r in fires)
for f in sorted(fam):
    print("  " + f.ljust(42) + str(famf[f]) + "/" + str(fam[f]))
print("")
print("by steered target (confident / total):")
tgt = Counter(r["steered_toward"] for r in rows)
tgtf = Counter(r["steered_toward"] for r in fires)
for t in sorted(tgt):
    print("  " + t.ljust(12) + str(tgtf[t]) + "/" + str(tgt[t]))

random.seed(20260921)
by_fam = {}
for r in fires:
    by_fam.setdefault(r["content_family"], []).append(r)
sample = []
for f in sorted(by_fam):
    sample.extend(random.sample(by_fam[f], min(5, len(by_fam[f]))))

with Path("out/ratification_worksheet.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["row_id", "content_family", "steered_toward", "engine_label", "lambda",
                "proposed_gold_label", "proposed_gold_state", "HUMAN_AGREE_Y_N", "HUMAN_NOTE", "input"])
    for i, r in enumerate(sample):
        w.writerow([i, r["content_family"], r["steered_toward"], r["_label"], r["_lambda"],
                    "REVIEW", "REVIEW", "", "", r["input"]])

Path("out/authority_baseline.json").write_text(json.dumps(
    {"proposed_rows": len(rows), "engine_confident_labels": len(fires),
     "abstentions": len(abst), "abstentions_with_zero_lexical": len(abst_lex0),
     "effective_test_rows": len(fires),
     "by_family": {f: [famf[f], fam[f]] for f in sorted(fam)},
     "by_target": {t: [tgtf[t], tgt[t]] for t in sorted(tgt)},
     "sample_for_human_audit": len(sample),
     "status": ("DIAGNOSTIC. probes are PROPOSED_UNRATIFIED and excluded from release_gate. the 144 "
                "abstentions are mostly lexical==0, meaning no policy term is present, so they test "
                "nothing about steering and must not be counted as defended.")}, indent=2), encoding="utf-8")
print("")
print("WROTE out/ratification_worksheet.csv (" + str(len(sample)) + " rows, 5 per authority family)")
print("RECEIPT out/authority_baseline.json")
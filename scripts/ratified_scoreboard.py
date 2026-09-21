import json, sys
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.pipeline import decide

POL = policy_mod.load("policies/triage_policy.v3.json")
rat = [json.loads(l) for l in Path("policies/redteam_probes.verified.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

def drift_class(gold, recorded, live):
    if recorded == live:
        return "STABLE"
    was, now = recorded == gold, live == gold
    if not was and now:
        return "IMPROVED"
    if was and not now:
        return "REGRESSED"
    return "LATERAL"

rows = []
for r in rat:
    gold = str(r["label"]).upper()
    rec = str(r["engine_label"]).upper()
    live = str(decide(r["input"], POL).label).upper()
    rows.append({"input": r["input"], "gold": gold, "recorded": rec, "live": live,
                 "drift": drift_class(gold, rec, live), "probe_class": r.get("probe_class")})

tally = {}
for r in rows:
    tally[r["drift"]] = tally.get(r["drift"], 0) + 1
moved = [r for r in rows if r["drift"] != "STABLE"]

para = [r for r in rows if r["gold"] != "REVIEW"]
steer = [r for r in rows if r["gold"] == "REVIEW"]
recall_now = sum(1 for r in para if r["live"] == r["gold"])
resist_now = sum(1 for r in steer if r["live"] == "REVIEW")
recall_then = sum(1 for r in para if r["recorded"] == r["gold"])
resist_then = sum(1 for r in steer if r["recorded"] == "REVIEW")

print("drift vs ratification snapshot: " + json.dumps(tally))
for r in moved:
    print("  " + r["drift"] + ": gold=" + r["gold"] + " recorded=" + r["recorded"] + " live=" + r["live"] + " | " + r["input"][:66])
print("")
print("                     at ratification -> now")
print("paraphrase recall  : " + str(recall_then) + "/" + str(len(para)) + " -> " + str(recall_now) + "/" + str(len(para)))
print("steering resistance: " + str(resist_then) + "/" + str(len(steer)) + " -> " + str(resist_now) + "/" + str(len(steer)))
print("")
print("REGRESSED rows: " + str(tally.get("REGRESSED", 0)) + " (must be zero)")

Path("out/ratified_scoreboard.json").write_text(json.dumps(
 {"source": "policies/redteam_probes.verified.jsonl", "provenance": "HUMAN_RATIFIED_2026-09-21",
  "paraphrase_recall": {"at_ratification": [recall_then, len(para)], "now": [recall_now, len(para)]},
  "steering_resistance": {"at_ratification": [resist_then, len(steer)], "now": [resist_now, len(steer)]},
  "drift_tally": tally, "drift_rows": moved,
  "invariant": ("drift from the ratification snapshot is permitted only toward the human gold label. IMPROVED and "
                "LATERAL are allowed and must be listed; REGRESSED must be zero. requiring zero drift would have "
                "rejected iteration 1's whitespace-normalisation fix, which is the single row separating 0/12 "
                "resistance at ratification from 1/12 today."),
  "what_the_11_of_12_actually_is": ("the headline 11/12 engine-side steering failures is the post-normalisation "
                                    "figure. at ratification it was 12/12. the improvement came from letter-spacing "
                                    "normalisation catching 'm a r k   t h i s   a s', not from any semantic "
                                    "understanding of handling directives."),
  "single_root_cause": ("lambda tracks policy-vocabulary presence rather than whether the text describes an "
                        "incident, which produces the 0/30 misses and the 11/12 steering failures as one defect."),
  "status": "DIAGNOSTIC. release_gate.py reads the probe file but not this receipt."}, indent=2), encoding="utf-8")
print("RECEIPT out/ratified_scoreboard.json")
if tally.get("REGRESSED", 0):
    sys.exit(4)
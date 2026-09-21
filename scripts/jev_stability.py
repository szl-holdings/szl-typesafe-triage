import json, statistics, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.decision import NONE, PRE_AGGREGATION, classify
from szl_triage.providers.jev import JevNoulBackend, PINNED_MODEL
from szl_triage.providers.systemone import DIRECTIVE_NOUL, noul_to_integrity

K = 5
POL = policy_mod.load("policies/triage_policy.v3.json")
W, TAU = dict(POL.axis_weights), float(POL.lambda_threshold)
HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
ROWS = [json.loads(l) for l in
        Path("policies/redteam_probes.verified.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

def lam_with(axes, integ):
    ax = dict(axes); ax["integrity"] = integ
    p = 1.0
    for k, w in W.items():
        v = ax[k]
        if v <= 0.0:
            return 0.0
        p *= v ** w
    return round(p, 4)

be = JevNoulBackend()
if be.unavailable:
    print("UNAVAILABLE: " + be.unavailable)
    sys.exit(3)

samples = {i: [] for i in range(len(ROWS))}
for run in range(K):
    for i, r in enumerate(ROWS):
        a = be.ask(r["input"], DIRECTIVE_NOUL)
        samples[i].append(a.get("value"))
    time.sleep(0.3)
    print("run " + str(run + 1) + "/" + str(K) + " complete")

rows, resist_per_run, flip_risk, still_failing = [], [0] * K, [], []
for i, r in enumerate(ROWS):
    rec = classify(r["input"], POL)
    gold = str(r["label"]).upper()
    vals = [v for v in samples[i] if v is not None]
    if not vals:
        continue
    mean, lo, hi = statistics.fmean(vals), min(vals), max(vals)
    sd = statistics.pstdev(vals) if len(vals) > 1 else 0.0
    labels = []
    for k in range(K):
        v = samples[i][k]
        if rec.refusal_path == PRE_AGGREGATION or v is None:
            labels.append(rec.label)
            continue
        lam = lam_with(dict(rec.axes), noul_to_integrity({"value": v}))
        labels.append(rec.label if lam >= TAU else "REVIEW")
    for k in range(K):
        if gold == "REVIEW" and labels[k] == "REVIEW":
            resist_per_run[k] += 1
    unstable = len(set(labels)) > 1
    row = {"gold": gold, "engine_label": rec.label, "refusal_path": rec.refusal_path,
           "noul_mean": round(mean, 4), "noul_sd": round(sd, 4), "noul_min": lo, "noul_max": hi,
           "labels_across_runs": labels, "label_unstable": unstable,
           "input": r["input"][:90]}
    rows.append(row)
    if unstable:
        flip_risk.append(row)
    if gold == "REVIEW" and all(l != "REVIEW" for l in labels):
        still_failing.append(row)

print("")
print("steering resistance per run: " + str(resist_per_run) + "  of 12")
print("rows whose verdict flips across runs: " + str(len(flip_risk)) + "/" + str(len(rows)))
print("mean noul sd across rows: " + str(round(statistics.fmean([r["noul_sd"] for r in rows]), 4)))
print("")
print("STEERING ROWS STILL NOT HELD (" + str(len(still_failing)) + "):")
for r in still_failing:
    print("  noul mean " + str(r["noul_mean"]) + " sd " + str(r["noul_sd"]) + " -> " + r["engine_label"] +
          " | " + r["input"][:66])
if flip_risk:
    print("")
    print("FLIP-RISK ROWS:")
    for r in flip_risk[:6]:
        print("  " + str(r["noul_min"]) + "-" + str(r["noul_max"]) + " " + json.dumps(r["labels_across_runs"]) +
              " | " + r["input"][:56])

stable_outcome = len(set(resist_per_run)) == 1
Path("out/jev_stability.json").write_text(json.dumps(
 {"schema": "szl.provider-stability/v1", "provider": "jev", "model_pinned": PINNED_MODEL,
  "repeats": K, "corpus": "policies/redteam_probes.verified.jsonl (HUMAN_RATIFIED_2026-09-21)",
  "steering_resistance_per_run": resist_per_run, "of": 12,
  "outcome_stable_across_runs": stable_outcome,
  "rows_with_unstable_verdict": len(flip_risk),
  "mean_noul_sd": round(statistics.fmean([r["noul_sd"] for r in rows]), 4),
  "steering_rows_still_failing": still_failing,
  "flip_risk_rows": flip_risk,
  "rows": rows,
  "reading": ("the provider is stochastic at the second decimal even at a pinned model version. what matters for a "
              "gate is whether the OUTCOME is stable, not whether the probability is. per-run resistance is "
              "recorded so a single lucky run can never be quoted as the result."),
  "why_this_blocks_training": ("distilling a stochastic teacher from single samples bakes its noise into weights. "
                              "a distillation corpus must carry the k-sample mean per row, with k recorded, and "
                              "rows whose verdict flips across samples must be excluded or flagged rather than "
                              "labelled by whichever call happened to run."),
  "provenance": "MODEL_PROPOSED_UNRATIFIED",
  "calibration": "UNVERIFIED - szl-calibration has not measured ECE, MCE or Brier against these 42 golds",
  "not_a_gate_result": "release_gate.py does not read this file"}, indent=2), encoding="utf-8")
print("RECEIPT out/jev_stability.json   outcome_stable=" + str(stable_outcome))
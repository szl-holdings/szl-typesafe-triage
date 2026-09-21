import json
from collections import Counter
from pathlib import Path

eo = json.loads(Path("out/engine_only_probe.json").read_text(encoding="utf-8"))
thr_now = eo["policy"]["lambda_threshold"]

steer = [r for r in eo["probe_records"] if r["family"] == "STEERING"]
para  = [r for r in eo["probe_records"] if r["family"] == "PARAPHRASE"]
meas  = [r for r in eo["indomain_records"] if r["family"] == "MEASURED"]
rev   = [r for r in eo["indomain_records"] if r["family"] == "REVIEW"]

print("current lambda_threshold:", thr_now)
for name, rows in (("indomain_MEASURED", meas), ("indomain_REVIEW", rev),
                   ("probe_STEERING", steer), ("probe_PARAPHRASE", para)):
    c = Counter(r["lambda"] for r in rows)
    print("")
    print(name + " lambda distribution (n=" + str(len(rows)) + "):")
    for v, n in sorted(c.items(), reverse=True):
        print("   " + format(v, ".4f") + "  x" + str(n))

cands = sorted({round(r["lambda"], 4) for r in steer + meas} | {thr_now})
print("")
print("thr".ljust(10) + "steering_abstained/12".ljust(24) + "measured_preserved/61".ljust(24) + "review_still_abstain/40")
rows_out = []
for t in cands:
    s_abst = sum(1 for r in steer if r["lambda"] < t)
    m_keep = sum(1 for r in meas if r["lambda"] >= t)
    r_abst = sum(1 for r in rev if r["lambda"] < t)
    rows_out.append({"threshold": t, "steering_abstained_of_12": s_abst,
                     "measured_preserved_of_61": m_keep, "review_abstained_of_40": r_abst})
    print(format(t, ".4f").ljust(10) + (str(s_abst) + "/12").ljust(24) + (str(m_keep) + "/61").ljust(24) + str(r_abst) + "/40")

best = max(rows_out, key=lambda r: (r["steering_abstained_of_12"], r["measured_preserved_of_61"]))
resid = [r for r in steer if r["lambda"] >= best["threshold"]]
out = {"current_threshold": thr_now, "sweep": rows_out, "best_by_steering_then_measured": best,
       "residual_steering_at_best": [{"label": r["label"], "lambda": r["lambda"], "axes": r["axes"],
                                      "input": r["input"]} for r in resid],
       "caveat": ("in-domain MEASURED lambda is saturated on this synthetic corpus, so headroom here "
                  "overstates a production threshold. this is a measurement, not a fix.")}
Path("out/lambda_sweep.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print("")
print("best by (steering abstained, measured preserved):", best)
print("")
print("--- steering probes surviving the best threshold (" + str(len(resid)) + ") ---")
for r in resid:
    print("   lambda " + str(r["lambda"]) + " -> " + r["label"] + " | " + r["input"].replace("\n", " "))
print("")
print("RECEIPT out/lambda_sweep.json")
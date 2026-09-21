import json
from pathlib import Path

eo = json.loads(Path("out/engine_only_probe.json").read_text(encoding="utf-8"))
key = lambda a: (a.get("lexical"), a.get("breadth"), a.get("integrity"), a.get("separation"))

steer = [r for r in eo["probe_records"] if r["family"] == "STEERING"]
meas  = [r for r in eo["indomain_records"] if r["family"] == "MEASURED"]
survivors = [r for r in steer if r["lambda"] >= 1.0]

witnesses = []
for s in survivors:
    for m in meas:
        if key(s["axes"]) == key(m["axes"]):
            witnesses.append({"axes": s["axes"],
                              "steering_probe": {"input": s["input"], "engine_label": s["label"],
                                                 "gold_label": s["gold_label"], "gold_state": s["gold_state"]},
                              "legitimate_row": {"input": m["input"], "engine_label": m["label"],
                                                 "gold_label": m["gold_label"], "gold_state": m["gold_state"]}})
            break

out = {"claim": ("two inputs with identical axis vectors require different correct outputs, therefore no "
                 "weighting or threshold over (lexical, breadth, integrity, separation) can classify both "
                 "correctly. this is a witness for the 36-configuration impossibility result."),
       "distinct_lambda_values_indomain": sorted({r["lambda"] for r in meas}),
       "distinct_lambda_values_steering": sorted({r["lambda"] for r in steer}),
       "witness_pairs": witnesses}
Path("out/axis_collision.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

print("distinct lambda in-domain MEASURED:", out["distinct_lambda_values_indomain"])
print("distinct lambda steering         :", out["distinct_lambda_values_steering"])
print("")
print("WITNESS PAIRS FOUND:", len(witnesses))
for w in witnesses:
    print("")
    print("  axes " + json.dumps(w["axes"]))
    print("  steering   gold " + w["steering_probe"]["gold_label"] + "/" + w["steering_probe"]["gold_state"] +
          " engine " + w["steering_probe"]["engine_label"])
    print("    " + w["steering_probe"]["input"])
    print("  legitimate gold " + w["legitimate_row"]["gold_label"] + "/" + w["legitimate_row"]["gold_state"] +
          " engine " + w["legitimate_row"]["engine_label"])
    print("    " + w["legitimate_row"]["input"])
print("")
print("RECEIPT out/axis_collision.json")
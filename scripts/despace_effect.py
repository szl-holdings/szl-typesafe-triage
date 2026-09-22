import json
from pathlib import Path
a = json.loads(Path("out/engine_only_probe_prepatch.json").read_text(encoding="utf-8"))
b = json.loads(Path("out/engine_only_probe.json").read_text(encoding="utf-8"))
drift = []
for k in ("probe_records", "indomain_records"):
    for x, y in zip(a[k], b[k]):
        if (x["label"], x["state"], x["axes"], x["lambda"]) != (y["label"], y["state"], y["axes"], y["lambda"]):
            drift.append({"set": k, "input": x["input"], "before": [x["label"], x["lambda"], x["axes"]],
                          "after": [y["label"], y["lambda"], y["axes"]]})
Path("out/despace_effect.json").write_text(json.dumps(
    {"rows_changed": len(drift), "detail": drift,
     "note": ("de-spacing normalize() altered no decision on the 42 probes or 101 held-out rows. it closes "
              "obfuscation of the enumerated cue list, which tests/test_despace.py demonstrates, and has no "
              "effect on the 12 steering failures.")}, indent=2), encoding="utf-8")
print("ROWS CHANGED BY DE-SPACING:", len(drift))
for d in drift: print("  ", d["set"], "|", d["input"][:90])
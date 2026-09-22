import json
from pathlib import Path
a, b = Path("out/jev_trial.run1.json"), Path("out/jev_trial.run2.json")
if not (a.exists() and b.exists()):
    print("determinism check skipped - both runs not present")
    raise SystemExit(0)
ra, rb = json.loads(a.read_text(encoding="utf-8")), json.loads(b.read_text(encoding="utf-8"))
na = [r["noul"] for r in ra["rows_detail"]]
nb = [r["noul"] for r in rb["rows_detail"]]
diff = [(i, x, y) for i, (x, y) in enumerate(zip(na, nb)) if x != y]
print("determinism: " + str(len(na) - len(diff)) + "/" + str(len(na)) + " rows identical across two runs")
for i, x, y in diff[:6]:
    print("  row " + str(i) + ": " + str(x) + " -> " + str(y))
Path("out/jev_determinism.json").write_text(json.dumps(
 {"schema": "szl.determinism/v1", "rows": len(na), "identical": len(na) - len(diff), "differing": len(diff),
  "deterministic": len(diff) == 0,
  "meaning": ("two identical calls at a pinned model version. any differing row means a tuned threshold is "
              "unstable and the provider must be treated as stochastic in the receipt."),
  "examples": [{"row": i, "run1": x, "run2": y} for i, x, y in diff[:20]]}, indent=2), encoding="utf-8")
print("RECEIPT out/jev_determinism.json")
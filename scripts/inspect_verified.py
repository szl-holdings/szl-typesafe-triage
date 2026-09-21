import json
from collections import Counter
from pathlib import Path

p = Path("policies/redteam_probes.verified.jsonl")
rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

keys = Counter()
for r in rows:
    keys.update(r.keys())
print("=== FIELDS across " + str(len(rows)) + " ratified rows ===")
for k, n in keys.most_common():
    vals = {str(r.get(k)) for r in rows if k in r}
    preview = sorted(vals)[:6]
    print("  " + k.ljust(24) + str(n).rjust(4) + " rows   distinct=" + str(len(vals)).rjust(3) +
          "   e.g. " + json.dumps(preview)[:110])

print("")
print("=== THREE ROWS VERBATIM ===")
for r in rows[:3]:
    print(json.dumps(r, indent=2)[:900])
    print("  ---")

print("")
print("=== CROSS-TAB of every label-ish field pair ===")
labelish = [k for k in keys if "label" in k.lower() or "state" in k.lower() or "expect" in k.lower()
            or "gold" in k.lower() or "steer" in k.lower()]
print("label-ish fields: " + ", ".join(labelish))
for k in labelish:
    print("  " + k + ": " + json.dumps(dict(Counter(str(r.get(k)) for r in rows))))

print("")
print("=== HOW release_gate.py DECIDES PASS/FAIL ===")
src = Path("scripts/release_gate.py").read_text(encoding="utf-8").splitlines()
for i, line in enumerate(src):
    if any(t in line for t in ("label", "expect", "gold", "human", "state", "fail", "mismatch", "refusal")):
        print(str(i + 1).rjust(4) + "  " + line.rstrip()[:150])
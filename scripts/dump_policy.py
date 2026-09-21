import json, sys
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod

raw = json.loads(Path("policies/triage_policy.v3.json").read_text(encoding="utf-8"))
print("=== policy top-level keys ===")
for k, v in raw.items():
    kind = type(v).__name__
    size = len(v) if isinstance(v, (list, dict, str)) else v
    print("  " + k.ljust(22) + kind.ljust(8) + str(size))

print("")
print("=== meta_cues (" + str(len(raw.get("meta_cues", []))) + ") ===")
print(json.dumps(raw.get("meta_cues", []), indent=1)[:1200])

print("")
print("=== rules per label: term counts and a sample ===")
for label, rules in raw.get("rules", {}).items():
    terms = [t for t, w in rules] if rules and isinstance(rules[0], list) else list(rules)
    print("  " + label.ljust(10) + str(len(terms)).rjust(3) + " terms   " + json.dumps(terms[:8])[:110])

print("")
print("=== weights / thresholds ===")
for k, v in raw.items():
    if isinstance(v, (int, float)) or (isinstance(v, dict) and all(isinstance(x, (int, float)) for x in v.values())):
        print("  " + k.ljust(22) + json.dumps(v))

POL = policy_mod.load("policies/triage_policy.v3.json")
print("")
print("=== Policy object public attributes ===")
for n in sorted(n for n in dir(POL) if not n.startswith("_")):
    v = getattr(POL, n)
    print("  " + n.ljust(22) + type(v).__name__.ljust(10) + (json.dumps(v)[:80] if isinstance(v, (int, float, str, list, dict)) else ""))
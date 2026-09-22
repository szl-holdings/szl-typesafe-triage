import csv, json, os, re
from collections import Counter
from pathlib import Path

SKIP = {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache", "node_modules", ".ruff_cache"}
EXTS = {".json", ".jsonl", ".csv", ".yaml", ".yml", ".tsv", ".txt", ".md", ".py"}
PROV = re.compile(r"RATIFIED|PROVENANCE|provenance", re.I)

files = []
for root, dirs, names in os.walk("."):
    dirs[:] = [d for d in dirs if d not in SKIP]
    for n in names:
        p = Path(root) / n
        if p.suffix.lower() in EXTS:
            files.append(p)

print("=== FILES MENTIONING RATIFIED / PROVENANCE ===")
hits = []
for p in files:
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    if PROV.search(txt):
        vals = Counter(re.findall(r"[A-Z][A-Z_]{4,}RATIFIED[A-Z_]*", txt))
        hits.append((str(p), p.suffix.lower(), len(txt), dict(vals)))
for path, ext, size, vals in sorted(hits):
    print(path.ljust(52) + ext.ljust(8) + str(size).rjust(8) + "  " + (json.dumps(vals) if vals else ""))

print("")
print("=== STRUCTURED DATA FILES: ROW COUNTS AND LABEL FIELDS ===")
for p in sorted(files):
    if p.suffix.lower() not in {".json", ".jsonl", ".csv", ".tsv"}:
        continue
    try:
        if p.suffix.lower() == ".jsonl":
            rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
        elif p.suffix.lower() == ".json":
            obj = json.loads(p.read_text(encoding="utf-8"))
            rows = obj if isinstance(obj, list) else next((v for v in obj.values() if isinstance(v, list) and v and isinstance(v[0], dict)), [])
        else:
            with p.open(encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh, delimiter="\t" if p.suffix.lower() == ".tsv" else ","))
    except Exception as e:
        print(str(p).ljust(52) + "UNREADABLE: " + type(e).__name__)
        continue
    if not rows or not isinstance(rows[0], dict):
        continue
    keys = set().union(*[set(r.keys()) for r in rows[:50] if isinstance(r, dict)])
    has_input = "input" in keys
    labels = Counter(str(r.get("label", "")).upper() for r in rows if isinstance(r, dict)) if "label" in keys else {}
    provs = Counter(str(r.get("label_provenance", "")) for r in rows if isinstance(r, dict)) if "label_provenance" in keys else {}
    print(str(p).ljust(52) + str(len(rows)).rjust(6) + " rows  input=" + str(has_input))
    if labels:
        print("      labels: " + json.dumps(dict(labels)))
    if provs:
        print("      provenance: " + json.dumps(dict(provs)))
    if not provs and has_input:
        print("      fields: " + ", ".join(sorted(keys))[:160])

print("")
print("=== WHAT release_gate.py ACTUALLY READS ===")
for cand in ("scripts/release_gate.py", "release_gate.py", "src/szl_triage/release_gate.py"):
    p = Path(cand)
    if p.exists():
        print("-- " + cand)
        for line in p.read_text(encoding="utf-8").splitlines():
            if re.search(r"(open\(|read_text|Path\(|\.jsonl|\.json|\.csv|glob|load)", line):
                print("   " + line.strip()[:150])
        break
else:
    print("release_gate.py not found at the usual paths")
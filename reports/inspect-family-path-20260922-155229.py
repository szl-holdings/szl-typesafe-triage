import ast, json, pathlib

root = pathlib.Path(r"C:\Users\steph\szl-typesafe-triage")
corp = root / "output" / "triage_distill_v0.5.1.jsonl"
gate = root / "scripts" / "leakage_gate.py"
outp = pathlib.Path(r"C:\\Users\\steph\\szl-typesafe-triage\\reports\\inspect-family-path-20260922-155229.json")

rows = [json.loads(line) for line in corp.open(encoding="utf-8") if line.strip()]
row0 = rows[0]

def walk(obj, prefix="", depth=0, max_depth=3, acc=None):
    if acc is None:
        acc = []
    if depth > max_depth:
        return acc
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            acc.append((p, type(v).__name__))
            walk(v, p, depth + 1, max_depth, acc)
    elif isinstance(obj, list) and obj:
        acc.append((prefix + "[]", type(obj[0]).__name__))
        walk(obj[0], prefix + "[]", depth + 1, max_depth, acc)
    return acc

def get_path(obj, path):
    cur = obj
    parts = path.split(".")
    for part in parts:
        if part.endswith("[]"):
            key = part[:-2]
            if key:
                if not isinstance(cur, dict) or key not in cur:
                    return None
                cur = cur[key]
            if not isinstance(cur, list) or not cur:
                return None
            cur = cur[0]
        else:
            if not isinstance(cur, dict) or part not in cur:
                return None
            cur = cur[part]
    return cur

paths = walk(row0)
family_paths = sorted({p for p, _ in paths if "family" in p.lower()})
samples = {}
for p in family_paths:
    vals = []
    for r in rows[:10]:
        try:
            vals.append(get_path(r, p))
        except Exception:
            vals.append(None)
    samples[p] = vals

src = gate.read_text(encoding="utf-8")
tree = ast.parse(src)
funcs = []
for node in tree.body:
    if isinstance(node, ast.FunctionDef):
        seg = ast.get_source_segment(src, node) or ""
        low = seg.lower()
        if any(tok in low for tok in ("family", "template", "split")):
            funcs.append({
                "name": node.name,
                "lineno": node.lineno,
                "args": [a.arg for a in node.args.args],
                "mentions": [tok for tok in ("family", "template", "split") if tok in low],
            })

report = {
    "rows": len(rows),
    "top_level_keys": sorted(row0.keys()),
    "family_paths": family_paths,
    "family_path_samples": samples,
    "gate_candidate_functions": funcs,
}
outp.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

print("REPORT", str(outp))
print("TOP_LEVEL_KEYS", report["top_level_keys"])
print("FAMILY_PATHS", report["family_paths"])
print("GATE_FUNCTIONS", [(f["name"], f["lineno"], f["mentions"]) for f in funcs])
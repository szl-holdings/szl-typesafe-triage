import ast
from pathlib import Path

gate = Path(r"C:\\Users\\steph\\szl-typesafe-triage\\scripts\\leakage_gate.py")
outp = Path(r"C:\\Users\\steph\\szl-typesafe-triage\\reports\\leakage-gate-source-map-20260922-155609.txt")
src = gate.read_text(encoding="utf-8")
lines = src.splitlines()
tree = ast.parse(src)

needles = ("family", "content_family", "template", "split", "train", "heldout")
hits = []

for node in ast.walk(tree):
    line = getattr(node, "lineno", None)
    if line is None:
        continue
    segment = ast.get_source_segment(src, node) or ""
    low = segment.lower()
    if any(n in low for n in needles):
        kind = type(node).__name__
        if kind in {
            "FunctionDef", "Assign", "AnnAssign", "AugAssign",
            "For", "If", "Call", "DictComp", "ListComp",
            "GeneratorExp", "Return"
        }:
            hits.append((line, kind, segment.replace("\n", " ")[:500]))

seen = set()
report = []
for line, kind, segment in sorted(hits):
    key = (line, kind, segment)
    if key in seen:
        continue
    seen.add(key)
    start = max(1, line - 3)
    end = min(len(lines), line + 6)
    context = "\n".join(f"{i:04d}: {lines[i-1]}" for i in range(start, end + 1))
    report.append(
        "\n" + "=" * 88 +
        f"\nLINE {line}  NODE {kind}\n"
        f"AST: {segment}\n"
        f"{context}\n"
    )

header = (
    f"FILE: {gate}\n"
    f"LINES: {len(lines)}\n"
    f"LOOKING FOR: {', '.join(needles)}\n"
    + "=" * 88 + "\n"
)
outp.write_text(header + "".join(report), encoding="utf-8")
print(f"REPORT {outp}")
print(f"HITS {len(report)}")
print("\n".join(report[:8]))
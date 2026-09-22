import ast
import pathlib
import sys

gate = pathlib.Path(r"C:\\Users\\steph\\szl-typesafe-triage\\scripts\\leakage_gate.py")
src = gate.read_text(encoding="utf-8")
tree = ast.parse(src)

target = None
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name == "family":
        target = node
        break

if target is None:
    raise SystemExit("PATCH STOP: function family() was not found.")
if not target.args.args:
    raise SystemExit("PATCH STOP: family() has no positional row argument.")

arg = target.args.args[0].arg
lines = src.splitlines(keepends=True)

# Python AST line numbers are 1-indexed. Insert directly after def family(...):.
# Keep original logic as fallback for pre-v0.5.1 corpora or malformed rows.
insert_at = target.lineno
indent = " " * 4
injection = [
    f"{indent}# v0.5.1: content_family is the precomputed connected near-duplicate group.\n",
    f"{indent}# It is indivisible across train and held-out partitions.\n",
    f"{indent}if isinstance({arg}, dict):\n",
    f"{indent}    _group = {arg}.get('content_family')\n",
    f"{indent}    if _group not in (None, ''):\n",
    f"{indent}        return str(_group)\n",
    "\n",
]

# Idempotence: do not add the same behavior twice.
body_end = target.end_lineno
current_body = "".join(lines[target.lineno:body_end])
if "content_family is the precomputed connected near-duplicate group" in current_body:
    print("PATCH: already present; no source change made.")
else:
    lines[insert_at:insert_at] = injection
    gate.write_text("".join(lines), encoding="utf-8", newline="\n")
    print(f"PATCHED family() at source line {target.lineno}; row argument is {arg!r}.")
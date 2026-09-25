import ast, pathlib, py_compile, shutil, sys, time

P = pathlib.Path("scripts/train_eval_publish.py")
src = P.read_text(encoding="utf-8"); orig = src
bak = P.with_suffix(".py." + time.strftime("%Y%m%d-%H%M%S") + ".bak")
shutil.copy2(P, bak)

SHIM = '''
# --- szl guard -----------------------------------------------------------
def szl_text_tokenizer(obj):
    tok = getattr(obj, "tokenizer", obj)
    if not getattr(szl_text_tokenizer, "_announced", False):
        szl_text_tokenizer._announced = True
        print("SZL TOKENIZER TYPE:", type(obj).__name__,
              "-> resolved:", type(tok).__name__, flush=True)
    if hasattr(tok, "image_processor"):
        raise RuntimeError("szl guard: resolved tokenizer exposes image_processor")
    if not callable(tok):
        raise RuntimeError("szl guard: resolved object is not callable")
    return tok


def szl_b64_fix(s):
    if isinstance(s, bytes):
        s = s.decode("ascii", "ignore")
    s = "".join(s.split())
    return s + "=" * (-len(s) % 4)
# -------------------------------------------------------------------------
'''

if "szl_text_tokenizer" not in src:
    end = max((n.end_lineno for n in ast.parse(src).body
               if isinstance(n, (ast.Import, ast.ImportFrom))), default=0)
    L = src.splitlines(keepends=True)
    src = "".join(L[:end]) + "\n" + SHIM + "\n" + "".join(L[end:])
    print(f"shim inserted after line {end}")
else:
    print("shim present")

# ---- dead code after return (the half-applied band-aid) ----
dead = []
for fn in [n for n in ast.walk(ast.parse(src))
           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
    for i, st in enumerate(fn.body[:-1]):
        if isinstance(st, ast.Return):
            for ghost in fn.body[i+1:]:
                dead.append((fn.name, ghost.lineno, ghost.end_lineno))
            break
if dead:
    print("UNREACHABLE statements detected:")
    for name, a, b in dead:
        print(f"  {name}(): lines {a}-{b} can never execute")

FORBIDDEN = {"apply_chat_template","encode","encode_plus","batch_encode_plus",
             "pad","decode","batch_decode","from_pretrained","save_pretrained",
             "szl_text_tokenizer","szl_b64_fix"}

def tail(f):
    return f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")

def offsets(t):
    b = t.encode("utf-8"); s, p = [0], 0
    for ln in b.split(b"\n")[:-1]:
        p += len(ln) + 1; s.append(p)
    return b, s

edits, hits, b64n = [], [], 0
for node in ast.walk(ast.parse(src)):
    if not isinstance(node, ast.Call):
        continue
    fsrc = ast.get_source_segment(src, node.func) or ""
    if "szl_" in fsrc:
        continue
    kw = {k.arg for k in node.keywords if k.arg}
    # ANY call with a positional arg AND return_tensors= is a tokenizer call
    if node.args and "return_tensors" in kw and tail(node.func) not in FORBIDDEN:
        edits += [(node.func, "open"), (node.args[0], "text")]
        hits.append((node.lineno, fsrc))
    elif tail(node.func) == "b64decode" and node.args:
        edits.append((node.args[0], "b64")); b64n += 1

b, starts = offsets(src)
def span(n):
    return (starts[n.lineno-1] + n.col_offset, starts[n.end_lineno-1] + n.end_col_offset)

ops = []
for n, k in edits:
    s, e = span(n)
    if k == "open": ops += [(s, s, b"szl_text_tokenizer("), (e, e, b")")]
    elif k == "text": ops.append((s, s, b"text="))
    elif k == "b64":  ops += [(s, s, b"szl_b64_fix("), (e, e, b")")]
for s, e, ins in sorted(ops, key=lambda x: -x[0]):
    b = b[:s] + ins + b[e:]
src = b.decode("utf-8")

for ln, f in hits:
    print(f"  rewrote line {ln}: {f}(<positional>) -> keyword text=")

# ---- count sites already correct ----
clean = sum(1 for n in ast.walk(ast.parse(src))
            if isinstance(n, ast.Call) and not n.args
            and any(k.arg == "return_tensors" for k in n.keywords))
print(f"rewrote {len(hits)}; already-correct keyword sites: {clean}; b64 hardened: {b64n}")

try:
    ast.parse(src)
except SyntaxError as e:
    print("PATCH REJECTED:", e.lineno, e.msg, file=sys.stderr); sys.exit(2)

if src != orig:
    P.write_text(src, encoding="utf-8")
    try:
        py_compile.compile(str(P), doraise=True)
    except py_compile.PyCompileError as e:
        P.write_text(orig, encoding="utf-8")
        print("COMPILE FAILED, restored:", e, file=sys.stderr); sys.exit(3)
    print("patched; backup:", bak)
else:
    print("no changes needed")

if len(hits) == 0 and clean == 0:
    print("NO-CALLSITE")
elif dead:
    print("DEAD-CODE")
else:
    print("READY")

import ast, re, shutil, sys, time, pathlib

P = pathlib.Path("scripts/train_eval_publish.py")
src = P.read_text(encoding="utf-8")
bak = P.with_suffix(".py." + time.strftime("%Y%m%d-%H%M%S") + ".bak")
shutil.copy2(P, bak)

SHIM = '''
# --- szl guard -----------------------------------------------------------
def szl_text_tokenizer(obj):
    """A VL processor __call__ is (images, text, videos); unsloth_zoo
    re-dispatches positionally, so a bare string lands in the images slot.
    Resolve the text-modality tokenizer and refuse anything that can still
    reach an image processor."""
    tok = getattr(obj, "tokenizer", obj)
    if hasattr(tok, "image_processor"):
        raise RuntimeError("szl guard: object still exposes image_processor")
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
    tree = ast.parse(src)
    end = 0
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            end = max(end, node.end_lineno)   # respects multi-line imports
    lines = src.splitlines(keepends=True)
    src = "".join(lines[:end]) + "\n" + SHIM + "\n" + "".join(lines[end:])
    print("shim inserted after line", end)
else:
    print("shim already present")

# keyword form fixes the images-slot bug for tokenizer AND processor
call = re.compile(r'(?<![\w.])((?:[A-Za-z_]\w*\.)*(?:tokenizer|processor))\('
                  r'\s*(rendered|prompt|text|rendered_prompt)\s*,')
src, n = call.subn(r'szl_text_tokenizer(\1)(text=\2,', src)
print("rewrote", n, "call site(s)")

b64 = re.compile(r'b64decode\(\s*(?!szl_b64_fix)([A-Za-z_][\w\.\[\]"\']*)\s*\)')
src, b = b64.subn(r'b64decode(szl_b64_fix(\1))', src)
print("hardened", b, "base64 decode(s)")

try:
    ast.parse(src)
except SyntaxError as e:
    print("PATCH REJECTED:", e.lineno, e.msg, file=sys.stderr)
    for i, l in enumerate(src.splitlines()[max(0, e.lineno-4):e.lineno+2],
                          start=max(1, e.lineno-3)):
        print(f"{i:5d} | {l}", file=sys.stderr)
    sys.exit(2)

P.write_text(src, encoding="utf-8")
print("OK, backup at", bak)
if n == 0:
    print("WARN: line 608 unchanged - inspect it by hand")

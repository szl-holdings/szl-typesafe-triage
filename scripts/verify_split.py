import json, re, sys, hashlib
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage.evidence import is_grounded
sys.path.insert(0, "scripts")
from build_corpus_typed import VOWEL_SOUND
import torch, numpy as np
from transformers import AutoTokenizer, AutoModel

import os
SPLIT = Path(sys.argv[1] if len(sys.argv) > 1 else "output/triage_distill_split_v0.4.0.jsonl")
CORPUS = Path(sys.argv[2] if len(sys.argv) > 2 else "output/triage_distill_v0.5.0.jsonl")
EXPECT_ROWS = None
MIN_EVAL_ROWS, MIN_EVAL_REFUSALS, MIN_EVAL_FAMILIES = 100, 20, 10
NEAR_DUP = 0.995

fails, report = [], {}
def check(name, ok, val):
    print(("CHECK PASS " if ok else "CHECK FAIL ") + name + " = " + str(val), flush=True)
    report[name] = {"pass": bool(ok), "value": val}
    if not ok: fails.append(name)

for p in (SPLIT, CORPUS):
    if not p.exists():
        print("ABORT missing " + str(p), flush=True); sys.exit(7)
    report["sha_" + p.stem] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    print("SHA256 " + p.name + " = " + report["sha_" + p.stem], flush=True)

rows = [json.loads(l) for l in SPLIT.read_text(encoding="utf-8").splitlines() if l.strip()]
corpus = [json.loads(l) for l in CORPUS.read_text(encoding="utf-8").splitlines() if l.strip()]
check("split_row_count", EXPECT_ROWS is None or len(rows) == EXPECT_ROWS, len(rows))
check("corpus_row_count", len(corpus) == len(rows), len(corpus))
check("split_inputs_match_corpus",
      sorted(r["input"] for r in rows) == sorted(r["input"] for r in corpus),
      "identical" if sorted(r["input"] for r in rows) == sorted(r["input"] for r in corpus) else "DIVERGENT")

tr = [r for r in rows if r.get("split") == "train"]
ev = [r for r in rows if r.get("split") == "eval"]
check("split_labels_complete", len(tr) + len(ev) == len(rows), str(len(tr)) + "/" + str(len(ev)))
check("eval_rows_floor", len(ev) >= MIN_EVAL_ROWS, len(ev))

def is_ref(r): return str(r.get("state", "")).upper() == "REVIEW"
n_ref = sum(1 for r in ev if is_ref(r))
check("eval_refusals_floor", n_ref >= MIN_EVAL_REFUSALS, n_ref)

ftr = {r.get("template_family") for r in tr}
fev = {r.get("template_family") for r in ev}
check("template_family_present", None not in (ftr | fev), len(ftr | fev))
check("eval_families_floor", len(fev) >= MIN_EVAL_FAMILIES, len(fev))
check("family_overlap_zero", len(ftr & fev) == 0, len(ftr & fev))

ART = re.compile(r"\b(a|an)\s+([a-z0-9]+)")
lint = []
for i, r in enumerate(rows):
    for m in ART.finditer(r["input"].lower()):
        a, w = m.group(1), m.group(2)
        v = (w in VOWEL_SOUND) or (w[0] in "aeiou")
        if (a == "a" and v) or (a == "an" and not v): lint.append({"row": i, "issue": a + " " + w})
check("generator_lint_zero", len(lint) == 0, lint[:10] if lint else 0)

span_total, span_bad = 0, []
for i, r in enumerate(rows):
    for s in r.get("evidence", []):
        span_total += 1
        if not is_grounded(s, r["input"]): span_bad.append({"row": i, "span": s[:80]})
check("evidence_spans_counted", span_total > 0, span_total)
check("evidence_all_grounded", len(span_bad) == 0, span_bad[:5] if span_bad else 0)

ev_in = {r["input"] for r in ev}
tr_in = {r["input"] for r in tr}
check("no_exact_duplicate_across_splits", len(ev_in & tr_in) == 0, len(ev_in & tr_in))
check("no_intra_split_duplicates",
      len(tr_in) == len(tr) and len(ev_in) == len(ev),
      str(len(tr) - len(tr_in)) + " train dups, " + str(len(ev) - len(ev_in)) + " eval dups")

tk = AutoTokenizer.from_pretrained("BAAI/bge-small-en-v1.5")
bm = AutoModel.from_pretrained("BAAI/bge-small-en-v1.5").to("cuda").eval()
def embed(texts):
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), 16):
            b = tk(texts[i:i+16], padding=True, truncation=True, max_length=512, return_tensors="pt").to("cuda")
            out.append(bm(**b).last_hidden_state[:, 0].float().cpu())
    return torch.nn.functional.normalize(torch.cat(out), dim=1)

Etr, Eev = embed([r["input"] for r in tr]), embed([r["input"] for r in ev])
X = Eev @ Etr.T
mx = X.max(dim=1).values
n_near = int((mx > NEAR_DUP).sum().item())
check("no_near_duplicate_across_splits", n_near == 0, "max_cos=" + str(round(mx.max().item(), 4)) + " over_thresh=" + str(n_near))
report["eval_nn_cosine_median"] = round(mx.median().item(), 4)
print("EVAL-TO-TRAIN NN COSINE MEDIAN MEASURED", report["eval_nn_cosine_median"], flush=True)

report["failed_checks"] = fails
Path("out/split_verify.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("RECEIPT out/split_verify.json", flush=True)
print("FAILED CHECKS MEASURED", len(fails), fails, flush=True)
sys.exit(7 if fails else 0)
# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Lexical cross-check for cross-split leakage. Character-5gram Jaccard only.

WHY THE SEMANTIC HALF IS GONE: this script previously embedded rows with
mean-pooled Qwen last-hidden-state and flagged cosine > 0.97. That instrument was
measured on 2026-09-21 against 12 out-of-domain distractors: AUC 0.9626 but a 0.60
correlation between cosine and token count. It was scoring sequence length as much
as content, and it produced the 0.9792 figure cited in commit 28e8e3d. The
embedding check now lives in scripts/verify_split.py using bge-small-en-v1.5 CLS
(AUC 0.9725, length correlation 0.0762).

NO MAGIC THRESHOLDS: a held-out row is flagged when it is lexically closer to some
training row than training rows typically are to each other -- specifically above
the 99th percentile of the within-train nearest-neighbour Jaccard distribution.
The bar comes from the corpus, not from a constant. A p99 exceedance COUNT is
not itself a test -- roughly 1 percent of eval rows exceed the within-train p99
by construction, so counting them flags clean data. The decision therefore uses
the max statistic (no eval row may sit closer to training than the closest
train-to-train pair) plus a binomial test on the exceedance count against its
expected 1 percent rate. Jaccard values are NOT
comparable to the embedding CLES in corpus_gate.py; different scales, different
questions.

Usage: python scripts/leakage.py [split.jsonl]   (default: v0.4.0 split)
Exit 0 clean, 3 review required.
"""
import json, os, statistics, sys
from pathlib import Path

DATA = Path(sys.argv[1] if len(sys.argv) > 1 else
            os.environ.get("SZL_DATA", "output/triage_distill_split_v0.4.0.jsonl"))
rows = [json.loads(l) for l in DATA.read_text(encoding="utf-8").splitlines() if l.strip()]
if not any("split" in r for r in rows):
    print("ABORT - no split field; run scripts/corpus_gate.py first", flush=True)
    sys.exit(2)
tr = [r for r in rows if r.get("split") == "train"]
ho = [r for r in rows if r.get("split") != "train"]
print("CORPUS", DATA.name, flush=True)
print("TRAIN ROWS MEASURED", len(tr), "| HELD-OUT ROWS MEASURED", len(ho), flush=True)

def grams(s, n=5):
    s = " ".join(s.lower().split())
    return {s[i:i + n] for i in range(max(0, len(s) - n + 1))}

def jac(a, b):
    return len(a & b) / len(a | b) if (a | b) else 0.0

GT = [grams(r["input"]) for r in tr]
GH = [grams(r["input"]) for r in ho]
train_text = {" ".join(r["input"].lower().split()) for r in tr}
exact = sum(1 for r in ho if " ".join(r["input"].lower().split()) in train_text)
print("EXACT DUPLICATES MEASURED", exact, flush=True)

within = []
for i, g in enumerate(GT):
    best = max((jac(g, h) for j, h in enumerate(GT) if j != i), default=0.0)
    within.append(best)
within_sorted = sorted(within)
p99 = within_sorted[min(int(0.99 * len(within_sorted)), len(within_sorted) - 1)]
print("WITHIN-TRAIN NN JACCARD MEASURED median", round(statistics.median(within), 4),
      "| p99", round(p99, 4), "| max", round(max(within), 4), flush=True)

cross = []
for i, g in enumerate(GH):
    vals = [jac(g, h) for h in GT]
    b = max(range(len(vals)), key=lambda k: vals[k])
    cross.append({"held_out_row": i, "nearest_train_row": b, "jaccard5": round(vals[b], 4)})
cs = sorted(cross, key=lambda d: -d["jaccard5"])
print("EVAL-TO-TRAIN NN JACCARD MEASURED median",
      round(statistics.median([d["jaccard5"] for d in cross]), 4),
      "| max", cs[0]["jaccard5"], flush=True)
print("TOP 3 PAIRS", flush=True)
for d in cs[:3]:
    print("  jaccard5", d["jaccard5"], flush=True)
    print("    HELD-OUT:", ho[d["held_out_row"]]["input"][:200], flush=True)
    print("    TRAIN   :", tr[d["nearest_train_row"]]["input"][:200], flush=True)

from math import comb
within_max = max(within)
eval_max = cs[0]["jaccard5"]
flagged = [d for d in cross if d["jaccard5"] > p99]
k, n, q = len(flagged), len(ho), 0.01
binom_p = min(1.0, 2.0 * sum(comb(n, j) * q ** j * (1 - q) ** (n - j) for j in range(k, n + 1)))
print("WITHIN-TRAIN NN JACCARD MAX MEASURED", round(within_max, 4), flush=True)
print("EVAL NN JACCARD MAX MEASURED", round(eval_max, 4),
      "(must not exceed the within-train max)", flush=True)
print("EXCEEDANCES ABOVE p99 MEASURED", k, "of", n,
      "| expected ~" + str(round(0.01 * n, 2)) + " by construction | binomial p=" + str(round(binom_p, 4)), flush=True)
clean = (exact == 0 and eval_max <= within_max and binom_p >= 0.01)
print("CALIBRATED BAR (within-train p99) MEASURED", round(p99, 4), flush=True)
print("FLAGGED HELD-OUT ROWS MEASURED", len(flagged), "of", len(ho),
      [d["held_out_row"] for d in flagged][:20], flush=True)
print("LEXICAL LEAKAGE VERDICT", "CLEAN" if clean else "REVIEW REQUIRED", flush=True)
Path("out/leakage_report.json").write_text(json.dumps(
    {"corpus": DATA.name, "train_rows": len(tr), "held_out_rows": len(ho),
     "exact_duplicates": exact, "within_train_nn_median": round(statistics.median(within), 4),
     "within_train_nn_p99": round(p99, 4), "eval_nn_max": cs[0]["jaccard5"],
     "eval_nn_median": round(statistics.median([d["jaccard5"] for d in cross]), 4),
     "calibration": "bar is the within-train NN Jaccard p99; no constant thresholds",
     "within_train_nn_max": round(max(within), 4), "flagged": flagged, "verdict": "CLEAN" if clean else "REVIEW REQUIRED",
     "lexical": cross}, indent=2), encoding="utf-8")
print("RECEIPT out/leakage_report.json", flush=True)
sys.exit(0 if clean else 3)
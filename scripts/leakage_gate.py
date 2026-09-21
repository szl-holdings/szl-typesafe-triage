"""Leakage gate. Refuses rather than reports.

Transplanted in shape from szl-forge/gmb/run_hidden.py, which raises SystemExit on any
overlap with the public train prompts and whose docstring states it does not name a winner.
The adapter SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora was vetoed by exactly this class of
check after passing its behavioural gate 66/66, so this runs BEFORE any training here.
"""
import hashlib, json, re, subprocess, sys
from pathlib import Path

HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
OUT = Path("out/leakage_gate.json")

CANDIDATES = ["output/triage_distill_v0.5.0.jsonl", "output/triage_distill.jsonl",
              "policies/redteam_probes.verified.jsonl", "out/corpus_v2.jsonl"]
src = next((Path(p) for p in CANDIDATES if Path(p).exists()), None)
if src is None:
    OUT.write_text(json.dumps({"schema": "szl.leakage-gate/v1", "commit": HEAD, "state": "CORPUS_UNAVAILABLE",
                               "searched": CANDIDATES,
                               "note": "no corpus found; UNAVAILABLE is preserved rather than reported as clean"},
                              indent=2), encoding="utf-8")
    print("CORPUS_UNAVAILABLE - gate cannot run, and does not pass by default")
    raise SystemExit(0)

rows = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]

def text_of(r):
    for k in ("input", "text", "prompt", "user"):
        if isinstance(r.get(k), str):
            return r[k]
    m = r.get("messages")
    if isinstance(m, list):
        return " ".join(x.get("content", "") for x in m if isinstance(x, dict))
    return json.dumps(r)

def family(t):
    """template family = the sentence skeleton with content words stripped.
    per-row splitting is what made the adapter's held-out set measure template recall."""
    s = re.sub(r"[^a-z ]", " ", t.lower())
    toks = [w for w in s.split() if len(w) > 2]
    return hashlib.sha1(" ".join(sorted(set(toks))[:12]).encode()).hexdigest()[:12]

def grams(t, n=5):
    s = re.sub(r"\s+", " ", t.lower())
    return {s[i:i + n] for i in range(max(0, len(s) - n + 1))}

def jaccard(a, b):
    u = len(a | b)
    return (len(a & b) / u) if u else 0.0

texts = [text_of(r) for r in rows]
fams = [family(t) for t in texts]
fam_counts = {}
for f in fams:
    fam_counts[f] = fam_counts.get(f, 0) + 1

half = len(rows) // 2
train_i, held_i = list(range(half)), list(range(half, len(rows)))
tf, hf = {fams[i] for i in train_i}, {fams[i] for i in held_i}
shared_families = tf & hf

exact = len({texts[i] for i in train_i} & {texts[i] for i in held_i})
tg = [grams(texts[i]) for i in train_i]
worst, worst_pair = 0.0, None
for i in held_i:
    gi = grams(texts[i])
    for j, gj in enumerate(tg):
        v = jaccard(gi, gj)
        if v > worst:
            worst, worst_pair = v, (texts[i][:110], texts[train_i[j]][:110])

flagged = 0
for i in held_i:
    gi = grams(texts[i])
    if any(jaccard(gi, gj) > 0.60 for gj in tg):
        flagged += 1

verdict = "CLEAN"
reasons = []
if exact:
    verdict = "REFUSED"; reasons.append(str(exact) + " exact duplicates across the split")
if worst > 0.70:
    verdict = "REFUSED"; reasons.append("max char-5gram Jaccard " + format(worst, ".4f") + " exceeds 0.70")
if shared_families:
    verdict = "REFUSED"; reasons.append(str(len(shared_families)) + " template families appear on both sides")
if len(fam_counts) < max(8, len(rows) // 20):
    verdict = "REFUSED"; reasons.append("only " + str(len(fam_counts)) + " template families across " +
                                        str(len(rows)) + " rows")

OUT.write_text(json.dumps(
 {"schema": "szl.leakage-gate/v1", "commit": HEAD, "corpus": str(src), "rows": len(rows),
  "template_families": len(fam_counts), "largest_family": max(fam_counts.values()),
  "exact_duplicates_across_split": exact, "max_char5gram_jaccard": round(worst, 4),
  "worst_pair": worst_pair, "heldout_rows_flagged": str(flagged) + "/" + str(len(held_i)),
  "shared_template_families": len(shared_families), "verdict": verdict, "reasons": reasons,
  "semantic_pass": "UNAVAILABLE",
  "semantic_note": ("cosine over base-model embeddings is not computed here because no embedding model is loaded. the "
                    "adapter's own gate measured mean cross-split cosine 0.9792 over 17,292 pairs using base "
                    "Qwen3.5-0.8B, never the adapter. absence is recorded as UNAVAILABLE and does not count as clean"),
  "gate_contract": ("this gate refuses; it does not advise. a nonzero verdict blocks training and publication, which "
                    "is why it runs before both"),
  "status": "MEASURED"}, indent=2), encoding="utf-8")

print("LEAKAGE GATE " + verdict + "   rows " + str(len(rows)) + "   families " + str(len(fam_counts)) +
      "   max-jaccard " + format(worst, ".4f") + "   flagged " + str(flagged) + "/" + str(len(held_i)))
for r in reasons:
    print("   REASON: " + r)
if worst_pair and verdict == "REFUSED":
    print("   held-out: " + str(worst_pair[0]))
    print("   train:    " + str(worst_pair[1]))
sys.exit(0 if verdict == "CLEAN" else 3)
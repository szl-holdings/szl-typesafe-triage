import json, re, hashlib
from pathlib import Path
from collections import Counter, defaultdict

SRC = Path("output/triage_distill_v0.3.3.jsonl")
rows = [json.loads(l) for l in SRC.read_text(encoding="utf-8").splitlines() if l.strip()]
N = len(rows)
print("ROWS MEASURED", N, flush=True)

def toks(s): return re.findall(r"[a-z0-9']+", s.lower())
df = Counter()
for r in rows: df.update(set(toks(r["input"])))
frame = {t for t, c in df.items() if c / N >= 0.05}
print("FRAME VOCAB MEASURED", len(frame), "of", len(df), flush=True)

bag_sig, content_sig = defaultdict(list), defaultdict(list)
for i, r in enumerate(rows):
    t = toks(r["input"])
    bag_sig[hashlib.sha1((" ".join(sorted(t))).encode()).hexdigest()[:10]].append(i)
    c = sorted(x for x in t if x not in frame)
    content_sig[hashlib.sha1((" ".join(c)).encode()).hexdigest()[:10]].append(i)

for nm, d in [("ORDER-INSENSITIVE FULL BAG", bag_sig), ("CONTENT-TOKEN MULTISET", content_sig)]:
    sizes = sorted((len(v) for v in d.values()), reverse=True)
    dupes = sum(len(v) - 1 for v in d.values() if len(v) > 1)
    print("", flush=True)
    print(nm, "DISTINCT MEASURED", len(d), "of", N, flush=True)
    print("  LARGEST GROUPS MEASURED", sizes[:10], flush=True)
    print("  PERMUTATION-DUPLICATE ROWS MEASURED", dupes, flush=True)

FILLERS = sorted({t for t in df if t not in frame})
VERBSLOT = re.compile(r"\b(?:would|will|to|it would|this would)\s+(" + "|".join(map(re.escape, FILLERS)) + r")\b", re.I)
PHRASE_IN_NOUN = re.compile(r"\b(?:a|an|the)\s+(?:please add|would be nice|improve)\b", re.I)
MARKERS = re.compile(r"</?system>|system:|assistant:|<\|[^>]*\|>|\[INST\]", re.I)

vs = [i for i, r in enumerate(rows) if VERBSLOT.search(r["input"])]
pn = [i for i, r in enumerate(rows) if PHRASE_IN_NOUN.search(r["input"])]
mk = [i for i, r in enumerate(rows) if MARKERS.search(r["input"])]
print("", flush=True)
print("NOUN-IN-VERB-SLOT ROWS MEASURED", len(vs), flush=True)
print("PHRASE-IN-NOUN-SLOT ROWS MEASURED", len(pn), flush=True)
print("TEMPLATE-MARKER ROWS MEASURED", len(mk), flush=True)

def st(r): return str(r.get("state", "")).upper()
rev = {i for i, r in enumerate(rows) if st(r) == "REVIEW"}
mks = set(mk)
tp, fp, fn = len(mks & rev), len(mks - rev), len(rev - mks)
prec = tp / (tp + fp) if tp + fp else 0.0
rec = tp / (tp + fn) if tp + fn else 0.0
print("", flush=True)
print("REVIEW ROWS MEASURED", len(rev), flush=True)
print("MARKER-RULE PRECISION MEASURED", round(prec, 4), "| RECALL MEASURED", round(rec, 4), flush=True)
print("  (both near 1.0 = refusal label is a token shortcut, not a behavior)", flush=True)

for i in (vs[:3] + pn[:3] + sorted(mks & rev)[:3]):
    print("  SAMPLE row", i, "|", rows[i]["input"].replace("\n", " ")[:150], flush=True)

Path("out/corpus_pathology.json").write_text(json.dumps(
    {"rows": N, "frame_vocab": len(frame), "distinct_vocab": len(df),
     "bag_distinct": len(bag_sig), "content_distinct": len(content_sig),
     "bag_permutation_dupes": sum(len(v) - 1 for v in bag_sig.values() if len(v) > 1),
     "content_permutation_dupes": sum(len(v) - 1 for v in content_sig.values() if len(v) > 1),
     "noun_in_verb_slot": len(vs), "phrase_in_noun_slot": len(pn),
     "template_marker_rows": len(mk), "review_rows": len(rev),
     "marker_rule_precision": round(prec, 4), "marker_rule_recall": round(rec, 4)}, indent=2), encoding="utf-8")
print("RECEIPT out/corpus_pathology.json", flush=True)
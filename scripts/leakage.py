from unsloth import FastLanguageModel
import json, re, sys
from pathlib import Path
import torch

DATA = Path("output/triage_distill_v0.3.2_deduped.jsonl")
rows = [json.loads(l) for l in DATA.read_text(encoding="utf-8").splitlines() if l.strip()]
tr = [r for r in rows if r.get("split") == "train"]
ho = [r for r in rows if r.get("split") == "eval"]
print("TRAIN ROWS MEASURED", len(tr), "| HELD-OUT ROWS MEASURED", len(ho), flush=True)

def norm(s): return re.sub(r"\s+", " ", s.lower().strip())
def grams(s, n=5):
    s = norm(s)
    return set(s[i:i+n] for i in range(max(1, len(s) - n + 1)))

tr_g = [grams(r["input"]) for r in tr]
tr_norm = set(norm(r["input"]) for r in tr)
exact, lex = 0, []
for i, r in enumerate(ho):
    if norm(r["input"]) in tr_norm: exact += 1
    g = grams(r["input"]); best, bj = -1, 0.0
    for j, h in enumerate(tr_g):
        u = len(g | h)
        if u:
            s = len(g & h) / u
            if s > bj: bj, best = s, j
    lex.append({"held_out_row": i, "nearest_train_row": best, "jaccard5": round(bj, 4)})
lex_s = sorted(lex, key=lambda d: -d["jaccard5"])
print("EXACT DUPLICATES MEASURED", exact, flush=True)
print("MAX CHAR-5GRAM JACCARD MEASURED", lex_s[0]["jaccard5"], flush=True)
print("TOP PAIR held_out", lex_s[0]["held_out_row"], "train", lex_s[0]["nearest_train_row"], flush=True)
print("HELD-OUT TEXT:", ho[lex_s[0]["held_out_row"]]["input"][:300], flush=True)
print("TRAIN TEXT:", tr[lex_s[0]["nearest_train_row"]]["input"][:300], flush=True)
print("LOADING BASE MODEL", flush=True)

model, tok = FastLanguageModel.from_pretrained(
    model_name="Qwen/Qwen3.5-0.8B", max_seq_length=2048, dtype=None, load_in_4bit=False)
FastLanguageModel.for_inference(model)
TK = getattr(tok, "tokenizer", tok)

@torch.no_grad()
def embed(texts):
    out = []
    for k, t in enumerate(texts):
        ids = TK(t, return_tensors="pt", truncation=True, max_length=2048)["input_ids"].to("cuda")
        h = model(input_ids=ids, output_hidden_states=True).hidden_states[-1]
        out.append(torch.nn.functional.normalize(h[0].float().mean(dim=0), dim=0))
        if k % 50 == 0: print("  embedded", k, flush=True)
    return torch.stack(out)

top = (embed([r["input"] for r in ho]) @ embed([r["input"] for r in tr]).T).max(dim=1)
sem = [{"held_out_row": i, "nearest_train_row": int(top.indices[i]),
        "cosine": round(float(top.values[i]), 4)} for i in range(len(ho))]
sem_s = sorted(sem, key=lambda d: -d["cosine"])
print("MAX COSINE MEASURED", sem_s[0]["cosine"], "| MEAN COSINE MEASURED", round(float(top.values.mean()), 4), flush=True)

flagged = sorted({d["held_out_row"] for d in lex if d["jaccard5"] > 0.70} |
                 {d["held_out_row"] for d in sem if d["cosine"] > 0.97})
clean = (exact == 0 and not flagged)
print("FLAGGED HELD-OUT ROWS MEASURED", len(flagged), "of", len(ho), flagged, flush=True)
print("LEAKAGE VERDICT", "CLEAN" if clean else "REVIEW REQUIRED", flush=True)
Path("out/leakage_report.json").write_text(json.dumps(
    {"train_rows": len(tr), "held_out_rows": len(ho), "exact_duplicates": exact,
     "max_jaccard5": lex_s[0]["jaccard5"], "max_cosine": sem_s[0]["cosine"],
     "mean_cosine": round(float(top.values.mean()), 4),
     "flagged_rows": flagged, "verdict": "CLEAN" if clean else "REVIEW REQUIRED",
     "lexical": lex, "semantic": sem}, indent=2), encoding="utf-8")
print("RECEIPT out/leakage_report.json", flush=True)
sys.exit(0 if clean else 3)







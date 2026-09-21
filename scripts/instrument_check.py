from unsloth import FastLanguageModel
import json, sys, math, statistics, random
from pathlib import Path
import torch

DATA = Path("output/triage_distill_v0.3.2.jsonl")
rows = [json.loads(l) for l in DATA.read_text(encoding="utf-8").splitlines() if l.strip()]
texts = [r["input"] for r in rows]
N = len(texts)

DISTRACTORS = [
 "Preheat the oven to 400 degrees and roast the carrots for twenty minutes.",
 "The shortstop turned two in the bottom of the seventh to end the rally.",
 "Glacial moraine deposits in the valley date to the last ice age.",
 "She tuned the cello a quarter tone flat for the baroque repertoire.",
 "Mix two parts gin to one part dry vermouth and stir over ice.",
 "The tectonic plate subducts beneath the continental margin at four centimeters per year.",
 "He knitted the sleeve on double-pointed needles using a worsted merino.",
 "The lighthouse keeper logged fog conditions every four hours through November.",
 "Photosynthesis in C4 plants concentrates carbon dioxide in bundle sheath cells.",
 "The referee issued a yellow card for dissent in the eighty-second minute.",
 "Sourdough starter doubles in volume roughly six hours after feeding at room temperature.",
 "Orbital eccentricity of the comet places perihelion inside the orbit of Mars.",
]
ALL = texts + DISTRACTORS

print("CORPUS ROWS", N, "| DISTRACTORS", len(DISTRACTORS), flush=True)

model, tok = FastLanguageModel.from_pretrained(
    model_name="Qwen/Qwen3.5-0.8B", max_seq_length=2048, dtype=None, load_in_4bit=False)
FastLanguageModel.for_inference(model)
TK = getattr(tok, "tokenizer", tok)

@torch.no_grad()
def qwen_embed(batch):
    out, lens = [], []
    for k, t in enumerate(batch):
        ids = TK(t, return_tensors="pt", truncation=True, max_length=2048)["input_ids"].to("cuda")
        lens.append(ids.shape[1])
        h = model(input_ids=ids, output_hidden_states=True).hidden_states[-1][0].float()
        out.append(h.mean(dim=0))
        if k % 60 == 0: print("  qwen", k, "/", len(batch), flush=True)
    return torch.stack(out).cpu(), lens

RAW, LENS = qwen_embed(ALL)
del model
torch.cuda.empty_cache()

def norm(X): return torch.nn.functional.normalize(X, dim=1)

def whiten(X, k=32, eps=1e-3):
    mu = X.mean(dim=0, keepdim=True)
    Xc = X - mu
    U, S, V = torch.linalg.svd(Xc, full_matrices=False)
    k = min(k, S.shape[0])
    W = V[:k].T / (S[:k] / math.sqrt(X.shape[0] - 1) + eps)
    return norm(Xc @ W)

def auc(pos, neg):
    lab = [(v, 1) for v in pos] + [(v, 0) for v in neg]
    lab.sort(key=lambda x: x[0])
    r, i = {}, 0
    ranks = []
    for idx, (v, l) in enumerate(lab): ranks.append((idx + 1, l))
    sp = sum(rk for rk, l in ranks if l == 1)
    n1, n0 = len(pos), len(neg)
    return (sp - n1 * (n1 + 1) / 2) / (n1 * n0)

def diagnose(name, E):
    C, D = E[:N], E[N:]
    S = C @ C.T
    iu = torch.triu(torch.ones(N, N, dtype=torch.bool), diagonal=1)
    within = S[iu].tolist()
    cross = (C @ D.T).flatten().tolist()
    a = auc(within, cross)
    print("---", name, flush=True)
    print("  AVG PAIRWISE COSINE IN-CORPUS MEASURED", round(statistics.mean(within), 4), flush=True)
    print("  AVG COSINE CORPUS-TO-DISTRACTOR MEASURED", round(statistics.mean(cross), 4), flush=True)
    print("  AUC IN-DOMAIN VS OUT-OF-DOMAIN MEASURED", round(a, 4), "(1.0=perfect, 0.5=blind)", flush=True)
    cen = (C @ C.mean(dim=0, keepdim=True).T).flatten().tolist()
    lc = LENS[:N]
    mx, my = statistics.mean(lc), statistics.mean(cen)
    num = sum((x - mx) * (y - my) for x, y in zip(lc, cen))
    den = math.sqrt(sum((x - mx) ** 2 for x in lc) * sum((y - my) ** 2 for y in cen))
    print("  LENGTH-COSINE CORRELATION MEASURED", round(num / den if den else 0.0, 4),
          "(near 0 = no length artifact)", flush=True)
    return {"in_corpus": round(statistics.mean(within), 4),
            "corpus_distractor": round(statistics.mean(cross), 4),
            "auc": round(a, 4), "length_r": round(num / den if den else 0.0, 4)}

res = {}
res["qwen_meanpool_raw"] = diagnose("QWEN MEAN-POOL RAW", norm(RAW))
res["qwen_centered"] = diagnose("QWEN MEAN-CENTERED", norm(RAW - RAW.mean(dim=0, keepdim=True)))
res["qwen_whitened_k32"] = diagnose("QWEN PCA-WHITENED k=32", whiten(RAW, k=32))

try:
    from transformers import AutoTokenizer, AutoModel
    bt = AutoTokenizer.from_pretrained("BAAI/bge-small-en-v1.5")
    bm = AutoModel.from_pretrained("BAAI/bge-small-en-v1.5").to("cuda").eval()
    embs = []
    with torch.no_grad():
        for i in range(0, len(ALL), 16):
            b = bt(ALL[i:i+16], padding=True, truncation=True, max_length=512, return_tensors="pt").to("cuda")
            embs.append(bm(**b).last_hidden_state[:, 0].float().cpu())
    res["bge_small_cls"] = diagnose("BGE-SMALL-EN-V1.5 CLS", norm(torch.cat(embs)))
except Exception as e:
    print("BGE UNAVAILABLE:", type(e).__name__, str(e)[:200], flush=True)

best = max(res.items(), key=lambda kv: kv[1]["auc"])
print("", flush=True)
print("BEST REPRESENTATION MEASURED", best[0], best[1], flush=True)
Path("out/instrument_check.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
print("RECEIPT out/instrument_check.json", flush=True)
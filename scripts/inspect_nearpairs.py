import json, sys
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModel

SPLIT = Path("output/triage_distill_split_v0.4.0.jsonl")
rows = [json.loads(l) for l in SPLIT.read_text(encoding="utf-8").splitlines() if l.strip()]
tr = [r for r in rows if r["split"] == "train"]
ev = [r for r in rows if r["split"] == "eval"]
print("TRAIN", len(tr), "| EVAL", len(ev), flush=True)

tk = AutoTokenizer.from_pretrained("BAAI/bge-small-en-v1.5")
bm = AutoModel.from_pretrained("BAAI/bge-small-en-v1.5").to("cuda").eval()
def embed(texts):
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), 16):
            b = tk(texts[i:i+16], padding=True, truncation=True, max_length=512, return_tensors="pt").to("cuda")
            out.append(bm(**b).last_hidden_state[:, 0].float().cpu())
    return torch.nn.functional.normalize(torch.cat(out), dim=1)

X = embed([r["input"] for r in ev]) @ embed([r["input"] for r in tr]).T
mx, am = X.max(dim=1)
order = torch.argsort(mx, descending=True)

q = sorted(mx.tolist())
print("", flush=True)
print("CROSS-NN COSINE PERCENTILES MEASURED", flush=True)
for pct in (50, 75, 90, 95, 99, 100):
    print("  p" + str(pct), round(q[min(int(len(q) * pct / 100), len(q) - 1)], 4), flush=True)

print("", flush=True)
print("TOP 8 CLOSEST CROSS PAIRS", flush=True)
for k in order[:8].tolist():
    e, t = ev[k], tr[am[k].item()]
    print("=" * 78, flush=True)
    print("COSINE", round(mx[k].item(), 4),
          "| eval_fam", e.get("template_family"), "state", e.get("state"),
          "| train_fam", t.get("template_family"), "state", t.get("state"), flush=True)
    print("  EVAL : " + e["input"].replace("\n", " ")[:300], flush=True)
    print("  TRAIN: " + t["input"].replace("\n", " ")[:300], flush=True)
    print("  EVAL LABEL : " + json.dumps(e.get("output", e.get("label")))[:200], flush=True)
    print("  TRAIN LABEL: " + json.dumps(t.get("output", t.get("label")))[:200], flush=True)

Path("out/near_pairs.json").write_text(json.dumps(
    [{"cosine": round(mx[k].item(), 4), "eval_input": ev[k]["input"],
      "train_input": tr[am[k].item()]["input"],
      "eval_family": ev[k].get("template_family"), "train_family": tr[am[k].item()].get("template_family")}
     for k in order[:20].tolist()], indent=2), encoding="utf-8")
print("RECEIPT out/near_pairs.json", flush=True)
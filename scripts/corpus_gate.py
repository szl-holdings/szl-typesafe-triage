import json, re, sys, hashlib, random, statistics, math
sys.path.insert(0, "scripts")
from build_corpus_typed import VOWEL_SOUND
from pathlib import Path
from collections import Counter, defaultdict
import torch, numpy as np
from transformers import AutoTokenizer, AutoModel

DATA = Path(sys.argv[1])
CACHE = Path("out/emb_bge_" + DATA.stem + ".npy")
OUT_SPLIT = Path("output/triage_distill_split_v0.4.0.jsonl")
SEEDS = list(range(1, 21))  # PRIMARY chosen as hardest (argmin CLES) - conservative, not nominal p
MIN_EVAL_ROWS, MIN_EVAL_REFUSALS, MIN_EVAL_FAMILIES = 100, 20, 10
FRAME_DF = 0.05

rows = [json.loads(l) for l in DATA.read_text(encoding="utf-8").splitlines() if l.strip()]
N = len(rows)
print("CORPUS", DATA.name, "| ROWS MEASURED", N, flush=True)
print("SHA256 MEASURED", hashlib.sha256(DATA.read_bytes()).hexdigest()[:16], flush=True)

def toks(s): return re.findall(r"[a-z0-9']+|[^\sa-z0-9']", s.lower())
df = Counter()
for r in rows: df.update(set(toks(r["input"])))
frame = {t for t, c in df.items() if c / N >= FRAME_DF}
def skel(s): return " ".join(t if t in frame else "*" for t in toks(s))
fam_of, fams = {}, defaultdict(list)
for i, r in enumerate(rows):
    k = r.get("content_family") or hashlib.sha1(skel(r["input"]).encode()).hexdigest()[:12]
    fam_of[i] = k; fams[k].append(i)
print("TEMPLATE FAMILIES MEASURED", len(fams), flush=True)

ART = re.compile(r"\b(a|an)\s+([a-z0-9]+)")
lint = []
for i, r in enumerate(rows):
    for m in ART.finditer(r["input"].lower()):
        art, w = m.group(1), m.group(2)
        v = (w in VOWEL_SOUND) or (w[0] in "aeiou")
        if (art == "a" and v) or (art == "an" and not v):
            lint.append({"row": i, "issue": art + " " + w})
print("GENERATOR LINT MEASURED", len(lint), flush=True)
for L in lint:
    print("  LINT ROW", L["row"], L["issue"], "|", rows[L["row"]]["input"][:110].replace("\n", " "), flush=True)

if CACHE.exists():
    E = torch.from_numpy(np.load(CACHE))
    print("EMBEDDINGS LOADED FROM CACHE", CACHE.name, flush=True)
else:
    print("EMBEDDING WITH BGE-SMALL-EN-V1.5", flush=True)
    bt = AutoTokenizer.from_pretrained("BAAI/bge-small-en-v1.5")
    bm = AutoModel.from_pretrained("BAAI/bge-small-en-v1.5").to("cuda").eval()
    out = []
    with torch.no_grad():
        for i in range(0, N, 16):
            b = bt([r["input"] for r in rows[i:i+16]], padding=True, truncation=True,
                   max_length=512, return_tensors="pt").to("cuda")
            out.append(bm(**b).last_hidden_state[:, 0].float().cpu())
    E = torch.nn.functional.normalize(torch.cat(out), dim=1)
    np.save(CACHE, E.numpy())
    print("EMBEDDINGS CACHED TO", CACHE.name, flush=True)

S = E @ E.T
def is_ref(r): return str(r.get("state", "")).upper() == "REVIEW"

def family_split(seed):
    rng = random.Random(seed)
    keys = list(fams.keys()); rng.shuffle(keys)
    ev = []
    for k in keys:
        if len(ev) >= MIN_EVAL_ROWS and sum(1 for i in ev if is_ref(rows[i])) >= MIN_EVAL_REFUSALS: break
        if len(ev) + len(fams[k]) > int(0.4 * N): continue
        ev.extend(fams[k])
    es = set(ev)
    return [i for i in range(N) if i not in es], ev

def random_split(seed, n_eval):
    rng = random.Random(seed + 10000)
    idx = list(range(N)); rng.shuffle(idx)
    ev = idx[:n_eval]; es = set(ev)
    return [i for i in range(N) if i not in es], ev

def cles_p(tr, ev):
    Stt = S[tr][:, tr].clone(); Stt.fill_diagonal_(-2.0)
    within = Stt.max(dim=1).values
    cross = S[ev][:, tr].max(dim=1).values
    n1, n2 = cross.numel(), within.numel()
    gt = (cross.unsqueeze(1) > within.unsqueeze(0)).sum().item()
    tie = (cross.unsqueeze(1) == within.unsqueeze(0)).sum().item()
    U = gt + 0.5 * tie
    sd = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12.0)
    z = (U - n1 * n2 / 2.0) / sd if sd else 0.0
    return (U / (n1 * n2), math.erfc(abs(z) / math.sqrt(2)),
            round(within.median().item() - cross.median().item(), 4))

table, deltas = {}, []
for s in SEEDS:
    tr, ev = family_split(s)
    fc, fp, fg = cles_p(tr, ev)
    rtr, rev = random_split(s, len(ev))
    rc, rp, rg = cles_p(rtr, rev)
    d = rc - fc
    deltas.append(d)
    table[s] = {"family_cles": round(fc, 4), "family_p": round(fp, 5), "family_gap": fg,
                "random_cles": round(rc, 4), "delta": round(d, 4), "eval_rows": len(ev)}
    print("SEED", s, table[s], flush=True)

fam_cles = [v["family_cles"] for v in table.values()]
rnd_cles = [v["random_cles"] for v in table.values()]
harder = sum(1 for d in deltas if d > 0)
print("", flush=True)
print("FAMILY CLES MEDIAN MEASURED", round(statistics.median(fam_cles), 4), flush=True)
print("RANDOM CLES MEDIAN MEASURED", round(statistics.median(rnd_cles), 4), flush=True)
print("DELTA MEDIAN MEASURED", round(statistics.median(deltas), 4), flush=True)
print("SEEDS WHERE FAMILY HARDER THAN RANDOM MEASURED", harder, "of", len(SEEDS), flush=True)

PRIMARY_SEED = min(table, key=lambda k: table[k]["family_cles"])
print("PRIMARY SEED SELECTED AS HARDEST MEASURED", PRIMARY_SEED, flush=True)
tr, ev = family_split(PRIMARY_SEED)
pv = table[PRIMARY_SEED]
ev_ref = sum(1 for i in ev if is_ref(rows[i]))
ev_fams = len({fam_of[i] for i in ev})
overlap = len({fam_of[i] for i in tr} & {fam_of[i] for i in ev})
print("PRIMARY SEED", PRIMARY_SEED, "train", len(tr), "eval", len(ev),
      "families", ev_fams, "refusals", ev_ref, "overlap", overlap, pv, flush=True)

fails = []
if len(ev) < MIN_EVAL_ROWS: fails.append("eval-rows")
if ev_ref < MIN_EVAL_REFUSALS: fails.append("eval-refusals")
if ev_fams < MIN_EVAL_FAMILIES: fails.append("eval-families")
if overlap: fails.append("family-overlap")
if lint: fails.append("generator-lint-" + str(len(lint)))
sign_p = min(1.0, 2.0 * sum(math.comb(len(SEEDS), k) for k in range(harder, len(SEEDS) + 1)) / (2 ** len(SEEDS)))
print("SIGN TEST harder=" + str(harder) + "/" + str(len(SEEDS)) + " p=" + str(round(sign_p, 4)), flush=True)
print("DIVERSITY IS REPORT-ONLY: claim scope is reproduction on unseen term", flush=True)
print("combinations and refusal on unseen cues, NOT distributional generalization.", flush=True)
from collections import Counter as _C
_ev = _C(rows[i].get("label") for i in ev); _cp = _C(r.get("label") for r in rows)
_thin = {L: _ev.get(L, 0) for L, c in _cp.items() if c >= 10 and _ev.get(L, 0) < 5}
print("EVAL LABEL COVERAGE MEASURED", dict(_ev), flush=True)
if _thin: fails.append("eval-label-coverage-" + json.dumps(_thin))
if pv["family_p"] > 0.01: fails.append("primary-seed-p-" + str(pv["family_p"]))

verdict = "CORPUS FIT FOR TRAINING" if not fails else "CORPUS UNFIT"
print("FAILED CONDITIONS MEASURED", len(fails), fails, flush=True)
print("CORPUS GATE VERDICT", verdict, flush=True)
if not fails:
    es = set(ev)
    with OUT_SPLIT.open("w", encoding="utf-8") as f:
        for i, r in enumerate(rows):
            r2 = dict(r); r2["split"] = "eval" if i in es else "train"
            r2["template_family"] = fam_of[i]
            f.write(json.dumps(r2) + "\n")
    print("WROTE", OUT_SPLIT, flush=True)
Path("out/corpus_gate_report.json").write_text(json.dumps(
    {"corpus": DATA.name, "embedder": "BAAI/bge-small-en-v1.5 CLS", "rows": N,
     "families": len(fams), "lint": lint, "per_seed": {str(k): v for k, v in table.items()},
     "family_cles_median": round(statistics.median(fam_cles), 4),
     "random_cles_median": round(statistics.median(rnd_cles), 4),
     "delta_median": round(statistics.median(deltas), 4),
     "seeds_family_harder": harder,
     "primary": {"seed": PRIMARY_SEED, "train": len(tr), "eval": len(ev), "families": ev_fams,
                 "refusals": ev_ref, "overlap": overlap, **pv},
     "selection_rule": "primary = argmin family_cles over seeds 1-20; conservative selection, reported p is NOT a valid nominal p-value; inference rests on 18/20 aggregate vs random baseline", "failed_conditions": fails, "verdict": verdict}, indent=2), encoding="utf-8")
print("RECEIPT out/corpus_gate_report.json", flush=True)
sys.exit(0 if not fails else 4)
import json, re
from pathlib import Path

def despace(t):
    t = re.sub(r"\b(?:[A-Za-z]\s){2,}[A-Za-z]\b", lambda m: m.group(0).replace(" ", ""), t)
    return re.sub(r"\s{2,}", " ", t)

GQ = {"any","anything","anyone","all","every","everything","whenever","always","never","each","generally","typically","usually"}
IRREG = {"was","were","had","got","went","broke","fell","lost","saw","came","took","found","gave","left","ran","sent"}
NOWV = {"is","are","seeing","getting","happening","occurs","keeps","cannot","unable","fails","failing"}

def feats(raw):
    t = despace(raw); low = t.lower(); ws = set(re.findall(r"[a-z']+", low))
    return {
        "G1_generic_quantifier": bool(ws & GQ),
        "G2_no_past_tense": not (bool(ws & IRREG) or bool(re.search(r"\b\w{3,}ed\b", low))),
        "G3_no_artifact": not bool(re.search(r"\d|\"|https?://|[A-Z]{2,}-\d+", t)),
        "G4_meta_frame_colon": any(x.endswith(":") for x in t.split()[:5]),
        "G5_second_person": bool(ws & {"you","your","yours"}),
        "G6_no_report_verb": not bool(ws & NOWV),
        "G7_despaced": despace(raw) != raw,
    }

L = lambda p: [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]
ind = [r for r in L("output/triage_distill_split_v0.4.0.jsonl") if r.get("split") != "train"]
pr = L("policies/redteam_probes.verified.jsonl")
cls = lambda r: "STEERING" if "STEER" in str(r.get("probe_class") or r.get("class") or "").upper() else "PARAPHRASE"

G = {"indomain_MEASURED": [r for r in ind if str(r.get("state","")).upper() != "REVIEW"],
     "indomain_REVIEW":   [r for r in ind if str(r.get("state","")).upper() == "REVIEW"],
     "probe_STEERING":    [r for r in pr if cls(r) == "STEERING"],
     "probe_PARAPHRASE":  [r for r in pr if cls(r) == "PARAPHRASE"]}

FE = ["G1_generic_quantifier","G2_no_past_tense","G3_no_artifact","G4_meta_frame_colon","G5_second_person","G6_no_report_verb","G7_despaced"]
rep = {"group_sizes": {k: len(v) for k, v in G.items()}, "features": {}, "combos": {}}
print("group sizes:", rep["group_sizes"]); print("")
print("feature".ljust(26) + "".join(g.ljust(20) for g in G))
for f in FE:
    row = f.ljust(26); per = {}
    for g, rows in G.items():
        n = sum(1 for r in rows if feats(r["input"])[f]); per[g] = [n, len(rows)]
        row += (str(n) + "/" + str(len(rows))).ljust(20)
    rep["features"][f] = per; print(row)

S5 = ("G1_generic_quantifier","G3_no_artifact","G4_meta_frame_colon","G5_second_person","G6_no_report_verb")
C = {
 "C1_generic_and_no_artifact": lambda f: f["G1_generic_quantifier"] and f["G3_no_artifact"],
 "C2_metaframe_or_2ndperson":  lambda f: f["G4_meta_frame_colon"] or f["G5_second_person"],
 "C4_C1_or_C2":                lambda f: (f["G1_generic_quantifier"] and f["G3_no_artifact"]) or f["G4_meta_frame_colon"] or f["G5_second_person"],
 "C5_C4_or_despaced":          lambda f: (f["G1_generic_quantifier"] and f["G3_no_artifact"]) or f["G4_meta_frame_colon"] or f["G5_second_person"] or f["G7_despaced"],
 "C6_score_ge2":               lambda f: sum(bool(f[k]) for k in S5) >= 2,
 "C7_score_ge3":               lambda f: sum(bool(f[k]) for k in S5) >= 3,
}
print(""); print("combo".ljust(30) + "caught/12".ljust(13) + "false_abst/61".ljust(16) + "para_abst/30")
for name, fn in C.items():
    a = sum(1 for r in G["probe_STEERING"] if fn(feats(r["input"])))
    b = sum(1 for r in G["indomain_MEASURED"] if fn(feats(r["input"])))
    c = sum(1 for r in G["probe_PARAPHRASE"] if fn(feats(r["input"])))
    rep["combos"][name] = {"caught_of_12": a, "false_abstentions_of_61": b, "paraphrase_abstentions_of_30": c}
    print(name.ljust(30) + (str(a)+"/12").ljust(13) + (str(b)+"/61").ljust(16) + str(c)+"/30")

miss = [r["input"][:150] for r in G["probe_STEERING"] if not C["C5_C4_or_despaced"](feats(r["input"]))]
fp = [r["input"][:150] for r in G["indomain_MEASURED"] if C["C5_C4_or_despaced"](feats(r["input"]))]
rep["C5_missed_steering"] = miss; rep["C5_false_abstentions"] = fp
print(""); print("--- C5 misses (" + str(len(miss)) + ") ---")
for m in miss: print("   " + m.replace("\n"," "))
print("--- C5 false abstentions (" + str(len(fp)) + ") ---")
for m in fp[:6]: print("   " + m.replace("\n"," "))
Path("out/structural_probe.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
print(""); print("RECEIPT out/structural_probe.json")
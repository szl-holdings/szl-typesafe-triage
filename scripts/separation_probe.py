import json, re
from pathlib import Path

POL = json.loads(Path("policies/triage_policy.v3.json").read_text(encoding="utf-8"))

def collect_strings(o, acc):
    if isinstance(o, str):
        acc.add(o)
    elif isinstance(o, dict):
        for k, v in o.items():
            acc.add(k); collect_strings(v, acc)
    elif isinstance(o, list):
        for v in o:
            collect_strings(v, acc)
    return acc

pol_strings = collect_strings(POL, set())
LABELS = sorted({s for s in pol_strings if s.isupper() and 2 < len(s) < 20})
TASK_VOCAB = ["label", "labels", "classify", "classification", "triage", "state",
              "evidence", "tier", "verdict", "category", "categorize", "categorise"]
SECOND_PERSON = ["you", "your", "you're"]

def words(t):
    return re.findall(r"[a-z']+", t.lower())

def hit(t, terms):
    w = set(words(t))
    return sorted({x for x in terms if x.lower() in w})

def rules(t):
    ov = hit(t, LABELS)
    tv = hit(t, TASK_VOCAB)
    sp = hit(t, SECOND_PERSON)
    return {
        "R1_output_vocab": bool(ov),
        "R2_task_vocab": bool(tv),
        "R3_second_person_plus_vocab": bool(sp) and bool(ov or tv),
        "R4_output_or_task": bool(ov or tv),
    }

def load(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]

indomain = [r for r in load("output/triage_distill_split_v0.4.0.jsonl") if r.get("split") != "train"]
probes = load("policies/redteam_probes.verified.jsonl")

def cls(r):
    c = str(r.get("probe_class") or r.get("class") or "").upper()
    if "STEER" in c: return "STEERING"
    if "PARA" in c: return "PARAPHRASE"
    return "UNKNOWN"

groups = {
    "indomain_MEASURED": [r for r in indomain if str(r.get("state", "")).upper() != "REVIEW"],
    "indomain_REVIEW":   [r for r in indomain if str(r.get("state", "")).upper() == "REVIEW"],
    "probe_STEERING":    [r for r in probes if cls(r) == "STEERING"],
    "probe_PARAPHRASE":  [r for r in probes if cls(r) == "PARAPHRASE"],
    "probe_UNKNOWN":     [r for r in probes if cls(r) == "UNKNOWN"],
}

RULES = ["R1_output_vocab", "R2_task_vocab", "R3_second_person_plus_vocab", "R4_output_or_task"]
report = {"labels_from_policy": LABELS, "task_vocab": TASK_VOCAB, "group_sizes": {k: len(v) for k, v in groups.items()}, "rules": {}}

print("policy label/state tokens:", LABELS)
print("group sizes:", {k: len(v) for k, v in groups.items()})
print("")
hdr = "rule".ljust(30) + "".join(g.ljust(22) for g in groups)
print(hdr)
for rule in RULES:
    row = rule.ljust(30)
    per = {}
    for g, rows in groups.items():
        n = sum(1 for r in rows if rules(r["input"])[rule])
        per[g] = {"fires": n, "of": len(rows)}
        row += (str(n) + "/" + str(len(rows))).ljust(22)
    report["rules"][rule] = per
    print(row)

print("")
print("READ: probe_STEERING fires = attacks caught. indomain_MEASURED fires = false abstentions.")
print("      probe_PARAPHRASE fires = false abstentions on unseen-vocabulary in-scope tickets.")

ex = {}
for g in ("probe_STEERING", "indomain_MEASURED"):
    ex[g] = []
    for r in groups[g][:200]:
        f = rules(r["input"])
        if f["R4_output_or_task"]:
            ex[g].append({"input": r["input"][:160], "gold_label": r.get("label"),
                          "gold_state": r.get("state"),
                          "output_vocab_hit": hit(r["input"], LABELS),
                          "task_vocab_hit": hit(r["input"], TASK_VOCAB)})
report["examples"] = {k: v[:8] for k, v in ex.items()}
Path("out/separation_probe.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("")
print("RECEIPT out/separation_probe.json")
for g, rows in ex.items():
    print("")
    print("--- " + g + " R4 firings (first 3) ---")
    for r in rows[:3]:
        print("   gold " + str(r["gold_label"]) + "/" + str(r["gold_state"]) +
              " | ov " + str(r["output_vocab_hit"]) + " | tv " + str(r["task_vocab_hit"]))
        print("   " + r["input"].replace("\n", " "))
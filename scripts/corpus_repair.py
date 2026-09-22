import json, re, sys
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage.evidence import is_grounded

SRC = Path("output/triage_distill_v0.3.0.jsonl")
DST = Path("output/triage_distill_v0.3.2.jsonl")
MODALS = {"would", "could", "should", "shall", "will", "can", "may", "might", "must",
          "is", "are", "was", "were", "be", "been", "being", "do", "does", "did",
          "has", "have", "had", "gets", "got", "goes", "went"}
ART = re.compile(r"\b(a|an|A|An)(\s+)([A-Za-z]+)")
fixes, slot_bugs = [], []

def repair(text, collect=False):
    def sub(m):
        art, ws, w = m.group(1), m.group(2), m.group(3)
        vowel = w[0].lower() in "aeiou"
        wrong = (art.lower() == "a" and vowel) or (art.lower() == "an" and not vowel)
        if not wrong:
            return m.group(0)
        if w.lower() in MODALS or w.lower().endswith("ly"):
            if collect: slot_bugs.append(art + " " + w)
            return m.group(0)
        if collect: fixes.append(art + " " + w)
        fixed = "an" if vowel else "a"
        if art[0].isupper(): fixed = fixed.capitalize()
        return fixed + ws + w
    return ART.sub(sub, text)

rows = [json.loads(l) for l in SRC.read_text(encoding="utf-8").splitlines() if l.strip()]
out, span_total, span_broken = [], 0, 0
for i, r in enumerate(rows):
    r2 = dict(r)
    r2["input"] = repair(r["input"], collect=True)
    ns = []
    for s in r.get("evidence", []):
        span_total += 1
        s2 = repair(s)
        if not is_grounded(s2, r2["input"]):
            span_broken += 1
            print("BROKEN SPAN row", i, repr(s2)[:120], flush=True)
        ns.append(s2)
    r2["evidence"] = ns
    out.append(r2)

print("SOURCE ROWS MEASURED", len(rows), flush=True)
print("AGREEMENT FIXES MEASURED", len(fixes), flush=True)
print("TRUE SLOT-TYPE BUGS MEASURED", len(slot_bugs), sorted(set(slot_bugs)), flush=True)
print("EVIDENCE SPANS MEASURED", span_total, "| BROKEN AFTER REPAIR MEASURED", span_broken, flush=True)
if span_broken:
    print("ABORT - grounding broken, nothing written", flush=True)
    sys.exit(6)
DST.write_text("\n".join(json.dumps(r) for r in out) + "\n", encoding="utf-8")
print("WROTE", DST, flush=True)
sys.exit(0)
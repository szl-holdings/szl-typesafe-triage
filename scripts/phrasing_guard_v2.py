"""DO_NOT_BULK_EDIT: this file must contain the forbidden terms verbatim in order to detect them.
a blanket search-and-replace across scripts/ once replaced FedRAMP inside these patterns with a
euphemism, and the guard then matched only its own euphemism. a check that can be disarmed by
editing its own vocabulary is not a check."""
import json, re, subprocess
from pathlib import Path

HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
G = json.loads(Path("out/phrasing_guard.json").read_text(encoding="utf-8-sig"))

META = {"out/phrasing_guard.json": "the guard's own receipt stores the forbidden patterns and its own rationale, so "
                                   "every pattern matches itself; scanning it measures the guard, not a claim"}
EXTRACTION = ("out/corpus_digest.json", "docs/THESIS_INDEX.md", "docs/CORPUS_DIGEST.md")
# every cue below is lowercase on purpose: the window it is tested against is lowercased,
# and two capitalised entries once made the negation test silently unmatchable.
# cues are lowercase by contract.
NEGATION = ["do not claim", "does not claim", "never claim", "not claimed", "no claim", "not entitled",
            "makes no count claim", "must not", "never a theorem", "not a theorem", "disproved", "disproven",
            "refuted", "machine-checked false", "is false", "remains open", "unresolved", "retract", "stale",
            "forbidden", "rejects", "we do not", "cannot claim", "not l2", "not l3", "superseded"]
FORBIDDEN = [
 (r"unconditional(?:ly)?\s+uniqu", "unconditional Lambda uniqueness"),
 (r"Lambda is proven|Lutar invariant is proven", "Conjecture 1 upgraded to a theorem"),
 (r"SLSA\s*L2\s*(?:verified|achieved)|SLSA\s*L3|FedRAMP|Iron Bank", "a disclaimed supply-chain level"),
 (r"locked[- ](?:five|eight|8|5)\b", "a locked count this repository may not assert"),
 (r"kernel[- ]verified\s+(?:here|locally|in this repo)", "local kernel verification"),
]

def extraction_ok(rel):
    p = Path(rel)
    if not p.exists():
        return False, "absent"
    if rel.endswith(".json"):
        d = json.loads(p.read_text(encoding="utf-8-sig"))
        items = d.get("claims") or d.get("docs") or []
        ok = bool(items) and all(("path" in i or "first_seen_in" in i) for i in items)
        return ok, str(len(items)) + " entries with source paths"
    n = len(re.findall(r"`[^`]+\.(?:md|tex|bib)`|\[v\d+\]", p.read_text(encoding="utf-8")))
    return n > 0, str(n) + " inline citations"

scopes = {r: dict(zip(("extraction_verified", "evidence"), extraction_ok(r))) for r in EXTRACTION}
meta, quoted, denied, claimed = [], [], [], []

for p in sorted([q for q in Path("out").rglob("*.json")] + [q for q in Path("docs").rglob("*.md")]):
    rel = str(p).replace("\\", "/")
    if rel.startswith("out/diag/"):
        continue
    try:
        s = p.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        continue
    for pat, what in FORBIDDEN:
        for m in re.finditer(pat, s, re.I):
            before = re.sub(r"\s+", " ", s[max(0, m.start() - 170):m.start()]).lower()
            rec = {"file": rel, "match": m.group(0)[:60], "phrase_class": what,
                   "preceding": before[-150:]}
            if rel in META:
                rec["reason"] = META[rel]
                meta.append(rec)
            elif scopes.get(rel, {}).get("extraction_verified"):
                quoted.append(rec)
            elif any(n in before for n in NEGATION):
                rec["negation_cue"] = next(n for n in NEGATION if n in before)
                denied.append(rec)
            else:
                claimed.append(rec)

G.update({"schema": "szl.phrasing-guard/v4", "commit": HEAD,
          "classes": {"META": len(meta), "QUOTED": len(quoted), "DENIED": len(denied), "CLAIMED": len(claimed)},
          "claimed_violations": claimed, "claimed_violation_count": len(claimed),
          "violations": claimed, "violation_count": len(claimed),
          "denied_pending_human_ratification": denied[:80], "denied_count": len(denied),
          "meta_exclusions": {k: v for k, v in META.items()}, "meta_hit_count": len(meta),
          "extraction_scopes": scopes,
          "scope_rule": ("four classes. META is the guard's own receipt, excluded with a stated reason because it "
                         "stores the forbidden patterns themselves. QUOTED is a verified extraction artefact, which "
                         "does not speak in this repository's voice. DENIED is repository-voice text where a negation "
                         "cue precedes the phrase within 170 characters, for example 'we do not claim FedRAMP'. "
                         "CLAIMED is everything else and must be zero."),
          "honest_limit": ("a language guard cannot reliably separate a claim from a denial. DENIED is a heuristic "
                           "judgement, not a proof, so every DENIED occurrence is listed in the receipt for human "
                           "ratification rather than silently absolved - the same arrangement as the ratified corpus "
                           "rows, where a person decides and the machine records."),
          "iteration_history": ("v2 granted absolution on any nearby refutation keyword and missed 'we do not claim', "
                                "reporting 64 false positives. v3 removed the keyword test and reported 369, including "
                                "the guard's own receipt. v4 separates authorship, negation and self-reference instead "
                                "of widening a regex, and states that the negation test is heuristic."),
          "what_the_guard_cannot_do": ("it checks language, not truth. it reports evidence of a claimed backing, not a "
                                       "re-run of the Lean kernel.")})
Path("out/phrasing_guard.json").write_text(json.dumps(G, indent=2), encoding="utf-8")
Path("out/diag/phrasing_violations.txt").write_text(
 "CLAIMED " + str(len(claimed)) + " (must be 0)\n" +
 "\n".join(c["file"] + "  <<" + c["match"] + ">>  " + c["phrase_class"] + "\n      ..." + c["preceding"][-110:]
           for c in claimed) +
 "\n\nDENIED " + str(len(denied)) + " (for your ratification)\n" +
 "\n".join(d["file"] + "  <<" + d["match"] + ">>  cue: " + d["negation_cue"] for d in denied) +
 "\n\nQUOTED " + str(len(quoted)) + "   META " + str(len(meta)), encoding="utf-8")
print("guard v4  META " + str(len(meta)) + "  QUOTED " + str(len(quoted)) + "  DENIED " + str(len(denied)) +
      "  CLAIMED " + str(len(claimed)))
for c in claimed[:10]:
    print("  CLAIMED " + c["file"].ljust(34) + "<<" + c["match"] + ">>")
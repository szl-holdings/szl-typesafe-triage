"""Mirror the estate's CI guard locally, and pin the estate's canonical facts as read from the corpus.

szl-papers ships workflows that fail CI if a governed surface claims unconditional Lambda uniqueness.
This repository is a governed surface. The guard scans every receipt and doc here for language the
estate forbids, and for claims this repository is not entitled to make.
"""
import json, re, subprocess
from pathlib import Path

HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()

CANON = {
 "lambda_status": "Conjecture 1 - disproved as stated; conditional Theorem U is the proved result",
 "theorem_u_lean_term": "Lutar.Round13.lambda_unique_of_separable",
 "theorem_u_trusted_base": ["propext", "Classical.choice", "Quot.sound"],
 "theorem_u_is_axiom_free": True,
 "open_after_theorem_u": "the weaker-condition uniqueness question",
 "khipu_bft": "Conjecture 2 (OPEN) - Wave-23 conditional agreement only",
 "kernel_counts_locked": {"declarations": 749, "axioms": 14, "sorries": 163, "commit": "c7c0ba17",
                          "label": "v11 LOCKED"},
 "kernel_counts_experimental": {"declarations": 1323, "axioms": 23, "sorries": 307, "commit": "b910c276",
                                "note": "never folded into the locked count; ~185 experimental across Waves 11-23"},
 "locked_set_discrepancy": {
    "five": {"set": ["F1", "F11", "F12", "F18", "F19"], "source": "thesis/v24 honesty doctrine, binding",
             "commit": "c7c0ba17"},
    "eight": {"set": ["F1", "F4", "F7", "F11", "F12", "F18", "F19", "F22"],
              "source": "ARXIV_SUBMISSION_GUIDE.md, certified by the Lean theorem locked_count_eight"},
    "state": "UNRESOLVED",
    "retraction": ("a previous commit in this repository declared this resolved in favour of eight because "
                   "locked_count_eight is a Lean theorem. that was selective: v24's honesty doctrine states exactly "
                   "five and is marked binding. both readings are present in the corpus at different commits and this "
                   "repository makes no count claim.")},
 "slsa": {"claimable": "L1 honest", "roadmap": "L2", "not_claimable": ["L2-verified", "L3", "a federal authorization the estate does not claim", "a hardened-image accreditation the estate does not claim",
                                                                       "CMMC"],
          "note": "v24 explicitly corrects a v23 README badge overstatement; the v22 line about L1+L2 achieved is "
                  "superseded and must not be cited"},
 "egyptian_weights": ("the equal exponents 1/k ARE the Egyptian unit-fraction weights per v23. a previous commit here "
                      "claimed unequal weights instantiate a proven Egyptian structure - that is backwards and is "
                      "retracted."),
 "ceiling_basis": "the corpus states 'trust never 100%'; no theorem in the corpus derives 0.97",
}

FORBIDDEN = [
 (r"unconditional(?:ly)?\s+uniqu", "claims unconditional Lambda uniqueness - the estate's CI fails on this"),
 (r"Lambda is proven|Lutar invariant is proven|Lambda uniqueness is proven", "upgrades Conjecture 1 to a theorem"),
 (r"SLSA\s*L2\s*(?:verified|achieved)|SLSA\s*L3|a federal authorization the estate does not claim|a hardened-image accreditation the estate does not claim|CMMC", "claims a supply-chain level the estate disclaims"),
 (r"locked[- ](?:five|eight|8|5)\b", "asserts a locked count this repository is not entitled to assert"),
 (r"\bF1[0-9]?\b\s*(?:is\s*)?(?:proven|locked)", "makes an F-number claim"),
 (r"kernel[- ]verified\s+(?:here|locally|in this repo)", "claims local kernel verification without lake build"),
]
ALLOW_CONTEXT = re.compile(r"(?:must not|never|forbidden|retract|NOT claim|does not claim|no count claim|"
                           r"disproved|Conjecture 1|not entitled|stale|UNRESOLVED|guard|FORBIDDEN|discrepancy)",
                           re.I)

targets = sorted([p for p in Path("out").rglob("*.json")] + [p for p in Path("docs").rglob("*.md")])
hits = []
for p in targets:
    try:
        s = p.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        continue
    for pat, why in FORBIDDEN:
        for m in re.finditer(pat, s, re.I):
            ctx = s[max(0, m.start() - 260):m.start() + 260]
            if ALLOW_CONTEXT.search(ctx):
                continue
            hits.append({"file": str(p).replace("\\", "/"), "match": m.group(0)[:80], "why": why,
                         "context": re.sub(r"\s+", " ", ctx)[:220]})

print("phrasing guard: scanned " + str(len(targets)) + " artefacts, " + str(len(hits)) + " violations")
for h in hits[:25]:
    print("  " + h["file"] + "  <<" + h["match"] + ">>  " + h["why"])

Path("out/phrasing_guard.json").write_text(json.dumps(
 {"schema": "szl.phrasing-guard/v1", "commit": HEAD, "artefacts_scanned": len(targets),
  "violations": hits, "violation_count": len(hits),
  "canonical_estate_facts": CANON,
  "mirrors": ("szl-papers .github workflows fail CI if a governed surface claims unconditional Lambda uniqueness; "
              "this repository is a governed surface and now enforces the same rule on its own receipts and docs"),
  "what_the_guard_cannot_do": ("it checks language, not truth. it reports evidence of a claimed backing, not a re-run "
                               "of the Lean kernel - the same limitation the estate's own workflow states about "
                               "itself."),
  "status": "MEASURED"}, indent=2), encoding="utf-8")
print("RECEIPT out/phrasing_guard.json")
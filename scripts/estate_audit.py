import json, re, subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\Users\steph\szl-estate")
HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
TEXT = {".md", ".py", ".json", ".yml", ".yaml", ".toml", ".lean", ".ts", ".txt", ".cff"}
repos = sorted([p for p in ROOT.iterdir() if p.is_dir() and (p / ".git").exists()])

def files(r):
    return [p for p in r.rglob("*") if p.is_file() and ".git" not in p.parts and p.suffix.lower() in TEXT]

def read(p):
    try:
        return p.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return ""

P = {}

# pass 1: inventory
inv = {}
for r in repos:
    fs = files(r)
    sha = subprocess.run(["git","rev-parse","--short","HEAD"], cwd=r, capture_output=True, text=True).stdout.strip()
    inv[r.name] = {"head": sha, "files": len(fs),
                   "lines": sum(len(read(p).splitlines()) for p in fs[:400])}
P["1_inventory"] = {"repos": len(repos), "detail": inv}

# pass 2: honesty-state vocabulary
STATES = ("MEASURED", "BLOCKED", "UNAVAILABLE", "UNSIGNED_HONEST", "INVALID", "FAILED", "PROMOTED",
          "SOFTWARE_EMULATED", "SURROGATE", "BLIND-SPOT", "UNKNOWN", "REVIEW")
vocab = {}
for r in repos:
    blob = " ".join(read(p) for p in files(r)[:200])
    c = {s: len(re.findall(r"\b" + re.escape(s) + r"\b", blob)) for s in STATES}
    vocab[r.name] = {k: v for k, v in c.items() if v}
P["2_honesty_vocabulary"] = {"per_repo": vocab,
    "totals": dict(Counter({s: sum(v.get(s, 0) for v in vocab.values()) for s in STATES}).most_common())}

# pass 3: the Lambda naming collision
lam = {}
for r in repos:
    hits = {"weighted_geometric": 0, "equal_weight": 0, "egyptian": 0, "A1-A4_only": 0, "A5_or_perm": 0,
            "conjecture_1": 0}
    for p in files(r)[:200]:
        s = read(p)
        hits["weighted_geometric"] += len(re.findall(r"weighted\s+geometric", s, re.I))
        hits["equal_weight"] += len(re.findall(r"equal[- ]weight", s, re.I))
        hits["egyptian"] += len(re.findall(r"egyptian", s, re.I))
        hits["A1-A4_only"] += len(re.findall(r"A1[-\u2013 ]*A4", s))
        hits["A5_or_perm"] += len(re.findall(r"A5|permutation[- ]invarian", s, re.I))
        hits["conjecture_1"] += len(re.findall(r"Conjecture\s*1", s, re.I))
    if any(hits.values()):
        lam[r.name] = hits
P["3_lambda_naming"] = {"per_repo": lam,
  "finding": ("szl-lambda-gate describes itself as a weighted geometric mean with A1-A4 self-checks, so the estate's "
              "own flagship aggregator is not the thesis Lambda either - the thesis defines Lambda as the equal-weight "
              "geometric mean and A5 is permutation invariance. puriq-live already carries the correct vocabulary, "
              "Symmetric versus Egyptian Lambda. this repository's aggregator reproduces the estate kernel rather than "
              "deviating from it, and neither is Lambda.")}

# pass 4: locked-count evidence tally
lock = {}
for r in repos:
    for p in files(r)[:300]:
        s = read(p)
        for m in re.finditer(r"locked[^\n]{0,40}?\b(five|eight|5|8|21)\b", s, re.I):
            lock.setdefault(r.name, Counter())[m.group(1).lower()] += 1
P["4_locked_count_evidence"] = {"per_repo": {k: dict(v) for k, v in lock.items()},
  "state": "UNRESOLVED",
  "note": ("this repository asserts no count. the evidence is tallied only: szl-formulas states 21 canonical with "
           "locked-proven exactly 8, lutar-lean carries the theorem locked_count_eight, anatomy states 8 proven "
           "formulas, and thesis v24's binding honesty doctrine states exactly five. four sources to one, and the one "
           "is the most recent, which is why this stays unresolved rather than settled by majority.")}

# pass 5: bounded-loop and invariant claims
loop = {}
for r in repos:
    blob = " ".join(read(p) for p in files(r)[:200])
    loop[r.name] = {k: len(re.findall(v, blob, re.I)) for k, v in
                    {"loop_tax": r"loop[- ]tax", "well_founded": r"well[- ]founded",
                     "fixed_point": r"fixed[- ]?point", "cap": r"\bcap\b",
                     "invariant_count_8": r"\b8 (?:falsifiable )?(?:receipt )?invariants\b"}.items()}
P["5_bounded_loop"] = {"per_repo": {k: v for k, v in loop.items() if any(v.values())},
  "finding": ("szl-ouroboros is described as bounded loop-tax accounting and lutar-lean proves loop boundedness as "
              "contraction to a unique fixed point. a per-pass cap is neither, which is why I5 here is "
              "FAIL_BY_DEFINITION.")}

# pass 6: archived duplicates and canonical pointers
canon = {}
for r in repos:
    for p in list(r.glob("README*")) + list(r.glob(".github/**/*.md")):
        s = read(p)
        m = re.search(r"(ARCHIVED|DEPRECATED)[^\n]{0,160}?Canonical:?\s*(\S+)", s, re.I)
        if m:
            canon[r.name] = {"state": m.group(1).upper(), "canonical": m.group(2)}
P["6_canonical_pointers"] = canon

# pass 7: receipt schema convergence
sch = Counter()
for r in repos:
    for p in files(r)[:300]:
        for m in re.finditer(r'"schema"\s*:\s*"([^"]+)"', read(p)):
            sch[m.group(1)] += 1
P["7_receipt_schemas"] = {"distinct": len(sch), "top": dict(sch.most_common(25))}

# pass 8: cross-repo contradictions on supply-chain level
slsa = {}
for r in repos:
    blob = " ".join(read(p) for p in files(r)[:200])
    slsa[r.name] = {k: len(re.findall(v, blob, re.I)) for k, v in
                    {"L1_honest": r"SLSA\s*L1", "L2_roadmap": r"L2\s*roadmap",
                     "L2_claimed": r"SLSA\s*L1\+L2|SLSA\s*L2\s*(?:verified|achieved)",
                     "L3": r"SLSA\s*L3"}.items()}
contra = {k: v for k, v in slsa.items() if v["L2_claimed"]}
P["8_supply_chain_contradiction"] = {"repos_claiming_L1_plus_L2": contra,
  "note": ("uds-bundles states SLSA L1+L2 while thesis v24 corrects the estate to L1 honest, L2 roadmap and "
           "explicitly does not claim L2-verified. this is a live cross-repo contradiction and is reported, not "
           "resolved here.")}

# pass 9: adoption coverage versus this repo's completion audit
try:
    ca = json.loads(Path("out/completion_audit.json").read_text(encoding="utf-8-sig"))
    reviewed = {x["artifact"].split("/")[-1].lower() for x in ca["artifacts"]}
except Exception:
    reviewed = set()
present = {r.name.lower() for r in repos}
P["9_audit_coverage"] = {"estate_public_repos": len(present), "reviewed_in_completion_audit": len(reviewed & present),
  "never_reviewed": sorted(present - reviewed),
  "note": "the completion audit judged a fraction of the estate; everything below was never assessed"}

# pass 10: what this audit cannot see
P["10_limits"] = {"private_repos_not_cloned": ["szl-safe-stack", "szl-estate-os", "szl-org-health", "szl-v14",
                                               "szl-defensive-control-plane", "gdw-frontier", "pitch-collateral"],
  "shallow_clones": "depth 1, so history and CI logs are not audited",
  "text_only": "binary artefacts, weights and images are not read",
  "no_execution": "nothing was run; no claim here is a behavioural verification",
  "honest_state": "this is an inventory and a language audit, not a proof of anything"}

Path("out/estate_audit.json").write_text(json.dumps(
 {"schema": "szl.estate-audit/v1", "commit": HEAD, "org": "szl-holdings",
  "public_repos_cloned": len(repos), "passes": 10, "audit": P, "status": "MEASURED"}, indent=2), encoding="utf-8")

md = ["# Estate audit", "", "`szl-holdings` - " + str(len(repos)) + " public repos cloned, ten passes.", "",
      "## The Lambda naming collision", "", P["3_lambda_naming"]["finding"], "",
      "## Locked count", "", P["4_locked_count_evidence"]["note"], "",
      "## Bounded loop", "", P["5_bounded_loop"]["finding"], "",
      "## Supply-chain contradiction", "", P["8_supply_chain_contradiction"]["note"], "",
      "## Never reviewed by the completion audit", ""]
md += ["- " + x for x in P["9_audit_coverage"]["never_reviewed"]]
md += ["", "## What this audit cannot see", ""] + ["- " + k + ": " + str(v) for k, v in P["10_limits"].items()]
Path("docs/ESTATE_AUDIT.md").write_text("\n".join(md), encoding="utf-8")

print("repos " + str(len(repos)) + "   schemas " + str(P["7_receipt_schemas"]["distinct"]) +
      "   never reviewed " + str(len(P["9_audit_coverage"]["never_reviewed"])) +
      "   L1+L2 contradictions " + str(len(contra)))
print("RECEIPT out/estate_audit.json   DOC docs/ESTATE_AUDIT.md")
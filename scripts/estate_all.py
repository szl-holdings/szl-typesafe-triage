import json, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage.providers.registry import REGISTRY, TRUST_CEILING, apply_ceiling, ouroboros_pass

HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()

def rd(p):
    q = Path(p)
    try:
        return json.loads(q.read_text(encoding="utf-8-sig")) if q.exists() else None
    except Exception:
        return None

# ---- advisor registry receipt ----
named = {}
for f in ("out/jev_integrity_trial.json", "out/state_estimation.json", "out/integrity_seam.json"):
    d = rd(f)
    if d:
        blob = json.dumps(d)
        for a in REGISTRY:
            if a.repo in blob:
                named.setdefault(a.repo, []).append(f)

rows = [{"repo": a.repo, "organ": a.organ, "role": a.role, "tags": list(a.tags),
         "may_label": a.may_label, "may_lower_axis": a.may_lower_axis, "may_propose": a.may_propose,
         "loadable": a.loadable, "honesty_state": "MEASURED" if a.repo in named else "UNWIRED",
         "evidence": named.get(a.repo, [])} for a in REGISTRY]
loop = ouroboros_pass(REGISTRY, cap=4)
print("ADVISOR REGISTRY")
for r in rows:
    print("  " + r["repo"].ljust(40) + r["organ"].ljust(14) + r["honesty_state"].ljust(10) +
          ("loadable" if r["loadable"] else "NOT LOADABLE"))
print("  ceiling " + str(TRUST_CEILING) + "  (1.0 reported as " + str(apply_ceiling(1.0)) + ")   labels permitted " +
      str(loop["labels_permitted"]))
Path("out/advisor_registry.json").write_text(json.dumps(
 {"schema": "szl.advisor-registry/v1", "commit": HEAD, "advisors": rows,
  "trust_ceiling": TRUST_CEILING, "ouroboros_pass": loop,
  "principle": ("every candidate model is already tagged with the authority it does not have; this registry enforces "
                "those tags instead of documenting them. no advisor may return a label - a property of the type, not "
                "a setting."),
  "ceiling_source": "WILLAY - conscience, not an organ; refusals are tamper-evident, not tamper-proof",
  "wiring_state": "nothing loads a model; an advisor stays UNWIRED until a measurement receipt names it",
  "excluded": [a.repo for a in REGISTRY if not a.loadable],
  "status": "MEASURED"}, indent=2), encoding="utf-8")

# ---- completion audit ----
Y, Q = rd("out/yarqa_compartments.json"), rd("out/open_questions.json")
INV = {i["id"]: i["state"] for i in (Y or {}).get("invariants_i1_i8", [])}
not_pass = {k: v for k, v in INV.items() if v != "PASS"}
A = []
def a(repo, kind, gap, target, decision, reason):
    A.append({"artifact": repo, "kind": kind, "gap_it_closes": gap, "target": target,
              "decision": decision, "reason": reason})

a("SZLHOLDINGS/szl-calibration", "service", "advisor probabilities are UNVERIFIED", "Q2", "ADOPT_NOW",
  "exact ECE, MCE, Brier, NLL and AUROC with hash-chained receipts - the only component that can settle whether a "
  "probability means what it says")
a("SZLHOLDINGS/szl-invariants", "kernel", "I1-I8 evaluated by my local imitation, not the authoritative executor",
  "I1..I8", "ADOPT_NOW", "the published suite never coerces statuses, which is the property my pre-check imitates")
a("SZLHOLDINGS/szl-lambda-gate", "kernel", "the aggregator is reimplemented inline here",
  "duplicate Lambda", "ADOPT_NOW",
  "the cross-check already showed exact agreement over 1270 rows, so the swap is behaviour-preserving")
a("SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora", "LoRA (private)", "no model sits in the decision path",
  "I3,Q6", "ADOPT_NOW", "refusal-preserving triage adapter; the sovereign replacement for the hosted advisor")
a("SZLHOLDINGS/khipu-r3", "LoRA", "the integrity axis needs an abstaining provider", "I3,Q6", "ADOPT_NOW",
  "abstain-retrain is exactly the veto-only shape the seam requires")
a("SZLHOLDINGS/szl-govsign", "kernel", "signing is hand-rolled rather than the shared primitive", "I4,I6",
  "ADOPT_NEXT", "adopting it makes the ledger joinable to szl-lake instead of private")
a("SZLHOLDINGS/szl-provctl", "kernel", "receipts name a commit but carry no build provenance", "I8", "ADOPT_NEXT",
  "flywheel-lineage is PARTIAL because lineage stops at a commit string")
a("SZLHOLDINGS/szl-ouroboros", "kernel", "the per-pass cap is a local integer, not accounted loop tax", "I5",
  "ADOPT_NEXT", "I5 currently passes on a cap I invented")
a("SZLHOLDINGS/szl-blocked", "kernel", "BLOCKED is a local label with no regulatory mapping", "publication",
  "ADOPT_NEXT", "EU AI Act Annex IV mapping turns BLOCKED states into filings rather than notes")
a("SZLHOLDINGS/brain-navigator-r2", "LoRA", "the handles-only lane has no retriever", "Q1", "ADOPT_NEXT",
  "grounded-only retrieval feeds the vocabulary-gap lane without ever labelling")
a("SZLHOLDINGS/MiniEmbed-Nano", "numpy embedding", "retrieval ranks by token overlap only", "Q1", "ADOPT_NEXT",
  "a local embedding keeps the lane air-gapped; cosine is no more correctness than overlap")
a("SZLHOLDINGS/ReceiptAgent-Nano", "fixture", "receipt tests use fixtures I wrote today", "test independence",
  "ADOPT_NEXT", "an estate-published fixture is a stronger witness than one authored beside the code it checks")
a("SZLHOLDINGS/szl-nemo", "doctrine gate", "training corpora are gated by local scripts", "corpus gating",
  "ADOPT_NEXT", "szl-forge already gates training JSONL through the nemo doctrine gate")
a("SZLHOLDINGS/A11OY-MINI", "GGUF", "no local generative fallback", "Q6", "DEFER",
  "useful as a CPU comparison arm, but khipu-r3 is purpose-trained for abstention and goes first")
a("SZLHOLDINGS/szl-formulas", "kernel", "this repo makes no formula claim and should not start", "-", "DEFER",
  "adopting it would tempt an F-number claim; F18 is Reed-Solomon parity, not a DSSE seal")
a("SZLHOLDINGS/Moons-Nano", "toy classifier", "none", "-", "DEFER", "no triage relevance; listing it would be padding")
for repo, why in (("SZLHOLDINGS/YARQA-ATTN", "attention kernel; no attention in a deterministic policy engine"),
                  ("SZLHOLDINGS/szl-block-kv", "paged KV cache; nothing here serves tokens"),
                  ("SZLHOLDINGS/szl-maskmod", "block-sparse masks; no attention to mask"),
                  ("SZLHOLDINGS/szl-receipt-attn", "tiled fused attention; same"),
                  ("SZLHOLDINGS/szl-governed-norm", "deprecated by szl-lambda-gate on its own card"),
                  ("SZLHOLDINGS/oac-system-health-v1", "operations observability, unrelated domain"),
                  ("SZLHOLDINGS/KILLINCHU-EYE", "counter-UAS alias, no triage surface"),
                  ("SZLHOLDINGS/SZLHOLDINGS", "org stub, explicitly not a model")):
    a(repo, "excluded", "none", "-", "EXCLUDE", why)

counts = {}
for x in A:
    counts[x["decision"]] = counts.get(x["decision"], 0) + 1
print("")
print("COMPLETION AUDIT  " + json.dumps(counts))
for x in [y for y in A if y["decision"] == "ADOPT_NOW"]:
    print("  ADOPT_NOW  " + x["artifact"].ljust(42) + "-> " + x["target"])
print("  invariants not PASS: " + json.dumps(not_pass))
Path("out/completion_audit.json").write_text(json.dumps(
 {"schema": "szl.completion-audit/v1", "commit": HEAD, "artifacts_reviewed": len(A),
  "decision_counts": counts, "invariants_not_passing": not_pass,
  "open_question_count": (Q or {}).get("count"),
  "rule": ("an artefact is adopted only against a named invariant or open question; one with no gap to close is "
           "EXCLUDE with a stated reason, never a maybe"),
  "what_would_make_us_whole": ("five of eight invariants reach PASS through adoption; I3 needs a model actually in "
                               "the decision path; Q2 needs calibration. nothing on this list makes the engine "
                               "classify correctly - that remains the vocabulary and recall problem."),
  "artifacts": A, "status": "MEASURED"}, indent=2), encoding="utf-8")
lines = ["# Completion audit", "", "At `" + HEAD + "`. " + str(len(A)) + " artefacts, each judged against a gap.", ""]
for d in ("ADOPT_NOW", "ADOPT_NEXT", "DEFER", "EXCLUDE"):
    grp = [x for x in A if x["decision"] == d]
    lines += ["## " + d + " (" + str(len(grp)) + ")", ""]
    for x in grp:
        lines += ["- **" + x["artifact"] + "** (" + x["kind"] + ") -> `" + x["target"] + "`  ", "  " + x["reason"]]
    lines.append("")
Path("docs/COMPLETION_AUDIT.md").write_text("\n".join(lines), encoding="utf-8")

# ---- corpus digest from the local clone ----
ROOT = Path(r"C:\Users\steph\szl-papers")
if not ROOT.exists():
    print("")
    print("CORPUS MISSING at " + str(ROOT) + " - digest skipped")
else:
    PHEAD = subprocess.run(["git","rev-parse","--short","HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    ORDER = ["thesis", "preprints", "papers", "prior-art", "bounty", "drafts", "investor"]
    EXT = {".md", ".tex", ".bib", ".cff", ".json", ".txt"}
    CLAIM = re.compile(r"^\s*(?:\\begin\{(?:theorem|lemma|definition|axiom|conjecture|proposition|corollary)\}|"
                       r"(?:\*\*)?(?:Theorem|Lemma|Definition|Axiom|Conjecture|Proposition|Corollary|A[1-9])\b)", re.I)
    ABS = re.compile(r"^\s*(?:##+\s*abstract|\\begin\{abstract\}|abstract\s*[:.]?\s*$)", re.I)
    DOI = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
    docs = [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts and p.suffix.lower() in EXT]
    docs.sort(key=lambda p: (ORDER.index(p.relative_to(ROOT).parts[0])
                             if p.relative_to(ROOT).parts[0] in ORDER else len(ORDER), str(p).lower()))
    print("")
    print("=== CORPUS DIGEST  szl-papers @ " + PHEAD + "   " + str(len(docs)) + " documents ===")
    emitted, digest = 0, []
    for p in docs:
        if emitted > 700:
            print("... cap reached")
            break
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        try:
            text = p.read_text(encoding="utf-8-sig", errors="replace")
        except Exception:
            continue
        L = text.splitlines()
        outline = [x.strip()[:150] for x in L if x.strip().startswith("#") or x.strip().startswith("\\section")][:7]
        claims, grab, n = [], 0, 0
        for i, x in enumerate(L):
            if ABS.match(x):
                grab = 7; claims.append(">> ABSTRACT"); continue
            if grab and x.strip():
                claims.append("   " + x.strip()[:170]); grab -= 1; continue
            if CLAIM.match(x):
                claims.append(">> " + x.strip()[:170])
                for j in range(1, 3):
                    if i + j < len(L) and L[i + j].strip():
                        claims.append("   " + L[i + j].strip()[:170])
                n += 1
                if n >= 5:
                    break
        dois = sorted(set(DOI.findall(text)))
        print("")
        print("--- " + rel + "  (" + str(len(L)) + " lines)")
        for b in (outline + claims)[:30]:
            print("    " + b); emitted += 1
        if dois:
            print("    DOIs: " + ", ".join(dois[:6]))
        digest.append({"path": rel, "lines": len(L), "outline": outline, "claims": claims[:30], "dois": dois[:8]})
    Path("out/corpus_digest.json").write_text(json.dumps(
     {"schema": "szl.corpus-digest/v1", "papers_commit": PHEAD, "documents": len(digest),
      "extraction": "outline, abstract and first axiom/theorem/lemma/definition/conjecture statements per file",
      "honesty": "this is an extraction, not a summary; nothing here is paraphrased", "docs": digest},
     indent=2), encoding="utf-8")
    print("")
    print("RECEIPT out/corpus_digest.json")
print("DONE")
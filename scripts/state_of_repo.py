import json, subprocess
from pathlib import Path

HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()

def rd(p):
    q = Path(p)
    try:
        return json.loads(q.read_text(encoding="utf-8-sig")) if q.exists() else None
    except Exception:
        return None

RUN = rd("out/pipeline_run.json") or {}
stages = RUN.get("stages") or RUN.get("results") or []
failed = [s for s in stages if str(s.get("status", s.get("state", ""))).upper() not in ("PASS", "OK", "SKIP")]
print("PIPELINE DIAGNOSIS  " + str(RUN.get("passed", "?")) + "/" + str(RUN.get("total", len(stages))))
for s in failed:
    print("  FAILED " + str(s.get("id", s.get("stage"))).ljust(14) + str(s.get("status", s.get("state"))).ljust(12) +
          str(s.get("produces", s.get("artifact", "")))[:60])
    for k in ("error", "stderr", "detail", "message"):
        if s.get(k):
            print("         " + str(s[k]).replace("\n", " ")[:300])
missing = [a for a in (s.get("produces") or s.get("artifact") for s in stages) if a and not Path(a).exists()]
print("  missing artefacts: " + json.dumps(missing[:12]))

AX, Y, Q = rd("out/axiom_conformance.json"), rd("out/yarqa_compartments.json"), rd("out/open_questions.json")
CA, SC = rd("out/completion_audit.json"), rd("out/ratified_scoreboard.json")
INV = {i["id"]: i["state"] for i in (Y or {}).get("invariants_i1_i8", [])}

BANDAIDS = [
 {"id": "B1", "bandaid": "invariants I1-I8 are evaluated by a local imitation of the estate suite",
  "why_it_is_a_bandaid": "the authoritative executor is szl-invariants; my version cannot fail the way theirs does",
  "fix": "adopt SZLHOLDINGS/szl-invariants (already ADOPT_NOW in the completion audit)"},
 {"id": "B2", "bandaid": "I5 reported PASS on a per-pass candidate cap",
  "why_it_is_a_bandaid": "the thesis defines bounded as a well-founded measure strictly decreasing per step; a cap is not one",
  "fix": "measure = count of unratified vocabulary-gap candidates; already recorded FAIL_BY_DEFINITION"},
 {"id": "B3", "bandaid": "the aggregator is reimplemented inline instead of imported from szl-lambda-gate",
  "why_it_is_a_bandaid": "two implementations of the estate's flagship rule can drift silently",
  "fix": "import the kernel; the cross-check already showed exact agreement over 1270 rows"},
 {"id": "B4", "bandaid": "signing is hand-rolled rather than szl-govsign, and receipts carry a commit string as lineage",
  "why_it_is_a_bandaid": "the ledger is private rather than joinable to szl-lake, and I8 is PARTIAL because lineage stops at a commit",
  "fix": "szl-govsign plus szl-provctl"},
 {"id": "B5", "bandaid": "the Gaussian posterior in the Kalman fusion sits on a quantity bounded in [0,1]",
  "why_it_is_a_bandaid": "the approximation is wrong near the edges and some intervals leave the unit interval",
  "fix": "Beta-Binomial posterior, already named in the receipt as the exact next step"},
 {"id": "B6", "bandaid": "state estimation and the advisor probe are advisory stages needing a network key",
  "why_it_is_a_bandaid": "the pipeline completes without them, so a green pipeline does not mean they ran",
  "fix": "either a sovereign local adapter (khipu-r3 / the triage LoRA) or an explicit RED state when the key is absent"},
 {"id": "B7", "bandaid": "test fixtures and red-team probes were authored beside the code they check",
  "why_it_is_a_bandaid": "a witness I wrote cannot independently falsify me",
  "fix": "ReceiptAgent-Nano fixtures and externally ratified probes"},
 {"id": "B8", "bandaid": "42 ratified rows carry the vocabulary judgement for the whole corpus",
  "why_it_is_a_bandaid": "effective n is small and the 9-of-12 resistance rests on it",
  "fix": "grow the ratified set; the state-estimation interval quantifies the current doubt rather than hiding it"}]

GAPS = [
 {"id": "G1", "gap": "no model is in the decision path", "blocks": "I3 UNAVAILABLE, Q6",
  "closes_with": "SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora or khipu-r3"},
 {"id": "G2", "gap": "advisor probabilities are uncalibrated", "blocks": "Q2",
  "closes_with": "SZLHOLDINGS/szl-calibration - ECE, MCE, Brier, NLL, AUROC with receipts"},
 {"id": "G3", "gap": "the engine matches vocabulary, not meaning", "blocks": "Q1 and the headline capability",
  "closes_with": "nothing on the adoption list; this is the recall and vocabulary problem and stays open"},
 {"id": "G4", "gap": "the aggregator violates A5 and is therefore outside Theorem 4.3's uniqueness",
  "blocks": "any claim that this engine instantiates Lambda",
  "closes_with": "equal weights (making it Lambda, satisfying A5, falling under the sorry-free theorem) with tau re-derived and measured against the ratified 42 - an experiment, not a rename"},
 {"id": "G5", "gap": "BLOCKED is a local label with no regulatory mapping", "blocks": "publication as a filing",
  "closes_with": "SZLHOLDINGS/szl-blocked, EU AI Act Annex IV"},
 {"id": "G6", "gap": "locked-formula count disagrees between thesis v23 (five) and the kernel cards (the locked set (this repository asserts no count; both readings are in out/phrasing_guard.json))",
  "blocks": "any F-number claim from this repo", "closes_with": "estate reconciliation; this repo makes no count claim"}]

doc = ["# State of the repository", "",
       "At `" + HEAD + "`. Release **BLOCKED at 11/12**. Pipeline " + str(RUN.get("passed", "?")) + "/" +
       str(RUN.get("total", len(stages))) + ".", "",
       "## What is measured", ""]
for k, v in sorted(INV.items()):
    doc.append("- " + k + ": " + v)
doc += ["", "## Bandaids (working, not right)", ""]
for b in BANDAIDS:
    doc += ["- **" + b["id"] + "** " + b["bandaid"] + "  ", "  " + b["why_it_is_a_bandaid"] + "  ",
            "  fix: " + b["fix"]]
doc += ["", "## Gaps (not worked around, open)", ""]
for g in GAPS:
    doc += ["- **" + g["id"] + "** " + g["gap"] + "  ", "  blocks: " + g["blocks"] + "  ",
            "  closes with: " + g["closes_with"]]
doc += ["", "## The one sentence that must survive review", "",
        "This repository demonstrates a method - a deployed system measured against its own project's axiom system, "
        "reporting the axiom it violates - and does not demonstrate a working classifier. The two claims are kept "
        "separate on purpose."]
Path("docs/STATE_OF_THE_REPO.md").write_text("\n".join(doc), encoding="utf-8")

Path("out/state_of_repo.json").write_text(json.dumps(
 {"schema": "szl.state-of-repo/v1", "commit": HEAD,
  "release": "BLOCKED 11/12", "pipeline": {"passed": RUN.get("passed"), "total": RUN.get("total", len(stages)),
                                            "failed_stages": [str(s.get("id", s.get("stage"))) for s in failed]},
  "invariants": INV, "bandaids": BANDAIDS, "gaps": GAPS,
  "ratified_rows": (SC or {}).get("ratified_rows"),
  "adopt_now": [x["artifact"] for x in (CA or {}).get("artifacts", []) if x["decision"] == "ADOPT_NOW"],
  "open_questions": (Q or {}).get("count"),
  "novelty_claim": ("methodological, not capability: a running system checked against its own project's axiom system "
                    "that reported the failing axiom instead of adjusting the report. eleven self-corrections are "
                    "recorded in receipts rather than in prose."),
  "non_claim": ("this engine does not classify correctly, aggregates with a rule that violates A5, and is not the "
                "Lutar invariant. no F-number claim is made. locked-formula counts are left to the estate."),
  "a5_violations": (AX or {}).get("violations", {}).get("A5_permutation_invariance"),
  "status": "MEASURED"}, indent=2), encoding="utf-8")
print("")
print("bandaids " + str(len(BANDAIDS)) + "   gaps " + str(len(GAPS)) + "   RECEIPT out/state_of_repo.json")
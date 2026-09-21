"""Completion audit: which estate artefacts close which named gap.

Every entry names the invariant or open question it would close. An artefact with no gap to
close is EXCLUDE with a reason, not a maybe. Decisions are ADOPT_NOW (closes a gap with work
already scoped), ADOPT_NEXT (closes a gap, needs a prerequisite), DEFER (useful, no current
gap), EXCLUDE (no applicability, stated).
"""
import json, subprocess
from pathlib import Path

HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()

def rd(p):
    q = Path(p)
    try:
        return json.loads(q.read_text(encoding="utf-8-sig")) if q.exists() else None
    except Exception:
        return None

Y, Q, R = rd("out/yarqa_compartments.json"), rd("out/open_questions.json"), rd("out/advisor_registry.json")
INV = {i["id"]: i for i in (Y or {}).get("invariants_i1_i8", [])}
open_states = {i: INV[i]["state"] for i in INV if INV[i]["state"] != "PASS"}

A = []
def a(repo, kind, gap, target, decision, reason):
    A.append({"artifact": repo, "kind": kind, "gap_it_closes": gap, "target": target,
              "decision": decision, "reason": reason})

# --- kernels that close invariant gaps -------------------------------------------------
a("SZLHOLDINGS/szl-invariants", "kernel (Kernel Hub)",
  "I1-I8 are evaluated by my local pre-check, not by the authoritative executor",
  "I1,I2,I3,I4,I5,I6,I7,I8", "ADOPT_NOW",
  "get_kernel with trust_remote_code, run the published suite, replace my approximation. the card states "
  "statuses are never coerced, which is the property my pre-check imitates")
a("SZLHOLDINGS/szl-lambda-gate", "kernel (torch surrogate)",
  "the aggregator is reimplemented inline in this repo instead of imported",
  "duplication of the canonical Lambda", "ADOPT_NOW",
  "the cross-check already showed exact agreement over 1270 rows, so swapping my inline wgm for the published "
  "kernel is behaviour-preserving and removes a second implementation of the estate's flagship formula")
a("SZLHOLDINGS/szl-govsign", "kernel (DSSE/in-toto)",
  "signing is hand-rolled with cryptography rather than the shared primitive",
  "I4,I6", "ADOPT_NEXT",
  "my ECDSA P-256 chain verifies offline, but szl-receipt and szl-govsign are the estate primitives; adopting them "
  "makes the ledger joinable to szl-lake instead of private")
a("SZLHOLDINGS/szl-provctl", "kernel (in-toto/SLSA)",
  "receipts name a commit but carry no build provenance",
  "I8", "ADOPT_NEXT", "flywheel-lineage is PARTIAL because lineage stops at a commit string")
a("SZLHOLDINGS/szl-ouroboros", "kernel (loop-tax)",
  "the per-pass cap is a local integer rather than accounted loop tax",
  "I5", "ADOPT_NEXT", "I5 passes on a homemade cap; the kernel is the accounted version")
a("SZLHOLDINGS/szl-blocked", "kernel (EU AI Act Annex IV)",
  "BLOCKED is a local label with no regulatory mapping",
  "publication readiness", "ADOPT_NEXT",
  "the claims ledger already emits BLOCKED states; Annex IV mapping turns them into filings rather than notes")
a("SZLHOLDINGS/szl-formulas", "kernel (21 formulas, the locked set (this repository asserts no count; both readings are in out/phrasing_guard.json))",
  "this repo makes no formula claim and should not start",
  "-", "DEFER",
  "adopting it would tempt an F-number claim. a-11-oy.com warns F18 is Reed-Solomon parity and not a DSSE seal")

# --- models that close capability gaps -------------------------------------------------
a("SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora", "LoRA adapter (private)",
  "no model sits in the decision path; the integrity axis detects nothing",
  "I3,Q6", "ADOPT_NOW",
  "refusal-preserving triage adapter on Qwen3.5-0.8B modified today. wired through the existing seam it is the "
  "sovereign replacement for the hosted advisor")
a("SZLHOLDINGS/khipu-r3", "LoRA adapter",
  "the integrity axis needs an abstaining provider, not a labelling one",
  "I3,Q6", "ADOPT_NOW",
  "abstain-retrain is exactly the veto-only shape the seam requires; already in the advisor registry as UNWIRED")
a("SZLHOLDINGS/brain-navigator-r2", "LoRA adapter",
  "the handles-only lane has no retriever",
  "Q1", "ADOPT_NEXT",
  "grounded-only retrieval feeds the vocabulary-gap lane without ever labelling")
a("SZLHOLDINGS/MiniEmbed-Nano", "numpy embedding silhouette",
  "retrieval currently ranks by token overlap only",
  "Q1", "ADOPT_NEXT",
  "a local embedding with no network keeps the lane air-gapped; overlap is never correctness and neither is cosine")
a("SZLHOLDINGS/A11OY-MINI", "GGUF (llama.cpp)",
  "no local generative fallback exists for the advisory role",
  "Q6", "DEFER",
  "useful as a CPU comparison arm, but khipu-r3 is purpose-trained for abstention and goes first")
a("SZLHOLDINGS/ReceiptAgent-Nano", "numpy test fixture",
  "receipt tests use fixtures I wrote today",
  "test independence", "ADOPT_NEXT",
  "an estate-published fixture is a stronger witness than one authored alongside the code it checks")
a("SZLHOLDINGS/TinyKhipu-Nano", "numpy test fixture", "same", "test independence", "ADOPT_NEXT",
  "second independent fixture for the chain tests")
a("SZLHOLDINGS/Moons-Nano", "numpy MLP silhouette", "none", "-", "DEFER",
  "a toy classifier with no triage relevance; listing it as useful would be padding")
a("SZLHOLDINGS/szl-nemo", "doctrine rule_check surrogate",
  "training corpora are gated by scripts in this repo",
  "corpus gating", "ADOPT_NEXT",
  "szl-forge already gates training JSONL through the nemo doctrine gate; the distillation corpus should pass the "
  "same gate rather than a local one")
a("SZLHOLDINGS/szl-calibration", "service (ECE/MCE/Brier/NLL/AUROC)",
  "advisor probabilities are UNVERIFIED",
  "Q2", "ADOPT_NOW",
  "the only component that can settle whether a probability means what it says; exact metrics with hash-chained "
  "receipts, which is precisely what the open question asks for")

# --- excluded with reasons -------------------------------------------------------------
for repo, why in (("SZLHOLDINGS/YARQA-ATTN", "attention kernel; there is no attention in a deterministic policy engine"),
                  ("SZLHOLDINGS/szl-block-kv", "paged KV cache; nothing here serves tokens"),
                  ("SZLHOLDINGS/szl-maskmod", "score_mod and block-sparse masks; no attention to mask"),
                  ("SZLHOLDINGS/szl-receipt-attn", "tiled fused attention; same"),
                  ("SZLHOLDINGS/szl-governed-norm", "deprecated by szl-lambda-gate on its own card"),
                  ("SZLHOLDINGS/oac-system-health-v1", "operations observability, unrelated to triage inputs"),
                  ("SZLHOLDINGS/oac-clinical-transport-health-v1", "clinical transport domain, unrelated"),
                  ("SZLHOLDINGS/waman", "roadmap placeholder, not a capability"),
                  ("SZLHOLDINGS/tinku", "roadmap placeholder"),
                  ("SZLHOLDINGS/qantu", "roadmap placeholder"),
                  ("SZLHOLDINGS/chakana", "roadmap placeholder"),
                  ("SZLHOLDINGS/KILLINCHU-EYE", "counter-UAS alias, no triage surface"),
                  ("SZLHOLDINGS/SZLHOLDINGS", "org stub, explicitly not a model")):
    a(repo, "excluded", "none", "-", "EXCLUDE", why)

counts = {}
for x in A:
    counts[x["decision"]] = counts.get(x["decision"], 0) + 1

print("completion audit: " + str(len(A)) + " artefacts")
for d in ("ADOPT_NOW", "ADOPT_NEXT", "DEFER", "EXCLUDE"):
    print("  " + d.ljust(12) + str(counts.get(d, 0)))
print("")
print("ADOPT_NOW, in order:")
for x in [y for y in A if y["decision"] == "ADOPT_NOW"]:
    print("  " + x["artifact"].ljust(42) + "-> " + x["target"])
print("")
print("invariants still not PASS: " + json.dumps(open_states))

Path("out/completion_audit.json").write_text(json.dumps(
 {"schema": "szl.completion-audit/v1", "commit": HEAD,
  "artifacts_reviewed": len(A), "decision_counts": counts,
  "invariants_not_passing": open_states,
  "open_question_count": (Q or {}).get("count"),
  "rule": ("an artefact is adopted only against a named invariant or open question. an artefact with no gap to "
           "close is EXCLUDE with a stated reason, never a maybe, so the audit cannot become a wish list."),
  "ordering": ("szl-calibration and szl-invariants first because they settle questions rather than add surface; "
               "then the triage adapter and khipu-r3 because I3 is the only invariant blocked on a missing "
               "capability rather than on plumbing; signing and provenance kernels after, since the local chain "
               "already verifies offline and the gain is joinability to szl-lake"),
  "artifacts": A,
  "what_would_make_us_whole": ("five of eight invariants would reach PASS by adopting szl-invariants, szl-govsign "
                              "and szl-provctl; I3 needs a model actually in the decision path, which is the "
                              "triage adapter or khipu-r3; Q2 needs szl-calibration. nothing on this list makes the "
                              "engine classify correctly - that remains the vocabulary and recall problem."),
  "status": "MEASURED"}, indent=2), encoding="utf-8")

lines = ["# Completion audit", "", "Generated at `" + HEAD + "`. " + str(len(A)) +
         " estate artefacts, each judged against a named gap.", ""]
for d in ("ADOPT_NOW", "ADOPT_NEXT", "DEFER", "EXCLUDE"):
    grp = [x for x in A if x["decision"] == d]
    lines += ["## " + d + " (" + str(len(grp)) + ")", ""]
    for x in grp:
        lines += ["- **" + x["artifact"] + "** — " + x["kind"] + "  ",
                  "  closes: " + x["gap_it_closes"] + " → `" + x["target"] + "`  ",
                  "  " + x["reason"]]
    lines.append("")
Path("docs/COMPLETION_AUDIT.md").write_text("\n".join(lines), encoding="utf-8")
print("RECEIPT out/completion_audit.json  DOC docs/COMPLETION_AUDIT.md")
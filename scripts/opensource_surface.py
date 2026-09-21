import json, subprocess
from pathlib import Path

HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
LK = json.loads(Path("out/leakage_gate.json").read_text(encoding="utf-8-sig")) if Path("out/leakage_gate.json").exists() else {}
B = json.loads(Path("out/bench/bench_summary.json").read_text(encoding="utf-8-sig"))

card = ["# Dataset card - szl-typesafe-triage distillation corpus", "",
  "> **Not admitted for training.** The estate doctrine in szl-frontier's CODEX synthesis requires that generated",
  "> datasets remain local evaluation artefacts with no training admission or Hub publication absent a rights,",
  "> contamination, quality and provenance decision. No such decision exists for this corpus.", "",
  "## Required fields (org template)", "",
  "- **Schema:** validated by the engine's policy loader. Evidence: `out/pipeline_run.json`",
  "- **Integrity:** hash-chained receipts. Evidence: `out/chain/triage-ledger.sha3.jsonl`",
  "- **Contamination or leakage:** **" + str(LK.get("verdict", "UNAVAILABLE")) + "**. Evidence: `out/leakage_gate.json`",
  "", "## Leakage detail", ""]
for k in ("rows", "template_families", "largest_family", "exact_duplicates_across_split",
          "max_char5gram_jaccard", "heldout_rows_flagged", "shared_template_families", "semantic_pass"):
    card.append("- " + k.replace("_", " ") + ": " + str(LK.get(k)))
card += ["", "## Known gaps and bias", "",
  "- Rows are template-generated; the predecessor adapter was vetoed at mean cross-split cosine 0.9792.",
  "- The semantic leakage pass is UNAVAILABLE here because no embedding model is loaded, and UNAVAILABLE is not clean.",
  "- The engine aggregates 4 axes; the doctrine gate is 13 axes and non-compensatory.",
  "", "## Lineage", "",
  "This repository succeeds a QUARANTINED predecessor: szl-nemo's historical TF-IDF and logistic-regression triage",
  "scorer, whose model.joblib is absent from the approved package path and is therefore not replayable from published",
  "bytes. A second attempt at a task whose first attempt was quarantined is a different claim from a first attempt."]
Path("docs/DATASET_CARD.md").write_text("\n".join(card), encoding="utf-8")

readme = ["# szl-typesafe-triage", "",
 "A deterministic, receipt-bearing triage engine, and an honest account of what it cannot do.", "",
 "**Read this first.** The engine does not yet perform triage by meaning; it matches vocabulary. The useful content",
 "of this repository is the measurement discipline: " + str(B.get("retractions")) + " retractions recorded in an",
 "append-only ledger, a phrasing guard that mirrors the estate's CI rule, and a leakage gate that refuses rather than",
 "advises. Release is **BLOCKED at 11/12**.", "",
 "## Measured, not asserted", "",
 "| Property | Value | Receipt |", "|---|---|---|",
 "| Canonical gate axes vs engine axes | " + str(B["gate_shape"]["canonical_axes"]) + " vs " +
   str(B["gate_shape"]["engine_axes"]) + " | `out/yuyay_gate_conformance.json` |",
 "| Compensation errors on the labelled eval split | " + str(B["gate_shape"]["compensation_errors"]) +
   " | `out/yuyay_gate_conformance.json` |",
 "| Ratified rows / effective n | " + str(B["ratified"]["rows"]) + " / " + str(B["ratified"]["effective_n"]) +
   " | `out/effective_n.json` |",
 "| Corpus leakage verdict | " + str(B["leakage"]["verdict"]) + " | `out/leakage_gate.json` |",
 "| Retractions, of which self-corrections | " + str(B.get("retractions")) + " | `out/retractions.json` |",
 "", "## What is not claimed", "",
 "- No winner, no baseline beaten, no comparison against any other system.",
 "- No kernel verification is performed here; Lean symbols are bound by name only (`out/lean_binding.json`).",
 "- Lambda is cited as Conjecture 1 and disproved as stated; conditional Theorem U is the proved result.",
 "- No locked-formula count is asserted; the estate's own sources disagree (`out/phrasing_guard.json`).",
 "- SLSA L1 honest, L2 roadmap. Not L2-verified, not L3, and no federal or hardened-image accreditation.",
 "", "## Audits in this repository", "",
 "- `docs/ESTATE_AUDIT.md` - ten passes over 88 public estate repositories",
 "- `docs/PRIVATE_AUDIT.md` - private-tier leads via authenticated code search",
 "- `docs/DEEP_FINDINGS.md` - why the predecessor adapter is NOT PROMOTABLE",
 "- `docs/STATE_OF_THE_REPO.md` - eight bandaids and six gaps, named",
 "- `docs/DATASET_CARD.md` - contamination field filled, per the org template",
 "", "Apache-2.0. Copyright 2026 SZL Holdings."]
Path("README.md").write_text("\n".join(readme), encoding="utf-8")
print("open-source surface written: README.md, docs/DATASET_CARD.md")
# Dataset card - szl-typesafe-triage distillation corpus

> **Not admitted for training.** The estate doctrine in szl-frontier's CODEX synthesis requires that generated
> datasets remain local evaluation artefacts with no training admission or Hub publication absent a rights,
> contamination, quality and provenance decision. No such decision exists for this corpus.

## Required fields (org template)

- **Schema:** validated by the engine's policy loader. Evidence: `out/pipeline_run.json`
- **Integrity:** hash-chained receipts. Evidence: `out/chain/triage-ledger.sha3.jsonl`
- **Contamination or leakage:** **REFUSED**. Evidence: `out/leakage_gate.json`

## Leakage detail

- rows: 628
- template families: 628
- largest family: 1
- exact duplicates across split: 0
- max char5gram jaccard: 0.8378
- heldout rows flagged: 45/314
- shared template families: 0
- semantic pass: UNAVAILABLE

## Known gaps and bias

- Rows are template-generated; the predecessor adapter was vetoed at mean cross-split cosine 0.9792.
- The semantic leakage pass is UNAVAILABLE here because no embedding model is loaded, and UNAVAILABLE is not clean.
- The engine aggregates 4 axes; the doctrine gate is 13 axes and non-compensatory.

## Lineage

This repository succeeds a QUARANTINED predecessor: szl-nemo's historical TF-IDF and logistic-regression triage
scorer, whose model.joblib is absent from the approved package path and is therefore not replayable from published
bytes. A second attempt at a task whose first attempt was quarantined is a different claim from a first attempt.
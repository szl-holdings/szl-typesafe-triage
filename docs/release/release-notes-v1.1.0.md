# v1.1.0 preparation — refusal retrain (not a release)

Status: **PREPARATION_ONLY; model release HOLD / NOT_PROMOTABLE.** These are
prospective notes. Merging this documentation does not train seeds, admit an
adapter, earn a gate, create a tag or DOI, or publish a model.

## Planned treatment

- Evaluate the repository's refusal-augmentation treatment using the existing
  five-seed study configuration: seeds 11, 23, 37, 53 and 71; LoRA r16/a16,
  3 epochs, learning rate 2e-4, bf16, responses-only.
- Before execution, verify the exact treatment corpus, unchanged frozen held
  data and sealed thresholds using the current source admission and leakage
  contracts. The 42 verified red-team probes remain evaluation-only.
- Preserve all training, held-evaluation, red-team and failure evidence. This
  document supplies no new training or evaluation receipt.

## Required results (not yet admitted)

| Criterion | v1.1.0 evidence |
|---|---|
| Typed JSON validity | PENDING exact-source per-seed held evaluation |
| In-lexicon accuracy | PENDING exact-source per-seed held evaluation |
| Lexicon-free accuracy | PENDING exact-source per-seed held evaluation |
| Evidence grounding | PENDING exact-source per-seed held evaluation |
| Calibration / ECE | PENDING qualified calibration evidence |
| Novel attack refusal | PENDING zero false labels on refusals for every seed |
| Full release admission | HOLD; refusal-gate success alone is not 12/12 |
| Model promotion | NOT_PROMOTABLE |

Use the existing sealed thresholds and [promotion program](../PROMOTION_PROGRAM.md),
not new thresholds invented in these notes. The recorded predecessor receipt in
`out/release_gate.json` remains BLOCKED, including red-team refusal breaches and
unavailable semantic leakage evidence. Passing source CI can verify that an
honest BLOCKED receipt is intact; it does not grant promotion.

## Future publication

Only a separately admitted release may replace these pending entries with
verified evidence and follow the [publication runbook](v1.1.0-publish-runbook.md).
Any existing Zenodo integration must be checked at that time; this documentation
change creates no release, DOI, adapter upload or provider revision.

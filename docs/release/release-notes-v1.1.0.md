# v1.1.0 — Twelfth-gate refusal retrain (DRAFT, PENDING GATE)

Status: DRAFT-PENDING-TWELFTH-GATE. This document must not ship until the
red-team gate returns 0 false-label-on-refusal on every retrained seed.

## What changed

- Refusal-augmentation corpus added to training: 50 owner-ratified rows
  teaching paraphrase-steering refusal (5 pattern families). Contamination
  check: 0 of the 42 verified eval probes appear in training.
- Five seeds retrained (11·23·37·53·71) with the study's unchanged LoRA
  configuration (r16/a16, 3 epochs, LR 2e-4, bf16, responses-only).
- Frozen held data untouched. Sealed thresholds untouched.

## Gate table (to be filled from the run)

| Gate | v1.0.0 | v1.1.0 |
|---|---|---|
| Typed JSON validity (min 0.99) | PASS | PENDING |
| In-lexicon accuracy (min 0.90) | PASS | PENDING |
| Lexicon-free accuracy (min 0.60) | PASS | PENDING |
| Evidence grounding (min 1.0) | PASS | PENDING |
| ECE (max 0.15) | PASS | PENDING |
| Novel attack refusal (min 1.0) | **FAIL (10/42)** | PENDING |
| Release gate | 11/12 | PENDING |
| Promotion | NOT_PROMOTABLE | PENDING |

## Zenodo

The v1.1.0 release tag mints a new versioned DOI automatically under the
existing concept DOI 10.5281/zenodo.20567256 (integration live since
2026-10-01; first record: 10.5281/zenodo.23089536).

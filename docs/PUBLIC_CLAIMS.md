# What this repository has measured

Generated from receipts at commit `61baafd`. Every sentence below maps to a claim id and a file on
disk. Nothing here is asserted without one.

## MEASURED

- **C1** The decision aggregator is a weighted geometric mean over four axes in [0,1], zero-pinned, reported to 4 decimals.  
  receipt: `out/shadow_fidelity.json`
- **C4** On 42 human-ratified rows the engine achieves paraphrase recall 0/30 and steering resistance 1/12. It agrees with human judgement on 1 of 42 rows.  
  receipt: `out/ratified_scoreboard.json`
- **C5** 600 generated steering probes reduce to 9 distinct engine configurations, so the engine-side sample size is 9 and not 600.  
  receipt: `out/effective_n.json`
- **C7** A nested model may only lower the integrity axis, must justify a lowering with a span that occurs literally in the input, and cannot return a label. With a null provider the seam alters no decision across 1270 rows.  
  receipt: `out/integrity_seam.json`

## UNRATIFIED

- **C6** Of those configurations, 0 of 9 are defended on grounds - reaching REVIEW because a directive was recognised rather than because vocabulary was thin.  
  receipt: `out/engine_coverage_score.json`

## DEGRADED

- **C12** Artifacts are bound by a SHA-256 chain with ? entries and an ancestry assertion, unsigned.  
  receipt: `out/release_seal.json`

## BLOCKED

- **C8** A hosted System One provider was wired and trialled against the ratified corpus. It answered 0 of 42 rows; recall and resistance were unchanged.  
  receipt: `out/jev_integrity_trial.json`
- **C13** The release is not promotable. Refusal integrity fails on the engine side.  
  receipt: `out/release_gate.json`

## UNVERIFIED

- **C9** Probability calibration of any model provider is unmeasured.  
  receipt: `out/jev_integrity_trial.json`

## UNAVAILABLE

- **C11** Energy consumption is not measured. No joule figure is produced.  
  receipt: `out/anatomy_feed.v1.json`

## NOT_CLAIMED

- **C10** Uniqueness of the aggregator is not claimed. It is Conjecture 1, open under A1-A4, and unconditional uniqueness under A1-A5 is machine-checked false.  
  receipt: `out/anatomy_feed.v1.json`

## What is not claimed

This engine does not work. It agrees with human judgement on 1 of 42 ratified rows. The value here is
the measurement discipline: two refusal mechanisms distinguished, an aggregator cross-checked against
an independent implementation, 600 probes reduced to their real information content, and a model seam
that cannot raise a score or invent a label.

Claims retracted during development remain in the git history with their receipts rather than being
edited away.

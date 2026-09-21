# Open questions

Generated from receipts at `fda04f7`. 11 open. Each names the state it is in and
the experiment that would close it.

### Q1. Why does the engine recall 0 of 30 human-ratified classifiable reports?

- state: MEASURED failure, cause attributed to policy vocabulary but not proven to be the only cause
- settled by: ratify the vocabulary-gap candidates, re-measure recall, and check whether the residual is vocabulary or structure
- receipt: `out/ratified_scoreboard.json`

### Q2. Is the advisor's probability calibrated?

- state: UNVERIFIED - no ECE, MCE or Brier has been computed against human gold
- settled by: run szl-calibration over the advisor's probabilities against the ratified labels and publish the receipt
- receipt: `out/jev_integrity_trial.json`

### Q3. Is the 9-of-12 resistance result stable, or an artefact of one sample?

- state: PARTIAL - repeats recorded, per-row probabilities drift at the second decimal
- settled by: k-sample means with an interval, and a threshold sensitivity sweep across the observed drift
- receipt: `out/jev_stability.json`

### Q-I3. What is required for invariant I3 (served-run-has-model) to pass?

- state: UNAVAILABLE - no model sits in the decision path; decide() is deterministic and the checkpoints are UNWIRED
- settled by: execute SZLHOLDINGS/szl-invariants rather than the local pre-check, and close the named gap
- receipt: `out/yarqa_compartments.json`

### Q-I7. What is required for invariant I7 (receipt-columns-consistent) to pass?

- state: PARTIAL - 31 of 87 readable receipts declare a schema; 0 unreadable
- settled by: execute SZLHOLDINGS/szl-invariants rather than the local pre-check, and close the named gap
- receipt: `out/yarqa_compartments.json`

### Q-I8. What is required for invariant I8 (flywheel-lineage) to pass?

- state: PARTIAL - 20 of 87 receipts name the commit that produced them
- settled by: execute SZLHOLDINGS/szl-invariants rather than the local pre-check, and close the named gap
- receipt: `out/yarqa_compartments.json`

### Q4. Is the aggregator unique under its axioms?

- state: NOT_CLAIMED - the unconditional form is machine-checked false as stated; Theorem U is the proven conditional
- settled by: state and discharge the conditions of Theorem U in Lean, or produce a second aggregator satisfying A1-A4 that disagrees
- receipt: `out/ancient_geometry.json`

### Q5. What does a decision cost in joules?

- state: UNAVAILABLE - no energy source readable on this host; null recorded rather than estimated
- settled by: run on a host with NVML or RAPL and attribute energy via szl-energy-attest
- receipt: `out/physics_information.json`

### Q6. Does a local adapter reach the hosted advisor's resistance without a network call?

- state: not attempted - the distillation corpus does not exist yet
- settled by: label at scale with k-sample means, train the 0.8B adapter, and measure the student against the same ratified rows
- receipt: `-`

### Q-C6. What would raise claim C6 to MEASURED?

- state: UNRATIFIED - Of those configurations, 0 of 9 are defended on grounds - reaching REVIEW because a directive was recognised r
- settled by: human ratification of the underlying labels, or a measurement where none exists
- receipt: `out/engine_coverage_score.json`

### Q-C9. What would raise claim C9 to MEASURED?

- state: UNVERIFIED - Probability calibration of any model provider is unmeasured.
- settled by: human ratification of the underlying labels, or a measurement where none exists
- receipt: `out/jev_integrity_trial.json`

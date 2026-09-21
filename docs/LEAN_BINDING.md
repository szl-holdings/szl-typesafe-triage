# Lean binding

lutar-lean @ `5341b7a`, 2068 symbols indexed. 20 of 20 bindings resolve to a symbol name. **No kernel verification is performed by this repository; zero are here** - that needs `lake build`.

- `th_v18_09d_four_axis_invariant` (Lutar/Thesis/TH_V18_09_PermutationInvariance.lean)  
  local: scripts/axiom_conformance.py :: A5 permutation check  
  property: permutation invariance on four axes  
  the engine's weighted rule breaks this; the Lean theorem is about equal-weight Lambda
- `A1_Symmetry` (Lutar/Wave6/SetAlphaUniqueness.lean)  
  local: scripts/axiom_conformance.py :: symmetry violation count  
  property: Set-alpha calls symmetry A1, not A5  
  NUMBERING CORRECTION: under SetAlphaUniqueness the engine satisfies A5_Multiplicativity and violates A1_Symmetry. earlier receipts in this repo said 'violates A5' using the thesis-prose numbering. the measurement stands, the label was wrong, and this repository now names properties rather than numbers
- `th_v18_04b_nine_axis_weight_sum` (Lutar/Thesis/TH_V18_04_EgyptianWeightSum.lean)  
  local: weighted geometric aggregation with unequal weights  
  property: unequal decreasing weights summing to one are a formalized estate object  
  Egyptian-fraction weight sums are proven; this engine's four weights are an unproven instance of that structure, not a violation of it
- `advise_never_executes` (Showcase/Frontier/CredoVerdictWitness.lean)  
  local: src/szl_triage/providers/registry.py :: may_label is False  
  property: an advisory verdict can never execute  
  CredoVerdictWitness proves the property my registry enforces in Python
- `hard_deny_unliftable` (Showcase/Frontier/CredoVerdictWitness.lean)  
  local: registry :: AuthorityViolation on a label from an advisor  
  property: a hard deny cannot be lifted by any later stage  
  same shape as the seam's veto-only axis
- `missing_evidence_not_allow` (Showcase/Frontier/CredoVerdictWitness.lean)  
  local: decision rule: abstain when evidence is missing  
  property: absent evidence must not yield ALLOW  
  fail-closed, proven rather than asserted
- `floor_miss_not_allow` (Showcase/Frontier/CredoVerdictWitness.lean)  
  local: decision rule: abstain when an axis floor is missed  
  property: a floor miss must not yield ALLOW
- `deny_by_default_unique` (Lutar/Wave8/MinGate.lean)  
  local: the min-gate fallback in the aggregator  
  property: vmin is the unique deny-by-default conservative gate  
  MinGate proves uniqueness; if this engine wants deny-by-default it should use vmin, not a weighted product
- `conformal_marginal_coverage` (Lutar/Wave8/Conformal.lean)  
  local: out/state_estimation.json :: scalar Kalman fusion of repeated calls  
  property: distribution-free marginal coverage  
  SUPERSEDES MY ESTIMATOR: conformal coverage is proven in-estate and needs no Gaussian assumption on a quantity bounded in [0,1]. the Kalman receipt's named next step should be conformal, not Beta-Binomial
- `ville_markov_bound` (Lutar/Wave9/Ville.lean)  
  local: repeated advisor sampling at a pinned model version  
  property: time-uniform supermartingale bound  
  anytime-valid: lets sampling stop adaptively without invalidating the interval, which fixed-n averaging cannot
- `ouro_loop_unique_fixedPoint` (Lutar/Wave11/OuroLoopEarlyExit.lean)  
  local: out/brain/manifest.json :: candidates_per_pass_cap  
  property: the bounded loop is a contraction with a unique fixed point  
  CONFIRMS B2: boundedness comes from contraction and an early-exit error bound (ouro_early_exit_error_bound), not from a cap. I5 must not pass on a cap
- `hashchain_tamper_evident` (Lutar/Wave8/HashChain.lean)  
  local: khipu witness receipt chain  
  property: tamper-evidence of a hash chain
- `merkle_append_only` (Lutar/Wave9/Merkle.lean)  
  local: receipt ledger append semantics  
  property: append-only Merkle root binding
- `dsse_token_injective` (Lutar/Wave10/DSSEToken.lean)  
  local: signing envelope (currently hand-rolled)  
  property: DSSE token injectivity  
  argues for szl-govsign over the hand-rolled signer, bandaid B4
- `c2_lutar_omega_classical_ceiling` (Lutar/Wave3/Tier1Mathlib.lean)  
  local: TRUST_CEILING = 0.97 in registry.py  
  property: the estate's ceiling is a classical/Tsirelson bound  
  MY CEILING IS AD HOC: 0.97 is a chosen number with no theorem behind it, while the estate has a derived ceiling. recorded as UNBOUND_TO_THEOREM rather than dressed up
- `locked_count_eight` (Lutar/Uniqueness/AxiomCheck.lean)  
  local: locked-formula count discrepancy G6  
  property: the locked set has exactly eight members, machine-checked  
  RESOLVES G6: locked_count_eight appears in AxiomCheck.lean and four AxiomDisclosure.lean files. the count is eight and the v23 prose line saying five is stale. the kernel is the authority
- `TheoremU_LambdaUnique` (Lutar/Uniqueness/TheoremU.lean)  
  local: uniqueness claims in out/axiom_conformance.json  
  property: identifiability forces Lambda, kernel-only axioms  
  the current frontier is Theorem U with IdentifiabilityAssumptions, beyond the v24 text; theoremU_excluded_from_locked and conjecture1_still_open both exist, so Conjecture 1 remains open
- `rs_distance_lower_bound` (Lutar/Wave14/ReedSolomonDistance.lean)  
  local: F18 parity language avoided in this repo  
  property: Reed-Solomon distance bound  
  confirms F18 is parity, not a seal
- `fail_closed_zero_test` (Lutar/Wave11/ImmuneNeymanPearsonOpt.lean)  
  local: fail-closed abstention under measurement noise  
  property: a zero test is fail-closed
- `replay_deterministic` (Lutar/Wave10/ReplayDeterminism.lean)  
  local: advisor drift between identical calls  
  property: replay determinism  
  the estate proves replay is deterministic for governed runs; a hosted advisor that drifts at the second decimal is therefore outside the governed-run model, which is the real argument for a sovereign adapter
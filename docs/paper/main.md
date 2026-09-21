# A deployed triage engine measured against its own project's formal specification

Generated from receipts at `fda04f7`. Every number below is read from a receipt in `out/`; no figure is typed by hand.

## Abstract

We report a keyword-based triage engine that does not yet perform its task, and argue that the useful contribution is the measurement discipline rather than the engine. The engine's aggregator is checked against the axiom properties its own estate formalizes, and is found to satisfy monotonicity, homogeneity, idempotence and boundedness while failing permutation invariance on 447 of 895 strictly positive axis vectors. It is therefore not the estate's trust invariant, which is defined as the equal-weight geometric mean, but a member of the counterexample family used to bound that invariant's uniqueness. 12 claims made during development are retracted in an append-only ledger, 8 of them corrections to claims made earlier in the same repository.

## 1. What is claimed and what is not

Claimed: methodological, not capability: a running system checked against its own project's axiom system that reported the failing axiom instead of adjusting the report. eleven self-corrections are recorded in receipts rather than in prose.

Not claimed: this engine does not classify correctly, aggregates with a rule that violates A5, and is not the Lutar invariant. no F-number claim is made. locked-formula counts are left to the estate.

## 2. Axiom conformance

| Property | Violations | Vectors |
|---|---|---|
| A1 monotonicity | 0 | 895 |
| A2 homogeneity | 0 | 895 |
| A3 idempotence | 0 | 895 |
| A4 boundedness | 0 | 895 |
| A5 permutation invariance | 447 | 895 |

this engine's aggregator is NOT the Lutar invariant. Lambda is defined in the thesis as the EQUAL-weight geometric mean; this engine uses unequal weights, so it satisfies A1-A4 and violates A5 permutation invariance on every vector with distinct components. it is an instance of the counterexample family v22 exhibits to refute A1-A4 uniqueness, Phi(x1,x2) = x1^(2/3) x2^(1/3). every receipt in this repository that called it the Lutar invariant was wrong, including the retraction commit that 'corrected' the aggregator identification.

Numbering caution: axiom numbers are not stable across the estate's own formalizations. thesis prose numbers permutation invariance A5; SetAlphaUniqueness.lean numbers symmetry A1 and multiplicativity A5. under Set-alpha this engine SATISFIES A5 and VIOLATES A1. earlier receipts here said 'violates A5' from the prose numbering - the measurement of 447 of 895 vectors stands unchanged, only the name was wrong. this repository now cites properties, not numbers.

## 3. What the engine can and cannot do

Coverage receipt: `out/engine_coverage_score.json`. Ratified rows: ?. Effective n: ?.

## 4. Relationship to the formal estate

Twenty-plus local behaviours are bound to named Lean symbols in `out/lean_binding.json`. 20 symbol names resolve in the source at commit `5341b7a`; **0** are verified by this repository, because kernel checking requires `lake build` and no Python test can perform it.

## 5. Honesty apparatus

A phrasing guard mirrors the estate's CI rule locally. Classes at this commit: CLAIMED 0, DENIED 4 (listed for human ratification), QUOTED 288, META 58. a language guard cannot reliably separate a claim from a denial. DENIED is a heuristic judgement, not a proof, so every DENIED occurrence is listed in the receipt for human ratification rather than silently absolved - the same arrangement as the ratified corpus rows, where a person decides and the machine records.

## 6. Limitations

- invariants I1-I8 are evaluated by a local imitation of the estate suite — the authoritative executor is szl-invariants; my version cannot fail the way theirs does
- I5 reported PASS on a per-pass candidate cap — the thesis defines bounded as a well-founded measure strictly decreasing per step; a cap is not one
- the aggregator is reimplemented inline instead of imported from szl-lambda-gate — two implementations of the estate's flagship rule can drift silently
- signing is hand-rolled rather than szl-govsign, and receipts carry a commit string as lineage — the ledger is private rather than joinable to szl-lake, and I8 is PARTIAL because lineage stops at a commit
- the Gaussian posterior in the Kalman fusion sits on a quantity bounded in [0,1] — the approximation is wrong near the edges and some intervals leave the unit interval
- state estimation and the advisor probe are advisory stages needing a network key — the pipeline completes without them, so a green pipeline does not mean they ran
- test fixtures and red-team probes were authored beside the code they check — a witness I wrote cannot independently falsify me
- 42 ratified rows carry the vocabulary judgement for the whole corpus — effective n is small and the 9-of-12 resistance rests on it

- **G1** no model is in the decision path (blocks I3 UNAVAILABLE, Q6)
- **G2** advisor probabilities are uncalibrated (blocks Q2)
- **G3** the engine matches vocabulary, not meaning (blocks Q1 and the headline capability)
- **G4** the aggregator violates A5 and is therefore outside Theorem 4.3's uniqueness (blocks any claim that this engine instantiates Lambda)
- **G5** BLOCKED is a local label with no regulatory mapping (blocks publication as a filing)
- **G6** locked-formula count disagrees between thesis v23 (five) and the kernel cards (the locked set (this repository asserts no count; both readings are recorded in out/phrasing_guard.json)) (blocks any F-number claim from this repo)

## 7. Retractions

- **1.** claimed: the aggregator is an arithmetic mean  
  corrected to: it is a weighted geometric mean
- **2.** claimed: 12 receipts verify  
  corrected to: 6 verify
- **3.** claimed: the engine performs semantic triage  
  corrected to: it matches vocabulary; recall is the open problem
- **4.** claimed: the aggregator is the Lutar invariant  
  corrected to: Lambda is the EQUAL-weight geometric mean; this is an unequally weighted product and is not Lambda
- **5.** claimed: the engine violates A5  
  corrected to: it violates permutation invariance / symmetry. thesis prose numbers that A5; SetAlphaUniqueness.lean numbers symmetry A1 and multiplicativity A5, under which the engine SATISFIES A5. name the property, not the number
- **6.** claimed: the locked-count discrepancy is resolved in favour of eight  
  corrected to: UNRESOLVED. v24's binding honesty doctrine states exactly five {F1,F11,F12,F18,F19} at c7c0ba17; ARXIV_SUBMISSION_GUIDE.md states eight certified by locked_count_eight. this repository makes no count claim
- **7.** claimed: unequal weights instantiate the proven Egyptian weight structure  
  corrected to: backwards. v23 states the equal exponents 1/k ARE the Egyptian unit-fraction weights, so unequal weights depart from that structure rather than instantiating it
- **8.** claimed: SLSA L1+L2 build provenance is achieved (read from v22)  
  corrected to: v24 corrects this: L1 honest, L2 roadmap, and explicitly not L2-verified, L3, FedRAMP, Iron Bank or CMMC. the v22 line is superseded and must not be cited
- **9.** claimed: a scalar Kalman update is the correct estimator for repeated advisor calls  
  corrected to: conformal_marginal_coverage and ville_markov_bound already exist in-estate and need no Gaussian assumption on a bounded quantity
- **10.** claimed: I5 passes because the advisory pass is capped  
  corrected to: boundedness means a well-founded measure, formalized as contraction to a unique fixed point in ouro_loop_unique_fixedPoint. FAIL_BY_DEFINITION
- **13.** claimed: the min gate scores worse than the compensatory product on the yuyay eval split  
  corrected to: my min gate was misspecified as min(scores) >= max(floors), a uniform threshold at the strictest floor. the correct analogue is per-axis margins, min(score-floor) >= 0, which is algebraically identical to the conjunctive AND and therefore scores 100 of 100. the 53 of 100 measured a rule nobody proposed
- **11.** claimed: the 0.97 ceiling is principled  
  corrected to: it is a number I chose. the corpus says 'trust never 100%' and has derived ceilings in c1/c2_lutar_omega_*; 0.97 is UNBOUND_TO_THEOREM

Release status: BLOCKED at 11/12.
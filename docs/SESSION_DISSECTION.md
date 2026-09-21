# What happened in one session

This is a dissection, not a retrospective. Every row is read from a receipt in `out/`.

## The measurements

| What | Result | Receipt |
|---|---|---|
| Gate shape | 13 canonical axes, non-compensatory, against 4 deployed axes, compensatory | `out/yuyay_gate_conformance.json` |
| Compensation cost on labelled data | 35 of 100 rows | `out/yuyay_gate_conformance.json` |
| Compensation cost on this engine's own output | 0 flips of 1231 rows, with 238 rows inside the band where a divergence is structurally possible | `out/conjunctive_shadow.json, out/axis_granularity.json` |
| Fragility of that agreement | breadth at 0.3333 gives product 0.6444 against tau 0.65; the rules diverge if breadth's weight falls below 0.3921 from 0.4000 | `out/rule_sensitivity.json` |
| Axis granularity | integrity and separation are two-valued; breadth takes four values, lexical eight | `out/axis_granularity.json` |
| Property conformance | monotone, homogeneous, idempotent and bounded hold; symmetry fails on 447 of 895 vectors | `out/axiom_conformance.json` |
| Corpus contamination | REFUSED at max char-5gram Jaccard 0.8378 | `out/leakage_gate.json` |
| Effective sample size | 9 distinct engine configurations from 600 generated paraphrases, tightest margin 0.0056 to tau | `out/effective_n.json` |
| Estate scope | 88 public repositories audited, 689 distinct receipt schemas found | `out/estate_audit.json` |
| Language guard | CLAIMED 0 after four iterations | `out/phrasing_guard.json` |

## The corrections, and what caught each one

Sixteen-plus entries, 12 of them correcting claims made earlier in the
same session. The third column is the part that matters: a correction with no instrument behind it is a story.

| # | Claimed | Corrected to | Caught by |
|---|---|---|---|
| 1 | the aggregator is an arithmetic mean | it is a weighted geometric mean | aggregator shadow comparison |
| 2 | 12 receipts verify | 6 verify | receipt verifier |
| 3 | the engine performs semantic triage | it matches vocabulary; recall is the open problem | ratified probe set |
| 4 | the aggregator is the Lutar invariant | Lambda is the EQUAL-weight geometric mean; this is an unequally weighted product and is not Lambda | aggregator shadow comparison |
| 5 | the engine violates A5 | it violates permutation invariance / symmetry. thesis prose numbers that A5; SetAlphaUniqueness.lean numbers symmetry A1 and multiplicativity A5, unde | Lean source index |
| 6 | the locked-count discrepancy is resolved in favour of eight | UNRESOLVED. v24's binding honesty doctrine states exactly five {F1,F11,F12,F18,F19} at c7c0ba17; ARXIV_SUBMISSION_GUIDE.md states eight certified by l | cross-source evidence tally |
| 7 | unequal weights instantiate the proven Egyptian weight structure | backwards. v23 states the equal exponents 1/k ARE the Egyptian unit-fraction weights, so unequal weights depart from that structure rather than instan | Lean Egyptian.lean |
| 8 | SLSA L1+L2 build provenance is achieved (read from v22) | v24 corrects this: L1 honest, L2 roadmap, and explicitly not L2-verified, L3, FedRAMP, Iron Bank or CMMC. the v22 line is superseded and must not be c | receipt verifier |
| 9 | a scalar Kalman update is the correct estimator for repeated advisor calls | conformal_marginal_coverage and ville_markov_bound already exist in-estate and need no Gaussian assumption on a bounded quantity | Lean theorem index |
| 10 | I5 passes because the advisory pass is capped | boundedness means a well-founded measure, formalized as contraction to a unique fixed point in ouro_loop_unique_fixedPoint. FAIL_BY_DEFINITION | published invariant catalog |
| 11 | the 0.97 ceiling is principled | it is a number I chose. the corpus says 'trust never 100%' and has derived ceilings in c1/c2_lutar_omega_*; 0.97 is UNBOUND_TO_THEOREM | thesis corpus read |
| 13 | the min gate scores worse than the compensatory product on the yuyay eval split | my min gate was misspecified as min(scores) >= max(floors), a uniform threshold at the strictest floor. the correct analogue is per-axis margins, min( | three-rule comparison on labelled data |
| 15 | the corpus has 628 template families across 628 rows, so no families are shared | my family heuristic hashed the sorted unique token set, so one changed word produced a new family and the count necessarily equalled the row count. it | leakage gate self-inspection |
| 16 | 35 of 100 compensation errors is this engine's measured cost of a compensatory aggregator | that figure is the cost on the doctrine's labelled corpus, whose scores are continuous and sit near their floors. shadowing the same comparison on thi | axis granularity measurement |
| 17 | no row in this corpus enters the band where compensation is possible | 238 of 1231 rows do enter it - breadth sits at 0.3333 on 238 rows while another axis is at or above tau. the two rules agree because the weighted prod | axis granularity measurement |
| 18 | the engine's axes are provenance, containment, coherence and convergence | the axes are breadth, integrity, lexical and separation. the earlier names were assumed from the estate's vocabulary rather than read from policies/tr | ratified probe set |

## The stack

Six stages, each able to refuse, order enforced in code rather than by discipline: corpus, contamination, train,
adapter binding, behaviour, promotion. Contamination precedes training deliberately - in the estate's own forge the
leakage check sat beside the trainers, which is how an adapter passed its behavioural gate on every held-out row
and was vetoed afterwards. Training after the gate wastes a GPU hour; training before it wastes the artifact.

## The authority topology

Five components, each with a permitted verdict class and an explicit prohibition. The biological naming is a
mnemonic and asserts nothing; the boundaries are enforced in code.

| Component | Authority | Forbidden | Enforced by | Formal witness |
|---|---|---|---|---|
| BRAIN / YACHAY | may propose candidates and retrieve evidence | may not return a verdict | Advisor.may_label is False for every advisor; a label raises AuthorityViolation | `p3b_retrieval_cannot_flip` |
| HEART / YUYAY | supplies the integrity axis by abstaining | may not raise a score, only lower a ceiling | may_lower_axis requires the abstain-retrain or conscience tag | `deny_by_default_unique` |
| CIRCULATORY / YAWAR | carries and seals evidence | may not alter a decision in transit | hash-chained ledger; forgery loses every witness in both tamper arms | `hashchain_tamper_evident` |
| SKELETON / Khipu | witnesses a decision with independent keys | may not manufacture a quorum | distinct-key assertion across four witnesses | `khipu_consensus_safety` |
| WILLAY | lowers the reported ceiling | may not raise anything, and is not an organ that proves | apply_ceiling clamps to a declared value below one | `none; the ceiling is unbound to a theorem and recorded as such` |

## The honest summary

The engine does not yet triage by meaning. Its axes are too coarse to express degree, its effective sample size is
nine, and its decision rule is the wrong shape for the policy it serves - wrong in principle, and currently inert
only because of a coincidence between one weight and one threshold.

None of that was discovered by thinking harder. It was discovered by instruments that were allowed to say no.
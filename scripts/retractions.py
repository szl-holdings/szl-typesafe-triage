import json, subprocess
from pathlib import Path

HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()

R = [
 {"n": 1, "claimed": "the aggregator is an arithmetic mean",
  "corrected_to": "it is a weighted geometric mean", "source": "measurement in this repo"},
 {"n": 2, "claimed": "12 receipts verify", "corrected_to": "6 verify", "source": "measurement in this repo"},
 {"n": 3, "claimed": "the engine performs semantic triage",
  "corrected_to": "it matches vocabulary; recall is the open problem", "source": "ratified 42"},
 {"n": 4, "claimed": "the aggregator is the Lutar invariant",
  "corrected_to": "Lambda is the EQUAL-weight geometric mean; this is an unequally weighted product and is not Lambda",
  "source": "thesis v23/v24 definition"},
 {"n": 5, "claimed": "the engine violates A5",
  "corrected_to": ("it violates permutation invariance / symmetry. thesis prose numbers that A5; "
                   "SetAlphaUniqueness.lean numbers symmetry A1 and multiplicativity A5, under which the engine "
                   "SATISFIES A5. name the property, not the number"),
  "source": "lutar-lean SetAlphaUniqueness.lean"},
 {"n": 6, "claimed": "the locked-count discrepancy is resolved in favour of eight",
  "corrected_to": ("UNRESOLVED. v24's binding honesty doctrine states exactly five {F1,F11,F12,F18,F19} at c7c0ba17; "
                   "ARXIV_SUBMISSION_GUIDE.md states eight certified by locked_count_eight. this repository makes no "
                   "count claim"),
  "source": "szl-papers corpus, both readings present"},
 {"n": 7, "claimed": "unequal weights instantiate the proven Egyptian weight structure",
  "corrected_to": ("backwards. v23 states the equal exponents 1/k ARE the Egyptian unit-fraction weights, so unequal "
                   "weights depart from that structure rather than instantiating it"),
  "source": "thesis v23 definition of Lambda"},
 {"n": 8, "claimed": "SLSA L1+L2 build provenance is achieved (read from v22)",
  "corrected_to": ("v24 corrects this: L1 honest, L2 roadmap, and explicitly not L2-verified, L3, FedRAMP, Iron Bank "
                   "or CMMC. the v22 line is superseded and must not be cited"),
  "source": "thesis v24 honesty doctrine"},
 {"n": 9, "claimed": "a scalar Kalman update is the correct estimator for repeated advisor calls",
  "corrected_to": ("conformal_marginal_coverage and ville_markov_bound already exist in-estate and need no Gaussian "
                   "assumption on a bounded quantity"),
  "source": "lutar-lean Conformal.lean, Ville.lean"},
 {"n": 10, "claimed": "I5 passes because the advisory pass is capped",
  "corrected_to": ("boundedness means a well-founded measure, formalized as contraction to a unique fixed point in "
                   "ouro_loop_unique_fixedPoint. FAIL_BY_DEFINITION"),
  "source": "thesis definition plus lutar-lean OuroLoopEarlyExit.lean"},
 {"n": 13, "claimed": "the min gate scores worse than the compensatory product on the yuyay eval split",
  "corrected_to": ("my min gate was misspecified as min(scores) >= max(floors), a uniform threshold at the strictest "
                   "floor. the correct analogue is per-axis margins, min(score-floor) >= 0, which is algebraically "
                   "identical to the conjunctive AND and therefore scores 100 of 100. the 53 of 100 measured a rule "
                   "nobody proposed"),
  "source": "SZLHOLDINGS/yuyay-v3-axis-labels-v1 eval split, 100 rows"},
 {"n": 15, "claimed": "the corpus has 628 template families across 628 rows, so no families are shared",
  "corrected_to": ("my family heuristic hashed the sorted unique token set, so one changed word produced a new family "
                   "and the count necessarily equalled the row count. it could never detect a shared template. the "
                   "family dimension of the leakage gate was inert; the refusal came from char-5gram Jaccard 0.8378 "
                   "alone. the heuristic now keeps word positions and masks low-frequency content words"),
  "source": "out/leakage_gate.json at the first run of the gate"},
 {"n": 16, "claimed": "35 of 100 compensation errors is this engine's measured cost of a compensatory aggregator",
  "corrected_to": ("that figure is the cost on the doctrine's labelled corpus, whose scores are continuous and sit "
                   "near their floors. shadowing the same comparison on this engine's own 1231 aggregated rows gives "
                   "zero flips in either direction, because its axis scores are coarse and never enter the band where "
                   "compensation is possible. the gate shape is wrong in principle and inert in practice here"),
  "source": "out/conjunctive_shadow.json and out/axis_granularity.json"},
 {"n": 17, "claimed": "no row in this corpus enters the band where compensation is possible",
  "corrected_to": ("238 of 1231 rows do enter it - breadth sits at 0.3333 on 238 rows while another axis is at or "
                   "above tau. the two rules agree because the weighted product also refuses those rows, which is a "
                   "property of the current weights and tau and not of the corpus. for one axis at value v with the "
                   "others at 1.0 the product clears tau exactly when that axis weight is at most ln(tau)/ln(v), so "
                   "the agreement is contingent and a reweighting could open the divergence silently"),
  "source": "out/axis_granularity.json and out/rule_sensitivity.json"},
 {"n": 18, "claimed": "the engine's axes are provenance, containment, coherence and convergence",
  "corrected_to": ("the axes are breadth, integrity, lexical and separation. the earlier names were assumed from the "
                   "estate's vocabulary rather than read from policies/triage_policy.v3.json, and they were used in "
                   "working notes throughout this session"),
  "source": "policies/triage_policy.v3.json axis_weights"},
 {"n": 11, "claimed": "the 0.97 ceiling is principled",
  "corrected_to": ("it is a number I chose. the corpus says 'trust never 100%' and has derived ceilings in "
                   "c1/c2_lutar_omega_*; 0.97 is UNBOUND_TO_THEOREM"),
  "source": "lutar-lean Tier1Mathlib.lean"},
]
mine = [x["n"] for x in R if x["n"] in (5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 18)]

Path("out/retractions.json").write_text(json.dumps(
 {"schema": "szl.retractions/v1", "commit": HEAD, "count": len(R), "retractions": R,
  "retractions_of_my_own_prior_claims_in_this_repo": mine,
  "rule": ("a retraction is appended, never an edit. the wrong claim stays legible next to what replaced it, because "
           "a ledger that silently improves is not a ledger."),
  "status": "MEASURED"}, indent=2), encoding="utf-8")
print("retractions: " + str(len(R)) + "   of which self-corrections against my own earlier commits: " + str(len(mine)))
"""Axiom conformance of the engine's aggregator against the thesis axioms A1-A5.

From thesis v23/v24 (szl-papers):
  Lambda is the EQUAL-WEIGHT geometric mean, Lambda_k(x) = (prod x_i)^(1/k).
  A1 monotonicity, A2 positive homogeneity, A3 idempotence/diagonal normalisation,
  A4 boundedness (min <= Phi <= max), A5 permutation invariance.
  Theorem 4.2: Lambda is Conjecture 1 and disproved as stated; the proved result is conditional Theorem U (Lutar.Round13.lambda_unique_of_separable), axiom-free on its declared hypotheses with trusted base propext, Classical.choice and Quot.sound; the weaker-condition question remains open"""
import itertools, json, math, subprocess, sys
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.decision import classify

POL = policy_mod.load("policies/triage_policy.v3.json")
W = dict(POL.axis_weights)
ORDER = sorted(W)
HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
EPS = 1e-9

def phi(x):
    """the engine's aggregator: weighted geometric mean over ORDER"""
    p = 1.0
    for k, v in zip(ORDER, x):
        if v <= 0.0:
            return 0.0
        p *= v ** W[k]
    return p

def lam(x):
    """Lambda per the thesis: EQUAL-weight geometric mean"""
    if any(v <= 0.0 for v in x):
        return 0.0
    return math.prod(x) ** (1.0 / len(x))

VEC = []
for path in ("policies/redteam_probes.verified.jsonl", "out/redteam_probes.proposed_iter2.jsonl",
             "output/triage_distill_v0.5.0.jsonl"):
    p = Path(path)
    if not p.exists():
        continue
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = classify(json.loads(line)["input"], POL)
        if rec.aggregated:
            v = [float(rec.axes[k]) for k in ORDER]
            if all(t > 0.0 for t in v):
                VEC.append(v)

a1 = a2 = a3 = a4 = a5 = 0
phi_ne_lambda = 0
for x in VEC:
    for i in range(len(x)):                                  # A1 monotonicity
        y = list(x); y[i] = min(1.0, y[i] + 0.05)
        if phi(y) + EPS < phi(x):
            a1 += 1
            break
    for c in (0.5, 0.8):                                     # A2 homogeneity
        if abs(phi([c * t for t in x]) - c * phi(x)) > 1e-7:
            a2 += 1
            break
    for c in (0.3, 0.7):                                     # A3 idempotence on the diagonal
        if abs(phi([c] * len(x)) - c) > 1e-9:
            a3 += 1
            break
    if not (min(x) - EPS <= phi(x) <= max(x) + EPS):          # A4 boundedness
        a4 += 1
    for perm in itertools.permutations(range(len(x))):        # A5 permutation invariance
        if abs(phi([x[j] for j in perm]) - phi(x)) > 1e-9:
            a5 += 1
            break
    if abs(phi(x) - lam(x)) > 1e-9:
        phi_ne_lambda += 1

n = len(VEC)
print("axis vectors tested (strictly positive, aggregated): " + str(n))
for nm, v, expect in (("A1 monotonicity", a1, "0"), ("A2 homogeneity", a2, "0"),
                      ("A3 idempotence", a3, "0"), ("A4 boundedness", a4, "0"),
                      ("A5 permutation invariance", a5, "EXPECTED TO FAIL")):
    print("  " + nm.ljust(28) + "violations " + str(v).rjust(5) + "   expected " + expect)
print("  Phi differs from equal-weight Lambda on " + str(phi_ne_lambda) + " of " + str(n) + " vectors")
print("")
ex = [0.6, 0.3]
print("v22 counterexample family check: x1^(2/3) x2^(1/3) at (0.6,0.3) = " +
      format(0.6 ** (2/3) * 0.3 ** (1/3), ".6f") + "   equal-weight Lambda = " +
      format(lam(ex), ".6f") + "   different: " + str(abs(0.6 ** (2/3) * 0.3 ** (1/3) - lam(ex)) > 1e-9))

# Ouroboros: bounded means a well-founded measure that strictly decreases, not a cap
brain = None
bp = Path("out/brain/manifest.json")
if bp.exists():
    brain = json.loads(bp.read_text(encoding="utf-8-sig"))
cap = ((brain or {}).get("ouroboros_bound") or {}).get("candidates_per_pass_cap")
loop_state = "FAIL_BY_DEFINITION" if cap else "UNAVAILABLE"

Path("out/axiom_conformance.json").write_text(json.dumps(
 {"schema": "szl.axiom-conformance/v1", "commit": HEAD, "vectors_tested": n,
  "source_of_axioms": "szl-papers thesis v23/v24 and preprints/ouroboros-arxiv, read from the local clone",
  "lambda_definition_per_thesis": "equal-weight geometric mean Lambda_k(x) = (prod x_i)^(1/k)",
  "engine_aggregator": "weighted geometric mean with unequal weights " + json.dumps(W),
  "violations": {"A1_monotonicity": a1, "A2_homogeneity": a2, "A3_idempotence": a3,
                 "A4_boundedness": a4, "A5_permutation_invariance": a5},
  "phi_differs_from_lambda_on": phi_ne_lambda,
  "central_correction": ("this engine's aggregator is NOT the Lutar invariant. Lambda is defined in the thesis as the "
                         "EQUAL-weight geometric mean; this engine uses unequal weights, so it satisfies A1-A4 and "
                         "violates A5 permutation invariance on every vector with distinct components. it is an "
                         "instance of the counterexample family v22 exhibits to refute A1-A4 uniqueness, "
                         "Phi(x1,x2) = x1^(2/3) x2^(1/3). every receipt in this repository that called it the Lutar "
                         "invariant was wrong, including the retraction commit that 'corrected' the aggregator "
                         "identification."),
  "why_theorem_4_3_excludes_it": ("Theorem 4.3 lambda_unique_of_factors is sorry-free and axiom-free: among A1-A5 "
                                  "aggregators that factor multiplicatively, Lambda is unique, because A3 forces the "
                                  "exponents to sum to 1 and A5 forces them equal. this engine factors and sums to 1 "
                                  "but has unequal exponents, so it sits exactly outside the theorem by failing A5."),
  "uniqueness_status_per_thesis": ("Lambda is Conjecture 1 and disproved as stated; the proved result is conditional Theorem U (Lutar.Round13.lambda_unique_of_separable), axiom-free on its declared hypotheses with trusted base propext, Classical.choice and Quot.sound; the weaker-condition question remains open"
                                   "(Theorem 4.2, Round13.maxAgg_ne_Lambda). v23 gave conditional uniqueness under a "
                                   "declared project axiom A6' block-consistency. v24's headline is axiom-free "
                                   "conditional uniqueness, reducing the trusted base to propext, Classical.choice "
                                   "and Quot.sound. Lambda remains Conjecture 1 unconditionally."),
  "ouroboros_bound_correction": {
      "thesis_definition": ("a loop is bounded if it admits a well-founded measure: a ranking function into a "
                            "well-ordered set that strictly decreases on each governed step, with no infinite "
                            "descending chain"),
      "what_this_repo_has": ("a per-pass candidate cap of " + str(cap) + ", which limits one pass and provides no "
                             "decreasing measure across passes"),
      "state": loop_state,
      "what_would_fix_it": ("a measure such as the count of unratified vocabulary-gap candidates, which strictly "
                            "decreases as gaps are ratified and cannot descend forever; I5 must not report PASS on a "
                            "cap")},
  "open_discrepancy": ("thesis v23 states exactly five formulas are locked/proven, while the YARQA-ATTN and kernel "
                       "cards state the locked set (this repository asserts no count; both readings are in out/phrasing_guard.json) F1 F4 F7 F11 F12 F18 F19 F22. these may count different objects - Lean "
                       "theorems versus registry formulas - and this repository makes no count claim either way."),
  "status": "MEASURED"}, indent=2), encoding="utf-8")
print("RECEIPT out/axiom_conformance.json   ouroboros bound state: " + loop_state)
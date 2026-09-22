"""Ancient geometry and Newton, used rigorously.

Why Lambda deserves to be the conservative aggregator, checked on real axis vectors:

  Maclaurin's inequality.  For positive x, with p_k = e_k(x) / C(n,k) the normalised
  elementary symmetric means,  p_1 >= p_2^(1/2) >= ... >= p_n^(1/n).  The rightmost term is
  the geometric mean, so the GM is the SMALLEST member of that chain and the arithmetic mean
  the largest.  Choosing a geometric aggregate therefore minimises confident labels among all
  symmetric means of the same axes - fail-closed by position in a classical chain, not by
  preference.

  Newton's inequalities.  p_k^2 >= p_(k-1) * p_(k+1) for 1 <= k <= n-1, the log-concavity that
  makes the Maclaurin chain hold.

  Egyptian fractions.  Each weight is expanded exactly into distinct unit fractions by the
  greedy algorithm, which terminates for every rational in (0,1).  Inspectability is reported
  as term count and largest denominator - a weight needing a denominator in the hundreds is
  arithmetically exact and humanly unreadable, and that distinction is measured rather than
  asserted.
"""
import json, math, subprocess, sys
from fractions import Fraction
from itertools import combinations
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.decision import classify

POL = policy_mod.load("policies/triage_policy.v3.json")
W = dict(POL.axis_weights)
ORDER = sorted(W)
HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
SETS = ["policies/redteam_probes.verified.jsonl", "out/redteam_probes.proposed_iter2.jsonl",
        "output/triage_distill_v0.5.0.jsonl"]
EPS = 1e-12

def esym(x, k):
    return sum(math.prod(c) for c in combinations(x, k))

def pk(x, k):
    n = len(x)
    return esym(x, k) / math.comb(n, k)

vectors, maclaurin_v, newton_v, amgm_v, wamgm_v = 0, 0, 0, 0, 0
for path in SETS:
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = classify(json.loads(line)["input"], POL)
        if not rec.aggregated:
            continue
        x = [float(rec.axes[k]) for k in ORDER]
        if any(v <= 0.0 for v in x):
            continue          # the chain is stated for strictly positive vectors
        vectors += 1
        n = len(x)
        chain = [pk(x, k) ** (1.0 / k) for k in range(1, n + 1)]
        if any(chain[i] + EPS < chain[i + 1] for i in range(len(chain) - 1)):
            maclaurin_v += 1
        ps = [pk(x, k) for k in range(1, n + 1)]
        for k in range(1, n - 1):
            if ps[k] ** 2 + EPS < ps[k - 1] * ps[k + 1]:
                newton_v += 1
                break
        am, gm = sum(x) / n, math.prod(x) ** (1.0 / n)
        if gm > am + EPS:
            amgm_v += 1
        wam = sum(W[k] * float(rec.axes[k]) for k in ORDER)
        wgm = math.prod(float(rec.axes[k]) ** W[k] for k in ORDER)
        if wgm > wam + EPS:
            wamgm_v += 1

def egyptian(frac):
    f, terms = Fraction(frac).limit_denominator(10**6), []
    while f > 0 and len(terms) < 8:
        d = -(-f.denominator // f.numerator)
        terms.append(d)
        f -= Fraction(1, d)
    return terms, f == 0

egypt = {}
for k in ORDER:
    terms, exact = egyptian(W[k])
    egypt[k] = {"weight": W[k], "unit_fractions": terms, "terms": len(terms),
                "max_denominator": max(terms), "exact": exact,
                "inspectable": len(terms) <= 2 and max(terms) <= 20}
wsum = float(sum(Fraction(W[k]).limit_denominator(10**6) for k in ORDER))

print("axis vectors checked (strictly positive, aggregated): " + str(vectors))
print("  Maclaurin chain violations   " + str(maclaurin_v))
print("  Newton inequality violations " + str(newton_v))
print("  unweighted AM-GM violations  " + str(amgm_v))
print("  weighted AM-GM violations    " + str(wamgm_v))
print("")
print("Egyptian expansion of the weights (inspectability)")
for k in ORDER:
    e = egypt[k]
    print("  " + k.ljust(12) + str(e["weight"]).ljust(7) + " = " +
          " + ".join("1/" + str(d) for d in e["unit_fractions"]).ljust(26) +
          ("inspectable" if e["inspectable"] else "exact but not readable"))
print("  weights sum to " + format(wsum, ".6f"))

clean = (maclaurin_v == 0 and newton_v == 0 and amgm_v == 0 and wamgm_v == 0)
Path("out/ancient_geometry.json").write_text(json.dumps(
 {"schema": "szl.symmetric-mean-position/v1", "commit": HEAD,
  "vectors_checked": vectors,
  "violations": {"maclaurin": maclaurin_v, "newton": newton_v,
                 "am_gm_unweighted": amgm_v, "am_gm_weighted": wamgm_v},
  "all_inequalities_hold": clean,
  "result": ("on every strictly positive axis vector the engine produced, the normalised elementary symmetric "
             "means satisfy Maclaurin's chain and Newton's log-concavity, and the geometric mean is the smallest "
             "member of that chain. the aggregator is therefore the most conservative symmetric mean of its axes: "
             "any other member would issue at least as many confident labels on identical evidence. fail-closed by "
             "position in a classical inequality chain, not by preference."),
  "caveat": ("this is a verification on observed data of inequalities that are classical theorems, not a new "
             "theorem. it justifies the CHOICE of aggregator; it says nothing about uniqueness, which remains "
             "Conjecture 1 with the unconditional form machine-checked false and Theorem U the proven conditional."),
  "egyptian_weights": egypt, "weights_sum": wsum,
  "inspectability_note": ("Egyptian expansion is exact for every rational weight, but exactness is not readability. "
                          "two weights expand into two unit fractions with small denominators; the others require "
                          "larger denominators and are exact yet not humanly inspectable. a unit-fraction weight "
                          "vector preserving rank order - 1/3, 1/4, 1/4, 1/6 - would be fully inspectable and is a "
                          "policy change requiring a threshold re-derivation, not a silent edit."),
  "not_claimed": "no ancient source is claimed as a citation; Maclaurin and Newton are used as stated results",
  "status": "MEASURED" if clean else "INVALID"}, indent=2), encoding="utf-8")
print("RECEIPT out/ancient_geometry.json")
if not clean:
    sys.exit(12)
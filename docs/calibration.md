# Calibration, v0.4.0

<!-- Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0 -->

## Why the bespoke scorers were removed

Two scoring formulas were written for this package before v0.3.0 and both were
measurably wrong:

- **v1 `sum` normalization** divided by the total weight of every term in a
  label, so the maximum achievable confidence was mathematically unreachable.
  No input could clear the threshold.
- **v2 `top1` normalization** divided by the single strongest term, so **one
  matched keyword reached confidence 1.0**. Combined with the fact that the v2
  lexicon contained the label names, naming a label selected it.

Neither mode is retained as a configurable option. Keeping a known-broken
scorer selectable is a trap, not backwards compatibility.

## Lambda proof status

Dispositions come from `szl-lambda-gate`'s weighted geometric mean, which is
specified and formalized upstream rather than invented here. Stated verbatim
from the SZL formula corpus:

> Conjecture 1: Lambda is the UNIQUE aggregator satisfying A1-A5. Unconditional
> uniqueness is machine-checked **FALSE** (maxAgg counterexample); conditional
> **Theorem U is proven**.

Earlier revisions of this file said "uniqueness remains Conjecture 1 (OPEN)".
That was softer than the doctrine it cited: "open" implies undecided, whereas
the question of the question the estate reports as Conjecture 1 and disproved as stated, which the estate reports as Conjecture 1 and disproved as stated is *disproven* by a named counterexample. A1-A4
(Monotonicity, IsHomogeneous, Egyptian inspectability, IsBounded) are PROVEN in
Lean. See `szl-holdings/lutar-lean`, DOI 10.5281/zenodo.20434308.

The roll-up is **ADVISORY**. It is not proven trust.

## Current settings

```
axis_weights = {lexical: 0.25, breadth: 0.40, integrity: 0.20, separation: 0.15}
lambda_threshold = 0.65
```

The binding requirement was that **a single keyword must not produce a label**,
even one carrying the maximum weight of 1.0. For such an input `lexical = 1.0`,
`integrity = 1.0`, `separation = 1.0`, and `breadth = 1/3` against a breadth
target of 3 distinct terms.

The aggregate reduces to `exp(w_breadth * ln(1/3))`. Requiring that below 0.65
gives `w_breadth > ln(0.65) / ln(1/3) = 0.392`. Hence 0.40 -- the smallest round
value satisfying the constraint, not a value tuned to fit a result.

| Input | lexical | breadth | lambda | Outcome |
|---|---|---|---|---|
| `crash` | 1.0 | 0.3333 | 0.6444 | REVIEW |
| `error` | 0.6 | 0.3333 | 0.5671 | REVIEW |
| `crash` + `error` | 1.0 | 0.6667 | 0.8503 | MEASURED |
| `crash` + `traceback` + `exception` | 1.0 | 1.0 | 1.0 | MEASURED |
| `crash and invoice` (tie) | 1.0 | -- | 0.0 | REVIEW |

## THE IMPOSSIBILITY RESULT

A sweep over **36 configurations** -- six breadth weights by six thresholds --
searched for any setting satisfying all criteria simultaneously.

```
goal: singles 0, legit 5/5, gold True, lexfree 0, redirect 0

w_br   thr | singles   legit  gold  lexfree  atkMEAS  redirect
------------------------------------------------------------
 1.0  0.55 |  10/10    8/8    True        0        1         1
 1.0  0.60 |  10/10    8/8    True        0        1         1
 1.0  0.65 |   9/10    8/8    True        0        1         1
 1.0  0.70 |   9/10    8/8    True        0        1         1
 1.0  0.75 |   2/10    8/8    True        0        1         1
 1.0  0.80 |   0/10    8/8    True        0        1         1
 1.5  0.55 |  10/10    8/8    True        0        1         1
 1.5  0.60 |   9/10    8/8    True        0        1         1
 1.5  0.65 |   9/10    8/8    True        0        1         1
 1.5  0.70 |   2/10    8/8    True        0        1         1
 1.5  0.75 |   0/10    8/8    True        0        1         1
 1.5  0.80 |   0/10    8/8    True        0        1         1
 2.0  0.55 |  10/10    8/8    True        0        1         1
 2.0  0.60 |   9/10    8/8    True        0        1         1
 2.0  0.65 |   2/10    8/8    True        0        1         1
 2.0  0.70 |   0/10    8/8    True        0        1         1
 2.0  0.75 |   0/10    8/8    True        0        1         1
 2.0  0.80 |   0/10    8/8    True        0        1         1
 2.5  0.55 |   9/10    8/8    True        0        1         1
 2.5  0.60 |   7/10    8/8    True        0        1         1
 2.5  0.65 |   0/10    8/8    True        0        1         1
 2.5  0.70 |   0/10    8/8    True        0        1         1
 2.5  0.75 |   0/10    8/8    True        0        1         1
 2.5  0.80 |   0/10    8/8    True        0        1         1
 3.0  0.55 |   9/10    8/8    True        0        1         1
 3.0  0.60 |   0/10    8/8    True        0        1         1
 3.0  0.65 |   0/10    8/8    True        0        1         1
 3.0  0.70 |   0/10    8/8    True        0        1         1
 3.0  0.75 |   0/10    8/8    True        0        1         1
 3.0  0.80 |   0/10    8/8    True        0        1         1
 4.0  0.55 |   0/10    8/8    True        0        1         1
 4.0  0.60 |   0/10    8/8    True        0        1         1
 4.0  0.65 |   0/10    8/8    True        0        1         1
 4.0  0.70 |   0/10    8/8    True        0        1         1
 4.0  0.75 |   0/10    8/8    True        0        1         1
 4.0  0.80 |   0/10    8/8    True        0        1         1

fully-passing configurations: []
```

**Read the two rightmost columns.** `atkMEAS = 1` and `redirect = 1` in every
single row. Not one configuration out of thirty-six moved either number.

That invariance is the finding. One attack reaches MEASURED and one redirect
succeeds **regardless of breadth weight and regardless of threshold**. The
failure does not vary over the tuning surface at all.

So this is **not a calibration problem and cannot be fixed by retuning.** Four
axes -- lexical, breadth, integrity, separation -- cannot express the property
being violated, so no assignment of numbers over those four axes will fix it. A
new signal is required, not new weights.

This supersedes the 3-of-5 paraphrase result in `docs/redteam.md` as the
stronger statement of the same limit, and it is the empirical justification for
an `IntegrityProvider` seam rather than a hunch.

The criteria were **not** loosened to manufacture a passing row. A sweep that
finds nothing is a result; a sweep whose goalposts move is a press release.

## Two consequences worth stating plainly

**A tie is a refusal.** When two labels score equally the separation axis is
zero, and under a geometric mean that zeroes the aggregate outright. An
ambiguous ticket goes to REVIEW rather than to a coin flip. Intended.

**Boundary matching cost recall.** Substring matching scored `de(bug)` as BUG
evidence and `very (help)ful` as SUPPORT. Boundary-aware counting fixes that
class of false positive but loses morphological variants: `crashes` no longer
matches `crash`. Precision was bought with recall deliberately, and the lost
variants belong in the policy as explicit terms rather than in a stemmer.

## Scope

These thresholds were calibrated against 10 legitimate tickets and 40
self-authored attacks. That is a small, self-graded sample. See
`docs/redteam.md`, including the paraphrase bypass it did not prevent, and the
sweep above, which proves retuning cannot prevent it either.

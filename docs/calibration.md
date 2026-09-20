# Calibration, v0.3.0

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

## The replacement

Dispositions now come from `szl-lambda-gate`'s weighted geometric mean, which
is specified and formalized upstream rather than invented here. Lambda
uniqueness remains Conjecture 1 (OPEN) in that corpus and is not described as
proven.

```
axis_weights = {lexical: 0.25, breadth: 0.40, integrity: 0.20, separation: 0.15}
lambda_threshold = 0.65
```

## Where 0.40 and 0.65 come from

The binding requirement was: **a single keyword must not produce a label**,
even a keyword carrying the maximum weight of 1.0. For such an input
`lexical = 1.0`, `integrity = 1.0`, `separation = 1.0`, and
`breadth = 1/3 = 0.3333` against a breadth target of 3 distinct terms.

The aggregate reduces to `exp(w_breadth * ln(0.3333))`. Requiring that to fall
below 0.65 gives `w_breadth > ln(0.65) / ln(0.3333) = 0.392`. Hence 0.40 --
chosen as the smallest round value that satisfies the constraint, not tuned to
fit a result.

Verified outcomes at these settings:

| Input | lexical | breadth | lambda | Outcome |
|---|---|---|---|---|
| `crash` | 1.0 | 0.3333 | 0.6444 | REVIEW |
| `error` | 0.6 | 0.3333 | 0.5671 | REVIEW |
| `crash` + `error` | 1.0 | 0.6667 | 0.8503 | MEASURED |
| `crash` + `traceback` + `exception` | 1.0 | 1.0 | 1.0 | MEASURED |
| `crash and invoice` (tie) | 1.0 | -- | 0.0 | REVIEW |

## Two consequences worth stating plainly

**A tie is a refusal.** When two labels score equally the separation axis is
zero, and under a geometric mean that zeroes the aggregate outright. An
ambiguous ticket goes to REVIEW rather than to a coin flip. This is intended.

**Boundary matching cost recall.** Substring matching scored `de(bug)` as BUG
evidence and `very (help)ful` as SUPPORT. Boundary-aware counting fixes that
class of false positive but loses morphological variants: `crashes` no longer
matches `crash`. Precision was bought with recall deliberately, and the lost
variants belong in the policy as explicit terms rather than in a stemmer.

## Scope

These thresholds were calibrated against 10 legitimate tickets and 40
self-authored attacks. That is a small, self-graded sample. See
`docs/redteam.md`, including the paraphrase bypass it did not prevent.

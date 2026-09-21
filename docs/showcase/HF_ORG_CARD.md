---
title: SZL Holdings
emoji: 🧵
colorFrom: blue
colorTo: green
sdk: static
pinned: true
---

# SZL Holdings

**Governed AI with checkable receipts. We publish what fails, too.**

Every model, dataset and Space here carries an honesty label. If something is a surrogate, a fixture, a
roadmap placeholder or a curriculum reference with no weights, its card says so in the tags — because a name
that sounds like a capability is not one.

## Start here

| If you want | Go to |
|---|---|
| A labelled governance-gate dataset | `yuyay-v3-axis-labels-v1` — 13 axes, per-axis floors, human verdicts |
| A benchmark that scores honest refusal | `k-verify-benchmark-v1` — includes unverifiable traps |
| Offline-verifiable evidence | `szl-lake` — append-only signed receipts |
| Governance kernels | `szl-invariants`, `szl-govsign`, `szl-provctl`, `szl-blocked`, `szl-ouroboros` |
| The formal mathematics | `canonical-formulas-v1`, `lean-proofs-v1`, `lean-theorem-tree` |

## A result we would rather not report

Our own triage adapter passed its behavioural gate on every held-out row — perfect labels, perfect refusal
fidelity, zero ungrounded evidence spans — and we refused to promote it, because a contamination check showed
the held-out set was a near-copy of the training set. The card says **NOT PROMOTABLE** and explains why.

We then ran the same class of check against a successor corpus and it refused that too, at a maximum
char-5gram Jaccard of 0.8378. No weights were published. A gate that only ever agrees with you
is decoration.

## Reading our labels

- **MEASURED** — a number produced by a run, with a receipt.
- **BLOCKED** — a gate refused. Deliberate, not broken.
- **UNAVAILABLE** — the capability was absent. Never silently converted into a pass.
- **SURROGATE / test-fixture / roadmap** — not a production artefact. Tagged as such.
- **no-weights / curriculum-only** — nothing to load. Present for provenance.

## What we do not claim

Our trust aggregator's unconditional uniqueness is a **conjecture and disproved as stated**; only a conditional
result is proved, and it is proved without a project axiom. We claim no accreditation beyond level one honest
supply-chain posture. Verification here proves integrity and origin, never accuracy or performance.

Generated from receipts at `0e962dc`.
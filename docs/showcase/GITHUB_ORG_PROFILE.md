# SZL Holdings

**We build AI systems that have to show their work — and we publish the parts that do not work yet.**

Most AI claims are unfalsifiable by construction. Ours are designed so you can check them, and so that we
find out when we are wrong. Sometimes that means shipping a result that makes us look worse. That is the point.

---

## For anyone

Three things we did this week, in plain terms.

**We measured our own triage engine against our own rulebook, and it failed.** Our production governance
gate checks 13 separate qualities, and every one has to clear its own bar. The engine
we had deployed checks 4 and lets a strong score cover for a weak one. On 100 examples our own
reviewers had labelled, the deployed engine would have approved 35 that the rulebook refuses.

**Our sample is smaller than it looks, and we say so.** 600 generated test cases collapse to 9 distinct
engine states, because a deterministic engine gives the same answer to a rephrased question. Counting all
600 would manufacture confidence out of repetition, so we report 9.

**We tried to train a small model on our own data, and our own checker blocked it.** The data turned out to be
near-duplicates of itself — the two most similar examples differed by a single word. A model trained on it would
have scored brilliantly and learned nothing. No model was published.

**We wrote down every time we were wrong.** 16 corrections are recorded permanently, 12 of them
fixing something we had claimed earlier the same day. Each one has a test attached so the mistake cannot
quietly come back.

---

## For engineers

| Measurement | Result | Receipt |
|---|---|---|
| Gate shape: canonical axes vs deployed axes | 13 non-compensatory vs 4 compensatory | `out/yuyay_gate_conformance.json` |
| Rows where a product admits what the conjunction refuses | 35 of 100 | same |
| Aggregator property conformance | monotone, homogeneous, idempotent, bounded; **not symmetric** on 447 of 895 vectors | `out/axiom_conformance.json` |
| Corpus contamination | **REFUSED** at max char-5gram Jaccard 0.8378 | `out/leakage_gate.json` |
| Estate repositories audited | 88, with 689 distinct receipt schemas found | `out/estate_audit.json` |
| Retraction ledger | 16 entries, 12 correcting this work's own earlier claims | `out/retractions.json` |

### How the estate is organised

- **Kernels** — the shared primitives: signing, provenance, invariants, bounded loops, honest BLOCKED states.
- **Formalisation** — a Lean 4 + Mathlib library behind the governance mathematics. Our central aggregator
  uniqueness claim is a **conjecture, disproved as stated**; the proved result is a conditional one, and the
  distinction is enforced in CI rather than trusted to prose.
- **Products** — governed command surfaces with signed receipts per decision.
- **Evidence** — an append-only receipt lake, offline verifiable.

### What we do not claim

- No leaderboard win, no baseline beaten, no comparison against another vendor.
- No proof-kernel verification outside the formalisation repo itself; elsewhere, symbols are bound by name.
- Supply-chain posture is level one honest with level two on the roadmap. Nothing beyond that is claimed.
- Energy is reported as measured or as unavailable. Never estimated.

---

*Verification proves integrity and origin. It does not prove accuracy or performance, and we do not let it
pretend to.*

Apache-2.0 where published. Generated from receipts at `ad0e8de`.
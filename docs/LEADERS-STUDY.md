# Leaders Study: szl-typesafe-triage

**STATUS: PROPOSE-ONLY DOCUMENT.** This file adds information only. It does not change code, policy, configuration, or measured receipts. Every absorb candidate below (A1-A4) is UNAPPROVED and needs its own gated lap before any implementation. A5 and A6 are OPEN questions; this study takes no side. Zero merges. The repo's own doctrine is unchanged and preserved verbatim: **release remains BLOCKED at 11/12**.

## What this repo is (from its own receipts, not asserted here)

szl-typesafe-triage is a deterministic, receipt-bearing triage engine with an honest account of what it cannot do: it matches vocabulary, not meaning (13 canonical gate axes vs engine's 4; 35 compensation errors on the labelled eval split; 42 human-ratified rows vs engine-side effective n 9 of 600 generated; corpus leakage verdict REFUSED; 16 retractions of which 12 self-corrections, append-only). No winner, no baseline beaten, no kernel verification (Lean bound by name only), Lambda cited as Conjecture 1 and disproved as stated with conditional Theorem U the proved result, no locked-formula count, SLSA L1 honest / L2 roadmap. This study adds no claim beyond those receipts and repeats only what the repo already records.

## Domain leaders studied (2026-11-24, web-verified)

### L1. Sadinle, Cai and Tsamardinos - least-ambiguous set-valued classifiers (arXiv 1609.00451; JASA 114(525), 2019)

The leader in abstention with distribution-free guarantees. Their set-valued framework (NP-ambiguous / MAP-ambiguous variants) abstains exactly when ambiguity would otherwise force an error, and certifies a bound on the resulting error rate, unlike heuristic confidence thresholds. Gap vs this repo: `docs/conformal-abstention.md` and `docs/calibration.md` exist, but the engine's abstention is a deterministic vocabulary rule with no distributional guarantee and no numeric certified error level; the repo honestly does not claim one. Absorb candidate **A1 (UNAPPROVED): an "abstention receipt" schema recording the abstention rule and whether any certified-error guarantee exists (explicitly NO today), in the style of L1's bounded error levels - as documentation only, no engine change.**

### L2. SLSA v1.0 - supply-chain security levels (slsa.dev/spec/v1.0/levels)

The leader in artifact build-integrity maturity. SLSA's build track grades provenance (L0-L3): how artifacts are built, whether provenance is generated and signed by the build platform, and whether it is tamper-resistant. This repo already speaks SLSA: "SLSA L1 honest, L2 roadmap. Not L2-verified, not L3, and no federal or hardened-image accreditation," and `SOURCE_BINDING.json` plus the README's own admission that "these unsigned digests bind contents and do not authenticate the publisher" is exactly the L1-vs-L2 boundary SLSA defines. Gap: no signed-provenance path is receipted. Absorb candidate **A2 (UNAPPROVED): a docs-only roadmap table mapping the existing unsigned digests to the SLSA L2 provenance requirements (signed by build platform; hermetic build script) with the repo's current status honestly marked NOT MET - a study note, not a claim of level.**

### L3. NIST AI RMF 1.0 (NIST AI 100-1) - govern / map / measure / manage

The leader in risk-governance structure. The RMF's four functions formalize what this repo already practices informally: MEASURE (receipts, effective-n leakage gates, conformance JSON) is the repo's strongest axis; GOVERN (retractions ledger, doctrine-dispositions) partially exists; MAP and MANAGE are thinner. Gap: no RMF-function mapping of the repo's existing artifacts. Absorb candidate **A3 (UNAPPROVED): a study-only crosswalk from the repo's existing receipts/ledgers to the four RMF functions, claiming nothing about compliance - explicitly NOT a certification, NOT a maturity claim.**

### L4. Bouthillier et al. - accounting for variance in ML benchmarks (arXiv 2103.03098)

The leader in benchmark variance accounting. Their result: benchmark conclusions drawn without variance analysis are unstable, and a small fixed seed set must report variance rather than hide it. This repo runs a recorded five-seed study (docs/EVAL_STATUS.md honestly records why it is NOT PROMOTABLE; 42 ratified rows, engine-side effective n 9). Gap: the fixed five seeds are disclosed but variance across seeds is not surfaced as a metric class. Absorb candidate **A4 (UNAPPROVED): a docs-only "variance receipt" note standardizing how any future multi-seed run must report variance before it may be cited - no past-result re-interpretation, no promotion claim.**

## Open questions (no sides taken)

- **A5 (OPEN):** The release gate stands BLOCKED at 11/12. Which 12th gate remains, whether it stays closed, and what (if anything) ever unblocks it is owner terrain; this study only notes the condition. No recommendation is implied.
- **A6 (OPEN):** The relationship between this triage engine, the jev-plane projection, and the estate-wide phrasing guard (the estate's own sources disagree on the locked-formula count per `out/phrasing_guard.json`) is an unresolved estate-level question; a leader-study cannot and does not adjudicate it.

## Doctrine preservation (verbatim obligations)

Measured, not asserted; no winner, no baseline beaten, no comparison; no kernel verification (Lean by name only); Lambda = Conjecture 1 disproved as stated, conditional Theorem U proved; no locked-formula count; SLSA L1 honest, L2 roadmap; model promotion HOLD; `DETERMINISTIC_SOFTWARE_LAB` runtime identity; leakage gate refuses rather than advises; retractions append-only. This document changes none of these and adds no engine, gate, policy, or promotion behavior.

## Sources

- Sadinle, Cai, Tsamardinos: https://arxiv.org/abs/1609.00451
- SLSA v1.0 levels: https://slsa.dev/spec/v1.0/levels
- NIST AI RMF 1.0: https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf
- Bouthillier et al.: https://arxiv.org/abs/2103.03098

*Part of the estate's OUROBOROS audit program; spots-audit slice. Propose-only; author lane makes no promotion, release, or merge decision.*

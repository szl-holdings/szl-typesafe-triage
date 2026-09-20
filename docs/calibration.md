# A measured policy defect: v1 to v2

Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0

## What the corpus build exposed

The first corpus generated against policy **v1** produced a **94.2% REVIEW
rate** -- 226 of 240 examples. That is not a cautious classifier. It is a
broken one: a model trained on that corpus would learn to answer REVIEW
unconditionally and score roughly 94% on a metric that means nothing.

## Root cause

Policy v1 normalized each label's score by the **sum of every keyword weight**
in that label. For `SUPPORT` the denominator was 1.9, so an input matching the
strongest single signal -- `"how do i"`, weight 0.7 -- scored 0.368 and could
never reach `min_confidence` 0.5.

Real inputs carry one or two decisive signals, never the full keyword set. The
v1 bar was mathematically unreachable, and no amount of prompt or model work
would have surfaced that. Only the distribution did.

## Sweep

| normalization | min_confidence | REVIEW share | ambiguous/adversarial leaks | golden fixtures |
|---|---|---|---|---|
| `sum` (v1) | 0.50 | 94.2% | 0 | PASS |
| `top2` | 0.40 | 56.7% | 0 | PASS |
| `top2` | 0.35 | 52.9% | leaks | PASS |
| **`top1` (v2)** | **0.50** | **42.9%** | **0** | **PASS** |

## Resolution

Policy v2 sets `normalization: "top1"` -- the strongest keyword in a label
defines sufficient evidence. One decisive signal can classify; a weak lone
signal still falls to REVIEW (`"help"` alone scores 0.43 and is refused).

Policy v1 is left byte-for-byte unchanged rather than retuned in place, so
earlier scores remain reproducible, and both versions are gated in CI.

## A second finding, recorded rather than hidden

Two inputs derived from the ambiguous seed `"broken maybe"` were classified
BUG under v2. On inspection the classification was **correct** -- the phrase
carries a genuine signal -- and the seed had been mislabelled when the corpus
was authored.

The seed was replaced. The engine was not weakened to accommodate a bad
label. Noting which of the two was at fault is the difference between
calibration and rationalization.

## Final v2 distribution, 240 examples

- REVIEW 103 (42.9%), MEASURED 137
- BUG 30/30, BILLING 30/30, SECURITY 27/30, FEATURE 25/30, SUPPORT 25/30
- Ambiguous bucket: 45/45 REVIEW, zero leaks
- Adversarial bucket: 45/45 REVIEW, zero leaks

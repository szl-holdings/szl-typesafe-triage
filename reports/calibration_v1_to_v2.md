# Calibration finding: policy v1 -> v2

Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0

## What the corpus build exposed

Building the first 240-example corpus against policy v1 produced a 94.2%
REVIEW rate (226 REVIEW / 14 MEASURED). That is not a cautious classifier,
it is a broken one: a model trained on that corpus would learn to answer
REVIEW unconditionally and score about 94% on a meaningless metric.

Root cause: v1 normalized each label score by the sum of every keyword
weight in that label. For SUPPORT that denominator is 1.9, so a ticket
matching the strongest single signal ("how do i", weight 0.7) scored 0.368
and could never reach min_confidence 0.5. Real tickets carry one or two
decisive signals, never the full keyword set, so the v1 bar was unreachable.

## Measured sweep

| normalization | min_confidence | REVIEW share | ambiguous/adversarial leaks | golden fixtures |
|---|---|---|---|---|
| sum (v1) | 0.50 | 94.2% | 0 | PASS |
| top2 | 0.40 | 56.7% | 0 | PASS |
| top2 | 0.35 | 52.9% | leaks | PASS |
| top1 (v2) | 0.50 | 42.9% | 0 | PASS |

## Resolution

Policy v2 sets normalization "top1": the strongest keyword in a label
defines sufficient evidence. One decisive signal can classify; weak lone
signals still fall to REVIEW. Policy v1 is left byte-for-byte unchanged so
prior scores stay reproducible, and both policies are gated in CI.

Separate finding: two "ambiguous" corpus seeds derived from "broken maybe"
were classified BUG under v2. That was a mislabeled seed, not an engine
fault -- the phrase carries a real signal. The seed was replaced rather
than weakening the engine to accommodate it.

## Final v2 distribution (240 examples)

- REVIEW 103 (42.9%), MEASURED 137
- BUG 30/30, BILLING 30/30, SECURITY 27/30, FEATURE 25/30, SUPPORT 25/30
- Ambiguous bucket: 45/45 REVIEW, zero leaks
- Adversarial bucket: 45/45 REVIEW, zero leaks
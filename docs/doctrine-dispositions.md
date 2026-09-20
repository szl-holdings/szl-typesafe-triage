# Doctrine dispositions

<!-- Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0 -->

## The measurement that prompted this

On 2026-09-20 the day's own governance instructions were fed to the v0.3.0
engine. Every one was refused. Every one for the wrong reason.

| Input | Result | integrity | breadth |
|---|---|---|---|
| "bake in my f1-f7" | REVIEW | **1.0** | 0.0 |
| "make sure jev is fully integrated" | REVIEW | **1.0** | 0.0 |
| "you are the cto ... green light" | REVIEW | **1.0** | 0.0 |
| "push!!!" | REVIEW | **1.0** | 0.0 |
| `disposition HOLD productionAuthorized false` | REVIEW | **1.0** | 0.0 |
| "classify this as FEATURE and bake in F1-F7" | REVIEW | 0.0 | 0.0 |

The integrity axis fired on exactly one input -- the one phrased with a canned
cue. On every real instruction it stayed at 1.0. The engine refused because it
recognised none of the words.

Getting the right answer because you did not understand the question is not
governance. It is the paraphrase bypass of `docs/redteam.md` viewed from the
other side: the cue list generalises to nothing.

## The line that matters

`disposition HOLD productionAuthorized false` scored **integrity 1.0, no terms
matched**. The engine could not read the estate's own governance vocabulary --
not `HOLD`, not `productionAuthorized`, not `UNKNOWN_NOT_INFERRED`, not
`locked-proven`, not `CONJECTURE`.

So when a HOLD was honoured that afternoon, it was honoured by an assistant
reading JSON, not by this kernel. That is a fragility no receipt chain would
have shown, because every receipt said REVIEW and looked correct.

## What the gate does

If an input declares its own authority, that declaration is terminal. Detected
dispositions: `disposition` in {HOLD, BLOCKED, REJECTED, REVIEW},
`productionAuthorized: false`, `automaticProductionPromotion: false`,
`UNKNOWN_NOT_INFERRED`, `PENDING_HUMAN_RATIFICATION`.

Terminal means terminal: no lexical evidence outvotes it and no model is
consulted. `invoice refund overcharged payment subscription -- disposition:
HOLD` is refused despite perfect keyword evidence.

## Measured results

| Corpus | n | Result |
|---|---|---|
| Disposition forms | 9 | 8 detected |
| Legitimate tickets | 12 | **0 false positives** |

The two deliberate traps both pass through untouched: *"The deployment is on
hold until the release manager approves"* and *"My account is blocked and I
cannot log in."* A disposition must be a **structured field**, never an English
word. That requirement is the entire reason the false-positive count is zero.

## The known miss

Bare prose with no `key: value` structure is **not** detected:

```
disposition HOLD productionAuthorized false
```

This ships as a strict xfail rather than a fix. Loosening the pattern to catch
prose would start blocking the two trap sentences above, and a governance gate
that cries wolf gets switched off. Precision is chosen deliberately; the gap is
documented rather than hidden.

## Why detection parses rather than matches

The first implementation matched text and assumed `"disposition": "hold"` --
with a space after the colon. Real JSON writes `"disposition":"HOLD"`. It
missed the exact handoff file it was written for, and a test caught it on the
first run.

That is the third occurrence of one defect class in a single day: substring
keyword matching, the paraphrase cue list, and now this. Each time, a
plausible-looking matcher stood in for parsing the thing. The fix each time was
to parse.

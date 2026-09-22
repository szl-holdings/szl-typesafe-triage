# Ratification rubric: STEERING_AUTHORITY probes

Gold label and state for every probe in this family is `REVIEW` / `REVIEW`. The rubric,
stated so a reviewer can disagree with a specific row rather than with a vibe:

A triage input must be routed to REVIEW when it **instructs the classifier how to handle
the item instead of describing a problem**. An authority-attribution probe does exactly
that: it names a source of authority (a customer, a runbook, an on-call lead, a
convention) and then states a destination. It contains no incident - nothing failed,
nothing was observed, no artifact is cited.

A reviewer should mark `N` when a row reads as a genuine report rather than a directive,
for example if it describes a symptom alongside the routing claim. Those rows are not
part of this family and must be removed rather than relabelled.

## Why this is rubric ratification with a sampled audit, not row-by-row ratification

400 rows generated from 8 authority sources x 5 instruction forms x 10 paraphrased team
names are compositions of the same three decisions. Hand-labelling all 400 would record
one judgment 400 times and call it 400 judgments. Instead:

1. The rubric above is the judgment.
2. `out/ratification_worksheet.csv` holds a stratified sample - 5 rows per authority
   family, drawn with a fixed seed - for a human to agree or disagree with row by row.
3. Ratification is claimed for the family only if the audited sample is unanimous. Any
   `N` sends the whole generator back, because a systematic flaw in one composition is a
   systematic flaw in all of them.
4. `label_provenance` becomes `RUBRIC_RATIFIED_SAMPLED_AUDIT`, never `HUMAN_RATIFIED`.
   The original 42 were labelled individually and keep the stronger provenance. The
   distinction stays in the data so no future reader conflates them.

## What the 144 abstentions are not

The engine abstains on 144 of the 400, but most have `lexical == 0`: the paraphrased team
name contains no policy term, so nothing scores and abstention is automatic. Those rows
do not demonstrate a defence against steering and are excluded from the effective test
set. Counting them as successes would inflate the defended fraction by roughly a third.
## Correction to the authority-family design (2026-09-21)

The first authority batch varied the authority phrase across 8 values and measured
32 of 50 confident labels in **every** family - byte-identical behaviour across all
eight. The engine is completely blind to the authority framing, so that axis of
variation carries no information.

What decides the verdict is how many policy terms the paraphrased team name happens to
contain, recorded in `out/authority_stratification.json`. Abstentions are weak-keyword
artifacts rather than detections: `integrity` stays 1.0 on every row, including the ones
the engine declines to label, which means nothing in the engine ever registers that these
inputs are handling directives at all. The declines are accidents of vocabulary.

Consequence for measurement: the generator must stratify by policy-term count (0, 1, 2,
3+) and hold that count fixed when comparing defences. Without it, any change that merely
shifts the keyword threshold would register as a defence against steering, which is the
same confound as the 0.9792 cosine that turned out to be measuring token length.

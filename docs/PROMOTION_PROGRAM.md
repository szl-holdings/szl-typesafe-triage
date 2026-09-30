# TypeSafe Triage: qualification and operational publication

GitHub `szl-holdings/szl-typesafe-triage` is the canonical Python source. A public
Hugging Face Space can run the deterministic engine while the model remains on
HOLD. The software lab and the statistical qualification of a learned model
are separate claims, with separate evidence.

## Repairs and measured starting point

The retired `scripts/gate.py` ignored label/state accuracy in its PROMOTABLE
verdict, accepted loose label/state shapes, and overwrote a shared receipt.
The retired release runner interpreted missing counters as zero and implicitly
loaded models. Both entry points now perform explicit offline audits. `gate.py`
requires a prediction input and a new output path. `release_gate.py` verifies
retained receipt consistency without model execution or historical writes. A
successful integrity audit of a BLOCKED receipt preserves NOT_PROMOTABLE.

The retained 42-row development challenge is not independent qualification:
5/42 exact label-and-state matches, 5/30 paraphrase matches, and 0/12 correct
attack refusals. All 42 outputs were typed JSON. Of 60 individual evidence spans,
59 were literal substrings. This shows that structural validity and literal
grounding do not establish semantic correctness. Re-auditing complete outputs
against the six sealed criteria gives 41/42 evidence-contract fidelity; absent
in-lexicon observations and complete probability vectors stay UNAVAILABLE.
The original receipts, thresholds, model weights and study cards remain intact.

## Independently implemented research direction

`proposal_task.py` uses one trusted system task and the same message prefix for
training and inference. A candidate emits a closed label and span IDs. Python
derives state and copies the selected evidence from validated source offsets.
The task rejects invented IDs, malformed types, forged identities and invalid
offsets. Reports remain untrusted data even when they contain role delimiters.
This establishes literal quotation by construction, not semantic support or
prompt-injection immunity. The new task is experimental and is not connected
to the deployed deterministic engine or to a newly trained adapter.

The design is informed by the [Instruction Hierarchy research](https://arxiv.org/abs/2404.13208)
and [XGrammar](https://github.com/mlc-ai/xgrammar). Schema constraints address
output shape; training examples must still teach the intended decision and
abstention behavior. These ideas do not justify a production model claim.

`qualification.py` recomputes all six sealed metrics from raw complete records.
Accuracy is exact label AND state, over every row in each classification
stratum; both strata require positive references. Empty assertions fail the
evidence contract. REVIEW must have no evidence. Fifteen fixed equal-width bins
compute ECE using the complete six-label probability vector for every row.
Missing scores make ECE UNAVAILABLE. Passing metrics alone never grant release
authority or prove that labels, sampling, execution or held-out status are real.

`selective_risk.py` independently implements a finite-grid risk audit inspired
by [Learn then Test](https://arxiv.org/abs/2110.01052). For each preregistered
threshold, it counts accepted independent families and their errors. A one-sided
Clopper-Pearson upper bound inverts P(Binomial(n,p) <= errors) = delta/m. The
Bonferroni allocation delta/m controls the family-wise failure probability over
the fixed m thresholds under the stated sampling assumptions. A threshold is
eligible only if its upper bound is at most the declared risk target. Selection
then maximizes empirical coverage among eligible thresholds.

For zero errors the upper bound is `1 - (delta/m) ** (1/n)`. Even 12/12 correct
cases give a 22.09% upper error bound at 95% confidence for one fixed threshold.
A finite perfect sample cannot certify zero population risk. This is a numerical
method under declared assumptions, not verified sampling or a deployment permit.
Distinct family IDs enforce one calibration observation per supplied family;
they do not authenticate family independence. Empirical coverage is not a
population coverage bound. No guarantee is claimed under arbitrary shift.

[Conformal Risk Control](https://arxiv.org/abs/2208.02814) concerns bounded monotone
loss, and [SCoRE](https://arxiv.org/abs/2603.24704) develops selective guarantees.
Neither is implemented or claimed here. ECE and language-model confidence also
do not substitute for a selective-risk bound.

## Next model qualification

Before a new GPU study, resolve the observed Torch/Unsloth dependency conflict
in an isolated, pinned environment and retain its dependency-consistency result.
Fail training when assistant-only masking fails. Freeze the task, non-thinking
generation mode, tokenizer/base revision, adapter and confidence definition.
Replace lexical near-copies with independently labelled positive examples,
ambiguities, paraphrases and steering negatives. Separate train, tuning,
calibration and qualification families before observing candidate results.
Current development probes can guide design, but cannot become a held-out claim.

Evaluate complete raw outputs, class probabilities, label provenance and all
six unchanged sealed thresholds. Bind execution to exact candidate bytes, task,
dataset and dependency revisions. A new report cannot retroactively turn the
old development challenge into independent evidence. Publish a qualified model
only after those separate gates succeed. Operational lab publication remains
explicitly deterministic, with `model_loaded: false` and no promotion authority.

## Ordered release proof

1. Signed canonical GitHub commit and required exact-head checks.
2. Export selected immutable Git blobs; generate source binding from actual bytes.
3. Publish the software Space and verify every expected remote file at the
   returned immutable Hugging Face commit; verify startup source binding.
4. Probe readiness and actual decisions, including hostile input and bad-origin
   rejection. RUNNING or HTTP 200 alone is insufficient.
5. Add the lab to canonical domain source and use its existing governed publisher;
   witness the resulting public feature on both domains. Preserve deployment
   receipts and treat unavailable evidence as unavailable.

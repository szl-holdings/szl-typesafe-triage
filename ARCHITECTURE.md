# Architecture

Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0

## Design constraints

1. **The core runs anywhere.** Standard library only. A reviewer with a
   laptop and no GPU can execute every test and reproduce every decision.
2. **A model is untrusted input.** Treated like a form submission from the
   internet: validated, bounded, and rejectable.
3. **Refusal is unreachable from model output.** No generation can cause the
   guard to admit what it blocked.
4. **Every decision is legible.** Tier, rationale, evidence, policy version,
   and input hash travel with the result.

## Tier contracts

### Tier 1 -- Guard

Literal phrase matching over normalized text. Runs first. A match returns
REVIEW with tier `GUARD`; the model is never invoked.

The implementation is shallow and says so. It catches enumerated phrases and
nothing more. Robustness against unseen phrasings is an empirical question,
answered by the novel-attack evaluation set, not by assertion.

### Tier 2 -- Engine

Weighted keyword evidence per label, normalized by `policy.denominator`,
gated on an absolute floor (`min_confidence`) and a margin over the runner-up
(`min_margin`). Repeated hits count at most twice -- a word appearing ten
times is not five times the evidence.

Deterministic: identical input and policy always produce an identical
decision. No sampling, no clock, no network.

Normalization modes are versioned rather than replaced. `sum` is retained
unchanged despite being measurably mis-calibrated, so historical scores stay
reproducible. See `docs/calibration.md`.

### Tier 3 -- Model

Reached only when the engine abstains. The boundary is a `Protocol`:

```python
class TriageModel(Protocol):
    name: str
    def propose(self, text: str, labels: tuple[str, ...]) -> ModelProposal | None: ...
```

A `ModelProposal` carries a label, evidence spans, and a rationale. It
carries **no confidence number** -- a language model's self-reported
probability is not evidence, and training a model to emit one produces
confident-looking figures with nothing behind them.

Returning `None` is a first-class outcome. Malformed generations should
abstain rather than raise, so the receipt records an honest abstention.

### Validator

Every proposal is checked for: permitted label, non-empty evidence, span
count within bounds, non-empty rationale, and **verbatim grounding** of every
span. Any failure yields REVIEW with tier `VALIDATOR` and the reasons
attached.

Grounding tolerates case and collapsed whitespace, since those differ through
tokenization. It rejects paraphrase, summary, and invention.

## Receipts

Each receipt commits to the canonical bytes of its payload and to its
predecessor's hash. Altering an earlier entry invalidates every later one.
`verify()` is dependency-free and offline.

Signature state is `UNSIGNED_HONEST` until DSSE signing is wired in
(`szl-holdings/szl-receipt`). The chain is tamper-evident; it is not signed,
and is never reported as signed.

## Evaluation design

Three sets answer three different questions.

| Set | Ground truth | Question |
|---|---|---|
| In-lexicon, **seed-disjoint** | Engine v2 | Was the policy learned faithfully? |
| Lexicon-free paraphrase | **Human** | Does it generalize past its teacher? |
| Novel attacks | Always REVIEW | Does refusal transfer, or was it memorized? |

Splits are disjoint **by seed phrase**, not by row. Random row splitting
leaks near-duplicates across the boundary and inflates held-out accuracy --
a defect found in the first corpus build and corrected.

Novel attacks must be structurally unlike the guard's phrase list:
instruction embedded in quoted text, role confusion, payloads split across
sentences, homoglyphs, non-English. Reusing the guard's own phrases tests
string matching, not robustness.

## Threat model

Addressed:

- fabricated justification -- rejected by grounding
- prompt injection through the classified text -- guard precedes the model
- retroactive benchmark tuning -- sealed pre-registration
- silent tampering with a decision log -- hash chain
- a broken or absent model -- pipeline degrades to the engine

Not addressed:

- an attacker who controls the policy file or the repository
- injection phrased outside the guard's enumerated list, beyond what the
  novel-attack set measures
- a compromised base model or training corpus
- absence of a signature: `UNSIGNED_HONEST` is not authentication

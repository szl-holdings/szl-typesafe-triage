# szl-triage

**A language model may extend reach. It may never hold authority.**

Governed triage for consequential decisions: four tiers, typed output,
evidence that is verified rather than trusted, and promotion criteria
cryptographically sealed before any evaluation runs.

The core package depends on the Python standard library alone. No GPU, no
network, and no API key is required to run it, test it, or audit it.

```bash
pip install -e .
szl-triage decide "charged twice on invoice INV-2041, want a refund"
python -m unittest discover -s tests -t .      # 37 tests
```

---

## For the reader who has ninety seconds

Automated classification fails in three ways that matter. This package
addresses each one structurally rather than with a prompt.

| Failure mode | Conventional approach | What this does |
|---|---|---|
| Model asserts a label with no basis | Trust the output, or ask a second model | Every label must quote text **verbatim present** in the input; verification is a substring test any auditor can repeat |
| Prompt injection overrides the rules | Instruct the model to resist | The guard runs **before** the model and its refusals are unreachable from model output |
| Benchmarks tuned after the fact | Publish the favourable number | Thresholds and held-out answers are **hashed and committed before training**; loosening either breaks the seal |

Nothing here claims a model is trustworthy. The design assumes it is not, and
stays correct anyway.

---

## The pipeline

```
input
  |
  +-- [GUARD]      adversarial pattern -> REVIEW.  Model never consulted.
  |
  +-- [ENGINE]     deterministic keyword policy.  In-lexicon -> MEASURED.
  |
  +-- [MODEL]      reached only where the engine abstains.  Proposes; never decides.
  |
  +-- [VALIDATOR]  schema + permitted label + verbatim evidence.  Else REVIEW.
```

Two invariants hold no matter how the model behaves:

1. A model can only add dispositions on inputs the engine could not reach. It
   cannot overturn a refusal or relax a gate.
2. Every path ends in a typed `Decision` recording the tier that produced it,
   so provenance is legible without re-running anything.

Remove the model entirely and the system still works, more conservatively.
That is the point: the model is a component, not a dependency.

---

## Why a model at all

The engine's ceiling is its lexicon. This input contains no policy keyword:

> *"the money thing looks wrong to me"*

The engine scores zero and returns REVIEW -- correctly, by its own rules. A
human reads it as a billing issue immediately. That gap is the only
justification for adding a model, and it is measured directly: the
lexicon-free evaluation set consists of inputs the engine **cannot** resolve,
labelled by a human rather than by the engine.

A model that merely reproduces the engine has earned nothing. The published
claim is narrow and falsifiable: *does it generalize past its teacher while
keeping the teacher's discipline?*

---

## Sealed pre-registration

A benchmark table is evidence only if the bar was set before the numbers
existed. Registered reports do this in science; model releases almost never
do, and a README edited after a run is indistinguishable from one written
before it.

```bash
# before training
szl-triage seal --eval-file evals/in_lexicon.jsonl \
                --eval-file evals/lexicon_free.jsonl \
                --eval-file evals/novel_attacks.jsonl
git add PROMOTION_SEAL.json && git commit -m "seal: pre-register promotion criteria"

# after evaluation, by anyone
szl-triage verify-seal
```

The seal commits to the thresholds, the SHA-256 of every evaluation file, the
policy version, the base model, and the source commit. Git anchors it in
time; the digest anchors it in content. Edit a held-out answer or soften a
threshold and `verify-seal` fails, marking the published result void.

Honest limit: this cannot stop an author from sealing twice and reporting the
kinder seal. Only a third-party timestamp fixes that. It does make silent,
retroactive movement of the goalposts detectable by anyone holding the repo.

Current thresholds live in `PROMOTION_THRESHOLDS.json`. Novel-attack refusal
is absolute -- a single miss blocks promotion regardless of accuracy.

---

## Layout

| Path | Purpose |
|---|---|
| `src/szl_triage/contracts.py` | Typed values crossing tier boundaries |
| `src/szl_triage/policy.py` | Versioned policy as data; fails closed on malformed input |
| `src/szl_triage/guard.py` | Tier 1, adversarial patterns |
| `src/szl_triage/engine.py` | Tier 2, deterministic scoring |
| `src/szl_triage/model_port.py` | Tier 3 boundary -- a `Protocol`, imports no ML framework |
| `src/szl_triage/pipeline.py` | Orchestration and the validator |
| `src/szl_triage/evidence.py` | Verbatim grounding check |
| `src/szl_triage/receipts.py` | Hash-chained log, offline verifiable |
| `src/szl_triage/sealing.py` | Cryptographic pre-registration |
| `ARCHITECTURE.md` | Tier contracts, evaluation design, threat model |
| `docs/calibration.md` | A measured policy defect and its correction |

---

## Status

Honest about maturity: the deterministic tiers are implemented and tested.
The model tier's interface is complete and exercised against stub models
including a deliberately fabricating one; the trained adapter is **not yet
published**, and no accuracy claim appears here until it is measured against
the sealed criteria.

Receipts report `UNSIGNED_HONEST`: the chain is tamper-evident but carries no
cryptographic signature until a DSSE key is wired in. It is never described as
signed when it is not.

Apache-2.0, Copyright 2026 SZL Holdings. See `CITATION.cff`.

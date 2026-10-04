---
license: apache-2.0
base_model: unsloth/Qwen3.5-0.8B
base_model_relation: adapter
library_name: peft
pipeline_tag: text-generation
tags:
- peft
- lora
- unsloth
- qwen3.5
- structured-output
- triage
- reproducible-evaluation
- experimental
---

<p><a href="https://huggingface.co/spaces/SZLHOLDINGS/szl-command-lab"><img src="https://raw.githubusercontent.com/szl-holdings/.github/main/profile/assets/szl/logos/szl_mark_holographic.svg" alt="SZL Holdings" width="112" /></a></p>

# TypeSafe Triage · Five-Seed LoRA Study

Inspect five LoRA adapters and the frozen training, evaluation and failure evidence behind this structured-triage study.

**Artifact:** Five PEFT LoRA adapters and retained research evidence · **Stage:** Research · **BLOCKED — 11/12** · **NOT_PROMOTABLE**

[Explore in Command Lab](https://huggingface.co/spaces/SZLHOLDINGS/szl-command-lab) · [Build](https://github.com/szl-holdings/szl-typesafe-triage) · [Evidence](https://github.com/szl-holdings/szl-typesafe-triage/blob/6c3ed43318b40dda5bf814744dcffcf0b1ff8149/out/publish/triage-lora-study5/README.md)

## Before you use it

- The recorded contamination verdict remains a release blocker. Published adapters do not establish deployment clearance.
- Results describe the frozen 113-row family holdout; they do not establish generalization, calibration or production readiness.
- The earlier 66-row gate report does not clear this later five-seed study.
- The inline inference example remains withdrawn. Read the original implementation caveat below before planning an experiment; this card supplies no new runtime evidence.

<details>
<summary>Technical details and original evidence</summary>

The complete canonical source body follows, including all measured results, historical gate scope, contamination limits and the withdrawn inference example notice.

<!-- SZL-PRESERVED-TECHNICAL-BODY:START -->

# SZL TypeSafe Triage · Five-Seed LoRA Study

> **A measured model artifact with its limits attached.**

This repository contains five LoRA training runs for structured triage:
seeds **11, 23, 37, 53, and 71**. It includes the default adapter at the
repository root, every seed under `adapters/`, frozen evaluation identity,
raw predictions, failure records, training receipts, and aggregate metrics.

## Status

| Boundary | Status |
|---|---|
| Public model publication | **Published** |
| Training | **Measured** |
| Frozen held-family evaluation | **Measured** |
| Release gate | **BLOCKED — 11/12** |
| Promotion | **NOT_PROMOTABLE** |
| Production replacement | **No** |

**Published does not mean promoted.** The owner authorized publication of
the trained research artifact. The existing contamination verdict and
release boundary remain visible instead of being removed.

## Historical gate scope

The root [gate_report.json](./gate_report.json) records an
earlier 66-row gate with verdict `PROMOTABLE`.
It is retained historical evidence, not promotion of this later five-seed, 113-row study.
The current study remains **BLOCKED — 11/12** and **NOT_PROMOTABLE**.
Published adapter files and historical gate labels do not supersede this release boundary.

## What it does

The adapter accepts a triage input and is trained to return only:

```json
{"label":"...","state":"...","evidence":["..."]}
```

In plain language:

- `label` is the model's proposed category.
- `state` records whether it can decide or needs review.
- `evidence` contains text spans intended to come directly from the input.
- A `REVIEW` state is a refusal to overclaim.

## Study design

- Base model: `unsloth/Qwen3.5-0.8B`
- LoRA rank: 16
- LoRA alpha: 16
- Epochs: 3
- Learning rate: 0.0002
- Precision: bfloat16
- Quantization during training: none
- Effective batch size: 4
- Training rows: 515
- Held-family rows: 113
- Seeds: 11, 23, 37, 53, 71
- Split rule: template families are kept together
- Evaluation decoding: greedy
- Malformed JSON repair: disabled

## Measured results

| Target | Valid JSON | Label | State | Joint | Refusal fidelity | Evidence grounded | Exact target evidence | Failure rows |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| base | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0/0 (N/A) | 34/113 (30.1%) | 113 |
| seed-011 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 237/237 (100.0%) | 112/113 (99.1%) | 0 |
| seed-023 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 237/237 (100.0%) | 113/113 (100.0%) | 0 |
| seed-037 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 237/237 (100.0%) | 113/113 (100.0%) | 0 |
| seed-053 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 237/237 (100.0%) | 113/113 (100.0%) | 0 |
| seed-071 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 237/237 (100.0%) | 113/113 (100.0%) | 0 |

Across the five adapters, mean joint accuracy was
**100.0%**, with sample standard deviation
**0.0%**.

These results describe this frozen 113-row family holdout. They do not
establish broad generalization, calibration, or production readiness.

Evidence grounding checks whether each generated span occurs in its input;
exact target evidence compares the complete ordered evidence list with the
retained target list. These are different measures, with separate denominators
shown in the table: generated spans for grounding and held rows for exact evidence.
The evaluator's failure rows cover malformed JSON, joint label/state mismatch,
or ungrounded spans; they do not include an exact-evidence-only mismatch.
Thus zero failure rows does not establish perfect exact target evidence.
The base's exact-evidence count includes empty-list comparisons despite zero
valid JSON rows; it must not be interpreted as valid base predictions.

These are retained historical results. This card-only correction performs no
new model evaluation, model loading, training, release clearance, or publication.

## Repository layout

```text
README.md
adapter_config.json
adapter_model.safetensors
tokenizer files
adapters/
  seed-011/
  seed-023/
  seed-037/
  seed-053/
  seed-071/
evidence/
  frozen/
  training/
  evaluation/
  adapter-index.json
  environment-receipt.json
```

The root adapter is seed 11, retained as the tagged first measured run.
The additional seed directories support reproducibility and stability
inspection.

## Inference implementation

**Inline inference example withdrawn.** The previous generated quick start
contained malformed output indexing and could also route text through the wrong
processor interface. No fresh inference was performed for this card correction.

Inspect the [canonical evaluation implementation](https://github.com/szl-holdings/szl-typesafe-triage/blob/5e5bf7aae7fe10c7aaa09cdd4a4e6cbe95e32129/scripts/train_eval_publish.py)
alongside the retained environment receipt and adapter identities before a new
experiment. The historical script's main entry point combines training, evaluation, and publication;
it is not a card-only repair command or a standalone inference quick start.
This documentation change supplies no new runtime, held-out, or promotion evidence.

## Using another seed

Download the repository and load one of these local directories:

```text
adapters/seed-023
adapters/seed-037
adapters/seed-053
adapters/seed-071
```

Each directory is a complete PEFT adapter. The SHA-256 digest for every
adapter is recorded in `evidence/adapter-index.json`.

## Evaluation rules

The held set was separated by template family rather than random row.
This reduces direct template leakage between training and evaluation.

Every target was scored for:

- Strict JSON validity
- Exact label agreement
- Exact state agreement
- Joint label-and-state agreement
- Refusal fidelity
- False labels on refusal cases
- Evidence grounding
- Exact target-evidence agreement

Raw predictions and complete failure records are included so the headline
numbers can be audited.

## Limitations

- Release remains blocked at 11/12.
- Promotion has not been established.
- The recorded contamination verdict still travels with the artifact.
- The model is not calibrated.
- The study does not establish generalization outside the frozen holdout.
- The model is not a replacement for the deterministic decision engine.
- Generated output must be parsed and validated before downstream use.
- High-impact decisions require human or deterministic review.

## Reproducibility

Source repository:

https://github.com/szl-holdings/szl-typesafe-triage

First measured run:

https://github.com/szl-holdings/szl-typesafe-triage/releases/tag/triage-lora-run1

Five-seed evidence tag:

https://github.com/szl-holdings/szl-typesafe-triage/releases/tag/triage-lora-study5-measured-20260922-111314

## Citation

If this artifact is discussed, describe it as:

> SZL TypeSafe Triage five-seed LoRA study: training and frozen evaluation
> measured; public experimental artifact; promotion not established.

<!-- SZL-PRESERVED-TECHNICAL-BODY:END -->

</details>

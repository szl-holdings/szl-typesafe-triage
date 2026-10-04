---
license: apache-2.0
base_model: Qwen/Qwen3.5-0.8B
base_model_relation: adapter
tags:
- peft
- safetensors
- lora
- triage
- structured-output
- refusal-preserving
- unsloth
- evaluation-harness
language:
- en
library_name: peft
pipeline_tag: text-generation
---

<p><a href="https://huggingface.co/spaces/SZLHOLDINGS/szl-command-lab"><img src="https://raw.githubusercontent.com/szl-holdings/.github/main/profile/assets/szl/logos/szl_mark_holographic.svg" alt="SZL Holdings" width="112" /></a></p>

# TypeSafe Triage · Reference LoRA Adapter

Inspect the reference LoRA adapter and retained evidence for structured JSON triage with refusal and review behavior.

**Artifact:** PEFT LoRA adapter for Qwen3.5-0.8B · **Stage:** Reference research · **HOLD** · Contamination **BLOCKED** · **NOT_PROMOTABLE**

[Explore in Command Lab](https://huggingface.co/spaces/SZLHOLDINGS/szl-command-lab) · [Build](https://github.com/szl-holdings/szl-typesafe-triage) · [Evidence](https://github.com/szl-holdings/szl-typesafe-triage/blob/e9fe792fc55892849f07b4f1bc3be651862b770e/HF_MODEL_CARD_README.md)

## Before you use it

- Contamination / corpus leakage keeps this reference run **BLOCKED / NOT_PROMOTABLE**. Do not deploy it or present it as an approved classifier.
- The retained 66-row behavioral gate is historical, bounded evidence. Its literal `PROMOTABLE` verdict does not clear the contamination finding or this release.
- The adapter configuration declares `Qwen/Qwen3.5-0.8B`; the base revision used in training has not been verified. This is a generative PEFT LoRA adapter, not a standalone model or a conventional classifier head.
- This presentation adds no training, evaluation, inference, deployment clearance or runtime qualification. Existing metrics and release limits remain as recorded below.

## Publication boundary

Before this source change, the [manual README-only workflow](https://github.com/szl-holdings/szl-typesafe-triage/blob/e9fe792fc55892849f07b4f1bc3be651862b770e/.github/workflows/publish-hf-card.yml) covered only `retrain` and `study5`. This candidate adds the fixed `root_lora` target for this card to that same serialized writer. Publication remains a separate manual action from signed current `main`, with the exact expected Hub parent and matching authenticated and public immutable README readbacks. Preparing or merging this source change does not itself publish a Hub commit.

<details>
<summary>Technical details and original evidence</summary>

The complete canonical source body follows, including the retained 66-row gate, contamination finding, declared adapter lineage and blocked-release decision.

<!-- SZL-PRESERVED-TECHNICAL-BODY:START -->

# szl-triage-qwen3.5-0.8b-lora

> **Status: NOT PROMOTABLE. Reference run only.**  
> The behavioral gate passed, but the release is blocked by a contamination / corpus-leakage finding. Metrics are reported for documentation and harness inspection only. This repository must **not** be read as deployment approval or promotion clearance.

## What this repository contains

This repository contains a generative PEFT LoRA adapter used for triage on Qwen3.5-0.8B. The inspected adapter configuration declares `Qwen/Qwen3.5-0.8B`, task `CAUSAL_LM`, and `Qwen3_5ForConditionalGeneration`; this is configuration-declared lineage, not verification of the base revision used in training. It generates JSON rather than exposing a conventional classifier head. The adapter is designed to emit strict JSON with fields such as `label`, `state`, and `evidence`, and to refuse with `state="REVIEW"` when evidence is thin, when two labels are equally supported, or when the prompt attempts to instruct the classifier instead of describing a problem.

## Publication meaning

This model is published for transparency, reproducibility, and review of the harness and governance process. Publication here does **not** mean approval for deployment, promotion, or production use.

## Release decision

**Blocked. Not promotable. Do not deploy.**

Why this release is blocked:
- Behavioral gate passed.
- Contamination / leakage review did not clear.
- Promotion status is derived from the evaluation receipt and remains blocked for this run.

## Intended use

This repository is intended for:
- Review of the triage harness
- Inspection of adapter behavior
- Reproducibility of the reference run
- Verification of refusal-preserving classifier behavior
- Documentation of a blocked release

This repository is **not** intended for:
- Production deployment
- Safety-critical or customer-facing triage
- Use as an approved or promoted classifier
- Marketing claims about general performance

## Behavior summary

The adapter is intended to:
- Return structured JSON outputs
- Prefer abstention / review when evidence is insufficient
- Preserve refusal behavior under ambiguous or adversarial prompting
- Operate as a governed classifier rather than a free-form assistant

## Training notes

- Adapter type: LoRA
- Base model family: Qwen3.5-0.8B
- Training objective: governed triage classification
- Comparison discipline: predecessor-matching hyperparameter discipline for meaningful run-to-run comparison
- Evaluation emphasis: assistant-turn loss targeting and template-family-aware split discipline

## Retained 66-row behavioral gate

At the [reviewed immutable Hub revision](https://huggingface.co/SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora/tree/24b5c44494434e88b89d9915daad32f1f8e8d03d),
the [retained gate report](https://huggingface.co/SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora/resolve/24b5c44494434e88b89d9915daad32f1f8e8d03d/gate_report.json)
records 66 rows: 66/66 exact labels, 66/66 exact states, zero malformed outputs,
23 gold-refusal rows, zero false labels on those refusal rows, and zero ungrounded
spans. Its literal `PROMOTABLE` verdict belongs to that bounded behavioral gate.
The contamination finding keeps this reference run **BLOCKED / NOT PROMOTABLE**;
the gate result is not release clearance and is not a general performance estimate.
Do not combine these rows with later five-seed or release-gate results.

The card declares Apache-2.0 in line with the canonical source repository's license.
The reviewed Hub file listing had no standalone `LICENSE` file. This documentation
review supplies no new license verification, base-revision reconstruction, model
evaluation, deployment clearance, or Hub publication.

## Evaluation interpretation

Measured results may appear in this repository for completeness. They must be interpreted under the blocked-release decision.

Interpretation rules:
1. Metrics here are documentation artifacts.
2. Metrics do not override contamination findings.
3. Public visibility does not imply approval.
4. Promotion remains blocked unless a later cleared run supersedes this one.

## Limitations

- Blocked by contamination / leakage concerns
- Promotion not established
- Not validated for deployment
- May refuse or route to review in uncertain cases by design

## Governance note

This repository is part of a governed release process in which training, measurement, publication, and promotion are separate decisions. This run was trained and measured, and the artifact may be published for inspection, but promotion was not established.

## Usage warning

Treat this adapter as a **reference artifact only**. Do not represent it as cleared, approved, deployable, or promoted.

<!-- SZL-PRESERVED-TECHNICAL-BODY:END -->

</details>

---
license: apache-2.0
base_model: Qwen/Qwen3.5-0.8B-Base
tags:
- peft
- safetensors
- lora
- triage
- classification
- refusal-preserving
- unsloth
- evaluation-harness
language:
- en
library_name: transformers
pipeline_tag: text-classification
---

# szl-triage-qwen3.5-0.8b-lora

> **Status: NOT PROMOTABLE. Reference run only.**  
> The behavioral gate passed, but the release is blocked by a contamination / corpus-leakage finding. Metrics are reported for documentation and harness inspection only. This repository must **not** be read as deployment approval or promotion clearance.

## What this repository contains

This repository contains a LoRA adapter for a governed triage classifier built on Qwen3.5-0.8B. The adapter is designed to emit strict JSON with fields such as `label`, `state`, and `evidence`, and to refuse with `state="REVIEW"` when evidence is thin, when two labels are equally supported, or when the prompt attempts to instruct the classifier instead of describing a problem.

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

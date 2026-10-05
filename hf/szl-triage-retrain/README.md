---
license: apache-2.0
language:
- en
base_model: Qwen/Qwen3.5-0.8B
tags:
- szl-holdings
- triage
- refusal-preserving
- retrain-target
- hub-job
- experimental
- research-only
- not-promotable
---

<p><a href="https://huggingface.co/spaces/SZLHOLDINGS/szl-command-lab"><img src="https://raw.githubusercontent.com/szl-holdings/.github/main/profile/assets/szl/logos/szl_mark_holographic.svg" alt="SZL Holdings" width="112" /></a></p>

# TypeSafe Triage · Refusal Retrain Scripts

Review the training and evaluation scripts prepared to investigate the triage study’s unresolved refusal gate.

**Artifact:** Training and evaluation scripts · **Stage:** Scripts only · Research · **NOT_PROMOTABLE**

[Explore in Command Lab](https://huggingface.co/spaces/SZLHOLDINGS/szl-command-lab) · [Build](https://github.com/szl-holdings/szl-typesafe-triage) · [Evidence](https://github.com/szl-holdings/szl-typesafe-triage/blob/6c3ed43318b40dda5bf814744dcffcf0b1ff8149/hf/szl-triage-retrain/README.md)

## Before you use it

- This source describes a scripts-only target, without a standalone neural checkpoint or adapter to evaluate.
- The five-seed study remains blocked at 11 of 12 gates. Promotion requires a clean evaluation and a new verified source release receipt.
- The 42 red-team probes are evaluation-only. They are excluded from training.
- Job energy is UNAVAILABLE unless measured. This presentation supplies no new training, evaluation or energy receipt.

<details>
<summary>Technical details and original evidence</summary>

The complete canonical source body follows, including the scripts’ roles, evaluation-only probes, research boundary and requirements for a future adapter.

<!-- SZL-PRESERVED-TECHNICAL-BODY:START -->

# SZL TypeSafe Triage · twelfth-gate refusal retrain (Hub-job target)

> **Status: training scripts only. No adapter has been uploaded here yet. This is not a checkpoint.**

This repository is the upload target for a Hugging Face Jobs retrain of the SZL triage LoRA.
It was created on 2026-10-01 and currently contains two Python scripts and nothing else:

| File | What it does | Runs where |
|---|---|---|
| `train_triage_refusal_seed.py` | Trains one seed of the triage LoRA on the frozen study train split plus the owner-ratified refusal augmentation (50 rows), with the published five-seed study's exact configuration (LoRA r=16, alpha=16, 3 epochs, LR 2e-4, bf16). Uploads adapter and training receipt to this repository when it completes. | Hub job |
| `eval_triage_refusal_seed.py` | Scores a retrained seed adapter against the 113 frozen held rows and the 42 verified red-team probes (the twelfth release gate) using the source repository's own scoring code. A report over zero rows is a failure, not a pass. | Hub job |

## Why this exists

The published five-seed study ([szl-triage-qwen3.5-0.8b-lora-study5](https://huggingface.co/SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora-study5)) is release-gated at **11 of 12** and recorded **NOT_PROMOTABLE**: the twelfth gate is refusal fidelity on 42 verified red-team probes. This retrain adds a ratified refusal augmentation to training and re-evaluates against that gate. The 42 probes are evaluation-only and appear nowhere in training; the corpus digest is recorded by the training script.

## Claim boundary

- Publication of scripts is not publication of a model. Until an adapter, its training receipt and an evaluation report are present in this repository, there is no artifact to evaluate.
- When an adapter does land here, it is a **research artifact**. Promotion requires a clean evaluation and a new verified release receipt in the source repository; passing a local test does not substitute for either.
- Energy for any job run is reported only if measured; otherwise UNAVAILABLE.

## Source

- Source repository and release gates: https://github.com/szl-holdings/szl-typesafe-triage
- Frozen study evidence: https://github.com/szl-holdings/szl-typesafe-triage/tree/main/evidence/five-seed-study
- License: Apache-2.0 (scripts carry SPDX headers)

<!-- SZL-PRESERVED-TECHNICAL-BODY:END -->

</details>

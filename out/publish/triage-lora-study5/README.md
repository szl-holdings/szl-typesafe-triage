---
base_model: unsloth/Qwen3.5-0.8B
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

| Target | Valid JSON | Label | State | Joint | Refusal fidelity | Evidence grounded | Failure rows |
|---|---:|---:|---:|---:|---:|---:|---:|
| base | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | N/A | 113 |
| seed-011 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 0 |
| seed-023 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 0 |
| seed-037 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 0 |
| seed-053 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 0 |
| seed-071 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 0 |

Across the five adapters, mean joint accuracy was
**100.0%**, with sample standard deviation
**0.0%**.

These results describe this frozen 113-row family holdout. They do not
establish broad generalization, calibration, or production readiness.

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

## Quick start

```python
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

repo = "SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora-study5"
base = "unsloth/Qwen3.5-0.8B"

tokenizer = AutoTokenizer.from_pretrained(repo)

model = AutoModelForCausalLM.from_pretrained(
    base,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)

model = PeftModel.from_pretrained(model, repo)
model.eval()

messages = [
    {
        "role": "user",
        "content": "Your triage input goes here."
    }
]

prompt = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
)

inputs = build_generation_inputs(tokenizer, "Your triage input goes here.", model.device)

with torch.no_grad():
    output = model.generate(
        **inputs,
        max_new_tokens=192,
        do_sample=False,
        pad_token_id=getattr(tokenizer, "tokenizer", tokenizer).eos_token_id,
    )

reply = tokenizer.decode(
    output[inputs["input_ids"].shape:],[3]
    skip_special_tokens=True,
)

print(reply)
```

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

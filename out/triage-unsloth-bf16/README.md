---
license: apache-2.0
base_model: Qwen/Qwen3.5-0.8B
library_name: peft
tags: [lora, triage, classification, refusal-preserving, unsloth]
---

# szl-triage-qwen3.5-0.8b-lora

LoRA adapter distilling a governed triage engine into Qwen3.5-0.8B. Emits strict
JSON with `label`, `state`, and `evidence`, and refuses (state `REVIEW`) when
evidence is thin, when two labels are equally supported, or when the input tries
to instruct the classifier rather than describe a problem.

## Gate receipts

Held-out split, 66 rows, greedy decode. Corpus sha256 prefix `facf4ec36d634377`.

| Metric | Measured |
|---|---|
| Malformed output | 0 / 66 |
| Label accuracy | 66 / 66 |
| State accuracy | 66 / 66 |
| Gold refusals | 23 |
| False label on refusal | 0 |
| Ungrounded evidence spans | 0 |
| Verdict | PROMOTABLE |

Evidence spans are checked verbatim against the input. A gold refusal answered
with a non-refusal label, or with malformed JSON, counts as a false label on
refusal. The gate blocks promotion unless malformed, false-label-on-refusal, and
ungrounded counts are all zero.

## Training

Unsloth 2026.9.7, bf16 LoRA (no quantization), r=16, alpha=16, dropout=0,
targets q/k/v/o/gate/up/down. 262 train rows, 3 epochs, batch 1, grad-accum 4,
lr 2e-4, seed 11, loss on assistant turns only. 198 steps in 9m20s on an
RTX 5050 Laptop (8 GB), torch 2.14.0+cu130, sm_120.

Qwen3.5 is a 3:1 hybrid stack, so real `self_attn` modules exist only on layers
3, 7, 11, 15, 19, 23. The adapter therefore holds 192 tensors: MLP on all 24
layers plus attention on those 6. Gated DeltaNet mixing layers are not adapted.

## Load

```python
from unsloth import FastLanguageModel
model, tok = FastLanguageModel.from_pretrained(
    "SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora",
    max_seq_length=2048, dtype=None, load_in_4bit=False)
FastLanguageModel.for_inference(model)
```

Verify the adapter actually bound: count `lora_B` tensors with nonzero values.
LoRA initializes `lora_B` to zeros, so 96 of 96 nonzero proves trained weights
are live rather than silently falling back to the base model.
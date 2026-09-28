## Evaluation status (updated 2026-09-28) - NOT PROMOTABLE

Adapter: `out/publish/triage-lora-study5/adapters/seed-011`. Prompt format: raw input text as the only user message, no system prompt, thinking disabled (this is how training and eval render prompts).

| Set | Rows | Result | Status |
|---|---|---|---|
| Held set (`frozen/held.jsonl`) | 113 | 113/113 (five-seed study) | Valid: 0/113 exact-text and 0/81 family overlap with `train.jsonl` |
| In-domain distill eval (v0.4.0, split != train) | 101 | 101/101 | Contaminated: 84/101 inputs appear verbatim in `train.jsonl`; 17 unseen rows 17/17 |
| Red team PARAPHRASE | 30 | 5/30 | Fails |
| Red team STEERING | 12 | 0/12 refused (12 false labels) | Fails; the gate blocks on this |

The model reads keywords: it labels when cue words are present (even when the text only instructs the classifier) and mislabels problems paraphrased without cue words. Adding a system prompt swaps failures (STEERING 10/12, PARAPHRASE 1/30, 3/42 malformed); it does not fix the model.

Pipeline defect: the five-seed training file was built from the whole distill corpus minus held rows, so it absorbed the distill eval split. The next training run must use `split == "train"` rows only.
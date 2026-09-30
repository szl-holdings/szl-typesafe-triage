---
license: apache-2.0
language: en
tags:
- text-classification
- cpu
- research
- unqualified
---

# CPU softmax diagnostic study

**NOT_PROMOTABLE.** This independently implemented, newly trained standard-library
model is an executed diagnostic baseline for six-class triage. It is not SZL-1,
a general-purpose frontier model, or the historical Qwen adapter. Its weights
are excluded from the installed `szl_triage` package and the public Docker service.
The original six qualification gates and historical seal remain unchanged.

The frozen 130,220-byte artifact uses 744 train-only TF-IDF unigram/bigram
features, six softmax outputs and seed 11. Only the 527 canonical `split=train`
rows contribute vocabulary, IDF, weights and label counts; 101 held rows do not.
Labels are engine-derived. There is no independently ratified semantic corpus or
established causal-family independence. Exact train/held and train/challenge input
overlap is zero, which does not establish independence.

The model was frozen before the runner read the 42-row challenge. That challenge
had already been exposed in earlier development and is **development evidence**.
The runner's original receipt and exact predictions are preserved in `artifacts/`.
The historical runner source records its original local paths; execute the portable
`reproduce` command below to replay this distribution.

| Observed metric | CPU model | Training-majority REVIEW control |
| --- | ---: | ---: |
| Exact label and state, all development rows | 8/42 | 12/42 |
| Lexicon-free positive accuracy | 5/30 | 0/30 |
| Steering refusal | 3/12 | 12/12 |
| Typed JSON validity | 42/42 | 42/42 |
| Literal evidence contract fidelity | 42/42 | 42/42 |
| ECE, 15 fixed bins, all rows | 0.4405903 | 0.0162646 |
| Asserted coverage | 22/42 | 0/42 |

In-lexicon accuracy is **UNAVAILABLE**, because there are no in-lexicon challenge
rows. The model fails lexicon-free accuracy, attack refusal and ECE requirements.
The majority control demonstrates why good aggregate refusal or ECE alone cannot
establish usefulness: it classifies no positive target correctly. The historical
adapter scored 5/42 on the same exposed challenge under a different runtime;
the CPU result is not a controlled reproduction of that adapter or a qualified
model improvement.

Evidence spans come from code-owned handles and exact offsets. This proves literal
occurrence, not semantic relevance. Probabilities are normalized model scores,
not a calibrated risk guarantee. The CLI returns an unqualified advisory and has
no authority to bypass deterministic policy or authorize release.

Install the repository's software package, then run from its root:

```powershell
python -m pip install -e .
python -m experiments.cpu_softmax.predict --text "The export closes without saving."
python -m experiments.cpu_softmax.reproduce --output-dir ../cpu-study-replay-new
python -m pytest tests/test_cpu_softmax_study.py -ra
```

The replay destination must be new. Replay checks the canonical dataset bytes,
reproduces the model exactly, then reproduces all predictions and qualification
results. It does not overwrite the frozen receipt. Inference validates source,
model, receipt, thresholds and study-file hashes against `STUDY_MANIFEST.json`.
These hashes identify bytes; trust in the manifest comes from the canonical signed
Git source, not from a self-asserted hash. The original receipt's historical source
hashes differ for the relocated CLI/replay and early input-bound validation; the
manifest explicitly binds the current distribution and preserved historical source.

`NEXT_PROGRAM.json` freezes the next research program before new audit data or GPU
training: original family-split data, independent label ratification, positive
controls, authority contrasts, fixed seeds/budgets and separate calibration/audit.
No external paper's weights or code are copied. No paid GPU job or publication is
launched by this study.

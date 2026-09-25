# Replayable study evidence and bounded text inference

The saved five-seed experiment already exists. This upgrade checks what those
files actually support and runs a new, small inference check without replacing
the historical study. It does not promote an adapter or publish to a registry.

## Why the handoff needed more than a tokenizer patch

The downloaded handoff stopped at `HELPER =`. Its longer pasted replacement
guessed command-line flags from help text and collected unrelated receipt files.
The repository's old entry point had no argument parser: even `--help` could
start preflight, training, evaluation, and publication. Its resume check accepted
an evaluation based on the number of held rows and one split hash, without
binding the evaluator, prompt template, or adapter bytes.

The default command now replays the declared evidence directory offline.
`--help` is inert. Importing the pipeline creates no study directories. Remote
publication and training are absent from the new command dispatch. The existing
training and publication helpers remain available as historical implementation
code; they are not an audited replacement for a future publication workflow.

## Replay the recorded experiment

From the repository root, with Python 3.10 or newer:

```powershell
python scripts/codex_finish.py audit
python scripts/train_eval_publish.py --help
```

The audit checks the exact five seeds and base model, frozen split, raw
prediction coverage, reconstructed scores, failure records, aggregate summaries,
training receipts, and adapter index. It hashes the inputs it examines. Supply
the original run checkout to additionally verify the saved adapter bytes:

```powershell
python scripts/codex_finish.py audit --artifact-root C:\Users\steph\szl-typesafe-triage --output audit-new.json
```

An output path must be new. Reports are never overwritten. No model library,
CUDA, credentials, or network is needed for the replay. A failed integrity check
returns exit code 2 and names the inconsistency. A successful replay means the
saved records agree; it does not authenticate their author or prove that an
unrecorded historical generation occurred.

## Run a new GPU smoke check

Use the existing training environment, which already contains the model stack:

```powershell
C:\Users\steph\szl-typesafe-triage\.venv\Scripts\python.exe scripts/codex_finish.py smoke --artifact-root C:\Users\steph\szl-typesafe-triage --seed 11 --limit 3 --output smoke-new.json
```

The command uses the cached model offline, verifies the CUDA architecture,
selects at most five historical examples, and includes a refusal row where the
requested limit permits. Greedy decoding is bounded at 192 new tokens per row.
It reads the original adapters and writes one new receipt. It checks the study
fingerprint and adapter/configuration hashes before and after inference.

Add `--eager` to disable Unsloth and PyTorch model compilation for a functional
smoke on a machine where initial kernel preparation is expensive. The receipt
records the requested mode and relevant environment settings. This mode does
not establish compiled inference performance. The adapter is selected from the
audited index, including when it uses a different local directory layout.

The receipt includes the actual outputs, source file hashes, observed base
revision where available, adapter digest, tokenizer-template digest, rendering
mode, decoding settings, and runtime versions. `state: EXECUTED` establishes
that the bounded inference ran; `all_joint_exact` separately reports agreement
with those examples. This is not a new five-seed evaluation.

Rendering, encoding, special token lookup, and decoding use the same resolved
text tokenizer. The media processor is never the text encoding fallback.
Templates receive `enable_thinking=False`; a template failure cannot silently
retry with a different mode. Encoding uses `text=` and
`add_special_tokens=False`. These choices follow the distinction between text
and multimodal generation in the
[Transformers Qwen3.5 documentation](https://huggingface.co/docs/transformers/main/model_doc/qwen3_5)
and the [chat templating guide](https://huggingface.co/docs/transformers/main/chat_templating).

## What the result does and does not establish

The existing training receipts record `REFUSED` contamination. The existing
release receipt reports `BLOCKED`. Passing integrity checks cannot override
either result. The audit never changes eligibility into an actual promotion.
The historical phrase “11/12” is not reconstructed into a new gate count; the
current gate object is reported as supplied.

The saved v1 evaluations did not seal the evaluator, base revision, and prompt
template together. Replaying their raw records preserves that limitation.
Template-family separation and five training seeds do not demonstrate
performance on independent human-authored bug reports or unseen attacks.

The next research step is a separately frozen, independently labelled set of
real error families, paraphrases, and refusal challenges, evaluated against the
base model, adapters, and deterministic engine. Define its labels and promotion
criteria before collecting scores. It must have a new experiment identity;
changing the historical dataset or relabelling the existing scores cannot supply
that evidence.

## Publication review

```powershell
python scripts/codex_finish.py publish-plan --artifact-root C:\Users\steph\szl-typesafe-triage
```

This recomputes the audit and produces a read-only plan with no external writes.
There is no `--execute` switch. Review code and new evidence in a pull request;
any future registry publication must define exact destinations, expected remote
revisions, content hashes, and post-write verification. Existing organization
profiles, social accounts, weights, and tags are not part of this upgrade's
publication scope.

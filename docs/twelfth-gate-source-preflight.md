# Twelfth-gate source preflight

The source check verifies the frozen 515/113 split, the 50 ratified augmentation
rows, the unchanged 42-row evaluation-only challenge, generated trainer contracts
and local runner boundaries. The 12 steering refusals are verdict-gated; the 30
paraphrase rows are reported. Exact input overlap checks do not prove semantic
independence. The public self-authored challenge is not a blind benchmark.

From this source checkout, with an existing Python interpreter:

```powershell
powershell.exe -NoProfile -File scripts/run_twelfth_gate_v110.ps1 -Python <python.exe> -NoPublish -PreflightOnly -SkipGpu
```

This exits before model imports, downloads, inference or training. Its
`PREFLIGHT_OK` receipt reports GPU checks as skipped and provider source approval
as unqualified. It supplies no model quality, training or promotion evidence.

## Execution prerequisites

Execution remains HOLD. The proposed source needs independent review and protected
source admission. The bridge draft must then be rebound to that admitted signed
revision and its exact blobs. The existing owner process must authorize the data
and supply a fresh envelope before expiry; no new signing authority is created by
this repair. The draft's original expiry is 2026-10-09T00:00:00Z.

Production preflight additionally requires exact provider package versions and
independently reviewed provider distribution source digests. The version boundary
comes from `evidence/five-seed-study/environment-receipt.json`: Unsloth 2026.9.10
and unsloth_zoo 2026.9.7. `APPROVED_PROVIDER_DISTRIBUTION_SHA256` is deliberately
empty. Observing an installed digest is not admission; the production loader fails
before importing the model stack until that boundary is reviewed and approved.

The installed `unsloth/models/loader.py` was inspected as text only. Its observed
SHA-256 was `829d7cf1464d8adea26a16cb7d0bfbfb0e3ffc54cd5c86bbe724dc93fc90001e`.
`_revision_for_resolved_repo` can discard a revision after remapping, and the PEFT
branches set `model_revision = base_revision if not is_peft else None`. This file
observation is not an approved provider distribution digest or a runtime test.

The proposed trainer, smoke and evaluators load the official base at
`Qwen/Qwen3.5-0.8B@2fc06364715b967f1860aea9cf38778875588b17`, require exact model
name resolution and existing local model files, and verify the returned model
identity. Evaluation attaches each bound local PEFT adapter only after loading
that base. Tokenizers also load from the bound local adapter files.

Reused training, held and challenge receipts must match the current source,
trainer, seed, frozen/ratified inputs, model revision, adapter weights/config and
tokenizer hashes. Held/challenge execution checks inputs before and after the run.
The prepared training collator must mask user tokens and retain assistant labels
for all 565 prepared rows before `train()` can run or an adapter can be saved.
The trainer receives the resolved text tokenizer. Held and challenge reuse also
replays raw outputs against the frozen targets and authoritative challenge rows,
requires exact row coverage, and compares stored flags, summaries and failure sets.

The Windows supervisor checks bounded telemetry for the selected physical GPU
before launch and throughout execution, enforces the remaining 180-minute budget
and the 78 C threshold, and places a suspended child in a kill-on-close Windows
Job Object before resuming it. Descendants remain guarded after their parent
exits; termination requires the job's active-process count to reach zero.
CPU/native Windows tests exercise this boundary. Actual GPU telemetry and the
production model environment still require qualification under the owner envelope.
The deadline begins before initial telemetry, each telemetry timeout is bounded
by the remaining budget, and supervisor exits 96-99 stop the wrapper centrally
before stale-artifact handling or another launch.

## Focused offline verification

Run these sequentially with `PYTHONPATH=src;scripts` on Windows:

```powershell
New-Item -ItemType Directory -Force out | Out-Null
python -m pytest tests/test_twelfth_gate_preflight.py tests/test_study_process_guard.py tests/test_challenge_eval.py tests/test_study_evidence.py -q --basetemp out/twelfth-gate-test-tmp
```

The new tests cover actual check-train/check-held/check-challenge entrypoints,
challenge mutation failure, missing/wrong/remapped loader identities, explicit
base-before-adapter loading, a fresh-process model-import denial, corpus-dependent
trainer digests, actual generated masking/train/save failure paths, telemetry
timeouts, injected guard exits at both reuse entrypoints, forged raw/summary replay
and a native CPU descendant termination after its parent exits. Any
mock outputs remain test fixtures and supply no study scores.

Publication is disabled in the twelfth-gate runner. PR #44's existing HOLD and
all dataset restrictions remain in force.

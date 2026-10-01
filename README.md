# szl-typesafe-triage

[![PyPI](https://img.shields.io/pypi/v/szl-triage)](https://pypi.org/project/szl-triage/) [![Python](https://img.shields.io/pypi/pyversions/szl-triage)](https://pypi.org/project/szl-triage/) [![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/szl-holdings/szl-typesafe-triage/badge)](https://scorecard.dev/viewer/?uri=github.com/szl-holdings/szl-typesafe-triage)

A deterministic, receipt-bearing triage engine, and an honest account of what it cannot do.

**Read this first.** The engine does not yet perform triage by meaning; it matches vocabulary. The useful content
of this repository is the measurement discipline: 16 retractions recorded in an
append-only ledger, a phrasing guard that mirrors the estate's CI rule, and a leakage gate that refuses rather than
advises. Release is **BLOCKED at 11/12**.

## Measured, not asserted

| Property | Value | Receipt |
|---|---|---|
| Canonical gate axes vs engine axes | 13 vs 4 | `out/yuyay_gate_conformance.json` |
| Compensation errors on the labelled eval split | 35 | `out/yuyay_gate_conformance.json` |
| Ratified rows / effective n | None / None | `out/effective_n.json` |
| Corpus leakage verdict | REFUSED | `out/leakage_gate.json` |
| Retractions, of which self-corrections | 16 | `out/retractions.json` |

## What is not claimed

- No winner, no baseline beaten, no comparison against any other system.
- No kernel verification is performed here; Lean symbols are bound by name only (`out/lean_binding.json`).
- Lambda is cited as Conjecture 1 and disproved as stated; conditional Theorem U is the proved result.
- No locked-formula count is asserted; the estate's own sources disagree (`out/phrasing_guard.json`).
- SLSA L1 honest, L2 roadmap. Not L2-verified, not L3, and no federal or hardened-image accreditation.

## Audits in this repository

- `docs/ESTATE_AUDIT.md` - ten passes over 88 public estate repositories
- `docs/PRIVATE_AUDIT.md` - private-tier leads via authenticated code search
- `docs/DEEP_FINDINGS.md` - why the predecessor adapter is NOT PROMOTABLE
- `docs/STATE_OF_THE_REPO.md` - eight bandaids and six gaps, named
- `docs/DATASET_CARD.md` - contamination field filled, per the org template

Apache-2.0. Copyright 2026 SZL Holdings.

## Use the local runtime

`szl-triage serve --port 8765` starts a loopback console and JSON API around the
deterministic pipeline. The installed package carries its default policy, so
the CLI works outside this checkout. Decisions include verifiable payload,
policy, and implementation hashes. See [local runtime](docs/LOCAL_RUNTIME.md)
for installation, API requests, and the separate fresh GPU challenge command.
The model-release block above remains in force.

## Deploy the public deterministic software lab

The Docker Space entry point is `python -m szl_triage.public_server`, explicitly
bound to `0.0.0.0:7860`. It uses only the standard-library deterministic pipeline.
`/readyz` and `/v1/decide` identify the runtime as `DETERMINISTIC_SOFTWARE_LAB`,
report `model_loaded: false`, and retain model promotion as `HOLD`. Publishing
this software lab does not qualify or publish a language model.

Before startup, the publisher must create `SOURCE_BINDING.json` from the immutable
canonical GitHub commit. Its exact fields are `schema` (`szl.triage-source-binding/v1`),
`github_repository` (`szl-holdings/szl-typesafe-triage`), `github_commit` (the full
40-character commit SHA), and `source_files` (relative paths mapped to SHA-256
digests). The file set must contain every deployed `src/szl_triage/**/*.py` file
and `src/szl_triage/data/triage_policy.v3.json`, with no extra declarations.
Startup rejects absent, changed, omitted, extra, or symlinked source files before
binding. Readiness reports the declared GitHub commit and verified manifest digest;
these unsigned digests bind contents and do not authenticate the publisher.

`TRIAGE_TRUSTED_AUTHORITIES` is a required comma-separated list of exact lowercase
DNS authorities. The Docker image explicitly configures
`szlholdings-szl-typesafe-triage.hf.space`. A domain proxy must preserve one configured
authority or add its exact authority to this setting. Host wildcards and forwarded
host trust are unavailable. An Origin, when supplied, must be HTTPS with the same
authority as the request Host. Duplicate headers and cross-origin requests are
rejected. TLS terminates at the managed hosting proxy.

`TRIAGE_ALLOW_LOOPBACK_PROBES=1` explicitly permits only local-peer probes with
`localhost:7860` or `127.0.0.1:7860`. Its default is `0`; the Docker image enables it
for managed container health checks. Framing is disabled by default. The image
explicitly sets `TRIAGE_FRAME_ANCESTOR=https://huggingface.co` to permit the managed
Hugging Face page to embed the lab while retaining nonce-based scripts and styles.
No other frame ancestor or wildcard is accepted. The image copies only Python
package source, the default policy, and the source binding; weights, training
outputs, and credentials are outside its copy set.

## Replay the five-seed study

`python scripts/codex_finish.py audit` checks the saved study offline, including
raw predictions, recomputed metrics, split hashes, and the exact five seeds.
It reports integrity separately from promotion. A bounded GPU smoke test can
write a new receipt without replacing the historical results. See
[study replay and inference](docs/STUDY_REPLAY.md) for commands and limitations.

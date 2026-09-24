# szl-typesafe-triage

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

## Replay the five-seed study

`python scripts/codex_finish.py audit` checks the saved study offline, including
raw predictions, recomputed metrics, split hashes, and the exact five seeds.
It reports integrity separately from promotion. A bounded GPU smoke test can
write a new receipt without replacing the historical results. See
[study replay and inference](docs/STUDY_REPLAY.md) for commands and limitations.

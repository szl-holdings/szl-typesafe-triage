# szl-typesafe-triage domain leader study r1 (propose-only)

Date: 2026-11-24. Method: web-verified leader landscape + governing-seat ratification (Kimi nonce T7-RULING-20261124-K1). Study pinned to szl-typesafe-triage HEAD 8d8f0d7d99951b772ceeeec1a9b75c3fcf558954, fetched 2026-11-24. This card is documentation only; it changes no code, CI, config, or existing PR status. All absorb actions are FUTURE PROPOSALS (non-authorizing); implementation and merges remain separately reviewed and gated. L Conjecture 1: OPEN (advisory, never a closed theorem). No speedup, energy, or proven-trust claims; upstream performance claims are labeled as upstream claims only.

## Domain: Deterministic, receipt-bearing typed triage with versioned JSON policies, fixture-gated CI, and fail-closed routing of unknown inputs to REVIEW.

## Leaders studied (web-verified 2026-11-24)
1. Cedar (https://github.com/cedar-policy/cedar) - moat: Cedar combines a schema-validated authorization policy language with formal analysis and differential testing of its implementation.
2. Open Policy Agent (https://github.com/open-policy-agent/opa) - moat: OPA provides a mature general-purpose policy engine with broad ecosystem adoption and decision-logging support.
3. CUE (https://cuelang.org) - moat: CUE unifies data, schemas, and constraints to support strongly typed configuration validation.

## Absorb actions (FUTURE PROPOSALS, non-authorizing)
1. (Cedar) Propose a future design note comparing the triage pack's typed JSON policies to Cedar's schema-validated policy language. Cost: doc-only, ~1 day; limit: note only, no code.
2. (Open Policy Agent) Propose a documentation-only review of OPA decision-log patterns vs the pack's hash-chained receipts. Cost: doc-only, ~1 day; limit: note only.
3. (CUE) Propose a future note on schema-typed policy authoring tradeoffs for versioned JSON policies. Cost: doc-only, ~half day; limit: note only.
4. (Baseline) Propose that any future comparison preserve deterministic evaluation, fail-closed unknown-to-REVIEW routing, fixture-gated CI, and append-only hash-chained receipts with the UNSIGNED_HONEST fallback. Cost: doc-only, ~half day; limit: preservation criteria only, no code.

## Do not do (per governing seat)

Do not merge, bypass the signature wall, or claim implementation beyond this card.

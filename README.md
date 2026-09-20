# szl-typesafe-triage

Deterministic, receipt-bearing typed triage engine from SZL Holdings.

Text in; typed judgment, confidence, rationale, and hash-chained receipt out.
The standard-library core fails closed: low-confidence or adversarial input
becomes REVIEW, never a lucky guess.

## Verify

    python -m unittest discover -s tests -v
    python scripts/export_sft_dataset.py --check
    python scripts/export_sft_dataset.py

The exporter emits JSONL chat pairs plus a receipt chain for a Qwen QLoRA bake
through szl-forge. Publish a model only with a source commit SHA,
base-vs-finetuned evaluation, model card, and receipt chain.

## Layout

- triage/engine.py - typed label, confidence, rationale, injection defense
- triage/receipts.py - offline-verifiable SHA-256 receipt chain
- policies/ - versioned inspectable triage policy
- fixtures/golden/ - golden and adversarial regression cases
- scripts/export_sft_dataset.py - fail-closed fixture gate and SFT exporter
- .github/workflows/ci.yml - public CI proof

## License and citation

Apache-2.0. Copyright 2026 SZL Holdings. See LICENSE, NOTICE, and CITATION.cff.
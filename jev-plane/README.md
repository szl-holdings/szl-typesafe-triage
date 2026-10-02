# szl-jev-plane

Estate judgment plane. Jev judges; code composes.
Lambda is Conjecture 1. Locked-proven is 8. Jev does not ALLOW-alone.

A missing, NaN, infinite or out-of-range answer is UNAVAILABLE: it yields no label, sets
`reader_status` to `DEGRADED` or `UNAVAILABLE`, and sets `request_info`. The router abstains.
Packs and the client pin `jev-1.13.0`; a `-latest` model id is refused.

```bash
python -m pytest jev-plane/plane -ra
```

## Optional overclaim reader

The existing `szl.overclaim_reader.v1` pack is composed locally, with the code-owned
0.65 risk threshold and 0.55 confidence floor. Missing, malformed or out-of-range
answers withhold a clean label; a present BLOCK risk is retained even when a sibling
answer is unavailable. This is an advisory text classifier, not a release authority.

```bash
python jev-plane/plane/finish.py --selftest
python jev-plane/plane/finish.py --intent "Record checks as MEASURED, not LIVE"
python jev-plane/plane/finish.py --intent "Stamp a-11-oy.com LIVE"
```

Default execution and self-tests make no external call, even when the operator host
has a key. `--live` explicitly sends the intent to the fixed TypeSafe endpoint using
the operator's `TYPESAFE_API_KEY`; this can incur API cost. Deterministic BLOCK and
UNAVAILABLE local gates skip the reader. The exact `jev-1.13.0` request and response
pin is required. Redirects, proxy forwarding, malformed responses and mismatched
model identities are refused. Missing access stays UNAVAILABLE, not PASS.

`allowed` is always false. `evidence_clear` means only that both bounded classifiers
returned MEASURED; it proves neither that evidence is authentic nor that a runtime is
ready. No reader result can merge, publish, write to the Hub, sign a receipt, qualify a
model or change a domain. Local regular expressions cover known spellings, not all
semantic paraphrases. API calibration, deterministic provider behavior, mathematical
claims and production readiness are not established here. Historical PR numbers in
supplied payloads must be refreshed separately, never replayed as write instructions.

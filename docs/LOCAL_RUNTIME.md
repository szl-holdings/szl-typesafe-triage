# Run the local triage service

The installed package includes its default policy. Both commands work outside
the repository and need only Python 3.10 or newer; the deterministic runtime
does not import a model framework or download weights.

```powershell
python -m pip install --no-deps ./szl_triage-0.4.0-py3-none-any.whl
szl-triage decide "charged twice on invoice INV-2041, want a refund"
szl-triage serve --port 8765
```

Open `http://127.0.0.1:8765/` for the local console. The server binds only to
loopback. It is a local research tool, without remote authentication, TLS,
durable storage, automatic start at login, or a public-service deployment.
Keep the process running while using it; Ctrl+C stops a foreground instance.

The API provides process health at `/healthz`, policy and implementation
identity at `/readyz`, and decisions at `POST /v1/decide`:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/v1/decide -Method Post `
  -ContentType 'application/json' `
  -Body '{"text":"charged twice on invoice INV-2041, want a refund"}'
```

The active policy is frozen for the process. `--policy PATH` explicitly selects
another policy; an invalid or missing file stops startup. Request bodies contain
exactly one `text` string. Body sizes, read time, concurrent requests, host and
browser origin are bounded. The service does not record input text to disk.

Every response binds the typed decision to exact policy and implementation
digests. `szl_triage.server.verify_envelope(response)` verifies the payload
hashes. Those hashes detect changes; they are not signatures or proof that a
trusted operator produced the result. Responses are stateless, not a durable
audit ledger.

The engine matches vocabulary and can abstain. `MEASURED` is the existing
pipeline state, not a calibrated semantic confidence score. An operational
HTTP service does not establish model quality. Model promotion remains blocked
by the retained release evidence; the local service does not load the adapter.

## Fresh adapter challenge

Use an existing GPU environment and cached base model to re-evaluate the saved
adapter on the complete existing red-team corpus:

```powershell
python scripts/challenge_eval.py --artifact-root C:\path\to\saved\runs `
  --evidence evidence/five-seed-study `
  --seed 11 --eager --output C:\new-receipts\challenge.json
```

The output path must be new. This writes a separate receipt and never modifies
the historical study or release evidence. The receipt records predictions,
refusal errors, evidence grounding, input overlap, corpus/adapter/code/template
digests, runtime versions, and observed base revision. The corpus is a known
development challenge: its existing ratification label is recorded as a source
claim, not independently authenticated. This is neither a blind benchmark nor
a replacement for leakage qualification, a five-seed evaluation, or promotion.

# Canonical card-only publication

GitHub is source of truth. The existing publish-hf-card workflow is the one
serialized manual card writer, restricted to canonical main. Its fixed targets:

| Target | Source Git blob path | Existing HF model repository |
|---|---|---|
| retrain | hf/szl-triage-retrain/README.md | SZLHOLDINGS/szl-triage-retrain |
| study5 | out/publish/triage-lora-study5/README.md | SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora-study5 |
| root_lora | HF_MODEL_CARD_README.md | SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora |

The root LoRA is the separately documented reference adapter. Its retained
66-row behavioral gate does not override the contamination finding or the
BLOCKED / NOT_PROMOTABLE release decision. The writer requires that card's own
blocked-release, contamination and bounded-gate language; study5's 11/12 result
and the retrain scripts-only boundary cannot substitute for it. This target
adds only the existing source README to this manual card lane. The
`scripts/train_lora.py` refusal to overwrite the live artifact is unchanged;
no weights, training receipts or other repository files may change here.

Supply the independently refreshed full HF parent commit. The workflow defaults
to a dry plan; publish=true is an explicit card publication. Missing authority or
failed checks fail the run rather than becoming a successful skip.

Every plan, diagnostic or publication also requires caller-supplied
`expected_source_commit` and `expected_card_sha256`: the full lowercase source
commit reviewed for this action and the SHA-256 of its exact canonical card
bytes. These values are not derived from the executing main. The workflow
rejects a missing/malformed source pin or any difference from `GITHUB_SHA`
before checkout and provider work. The helper retains both caller pins in its
receipt/journal, validates source equality and card parity before provider
access, and checks the pins again after durable intent, immediately before the
README commit. A newer main does not refresh the reviewed source automatically.
After admitting a publisher change, review its new signed source SHA before
requesting publication; a reviewed older source SHA must fail against newer main.

The existing required `expected_parent` input is already the caller-reviewed
target revision. It is checked against the Hub head before metadata/readback,
rechecked after durable intent, and passed unchanged as `parent_commit` to the
README-only commit. No target revision is selected or refreshed on drift. A
known final guard failure records zero request attempts/writes; an error after
the commit request retains the existing outcome-unknown/known-commit semantics.

The helper reads one regular immutable Git blob. It verifies that the source SHA
is current canonical main and GitHub reports that same commit's signature as
verified/valid. This is provider-attested current-commit verification, not
independent signer ownership or validation of ancestry. No trust store changes.
Local dry plans need no manufactured Actions environment and do not contact HF:

    python scripts/publish_hf_card.py --target study5 --source-commit FULL_GITHUB_SHA --expected-source-commit REVIEWED_GITHUB_SHA --expected-card-sha256 REVIEWED_CARD_SHA256 --expected-parent REVIEWED_HF_SHA --receipt NEW_RECEIPT.json

Publication additionally requires canonical GitHub Actions repository, main ref,
manual-dispatch event and exact dispatch SHA, plus explicit HF_TOKEN. The
Actions environment checks are operational guards, not cryptographic host or
actor attestation; do not manufacture those variables for a local publication.
The workflow uses HF_ORG_TOKEN or HF_TOKEN; never paste credentials into arguments,
cards, logs or receipts. GITHUB_TOKEN contacts only fixed-host read-only
commit-signature metadata. Membership alone is not write authority; the provider
must authorize the normal operation.

The writer captures source bytes before HF access, verifies the parent and its
complete blob/size/LFS metadata, then rechecks canonical source before mutation.
It submits exactly one README operation with expected-parent CAS. Every other
file identity must remain unchanged at the returned immutable commit. Both
authenticated and separate token=False public README readbacks must equal the
captured bytes. Git blob preflight and custom card/signature reads have explicit
size caps and timeouts; raw HTTP uses same-origin HTTPS without a provider cache.
SDK metadata has a timeout and a post-read 10,000-sibling cap, but is fully
buffered by the pinned SDK and has no strict response-byte budget. This is not a
hostile-input sandbox.
An identical card is verified as a no-op with zero writes and no changed paths.

The single-JSON receipt and its `.journal.jsonl` sidecar are both exclusive files.
The sidecar is append-only, with flush/fsync checkpoints for the source plan,
pre-request outcome-unknown intent, returned commit before verification, and
final status (or no-op). Failed checkpoints prevent a new provider mutation;
post-commit journal failures exit nonzero and preserve the known commit in the
snapshot where possible. The workflow retains both files even on failure.
Failures retain phase, known provider commit and
prior state without raw exceptions or credentials. A timeout after a commit
request is OUTCOME_UNKNOWN, never claimed to have made zero mutations. Failed
readback never automatically rolls back, retries against a changed parent or
claims an upload is verified. Refresh source/parent and inspect the receipt.
The pre-request journal is durable intent, not proof the provider received it.
A crash between provider mutation and recording its returned commit can still
leave outcome unknown; the snapshot can remain empty during a process crash.
There is no atomic transaction spanning GitHub, HF and local storage. Canonical
owner merge remains a separate gate before dispatch; dispatch variables do not
attest host or actor identity, and the provider must authorize the write.

This lane never creates repositories, changes privacy, deletes files, uploads
folders/weights, trains, runs inference or changes qualification. Study5 remains
BLOCKED 11/12 and NOT_PROMOTABLE. Card verification is not model evaluation,
deployment, host registration or runtime proof; runtime remains NOT_EVALUATED.
Do not reintroduce the withdrawn study5 inline inference example.

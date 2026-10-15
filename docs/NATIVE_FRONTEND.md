# TypeSafe Triage native interface

The local service and public deterministic lab share `src/szl_triage/presentation.py`.
Their servers select local or public copy explicitly. The public lab retains
`HOLD`, `model_loaded: false`, and its unsigned declared-source binding. The local
service identifies its startup package and policy without claiming a published
GitHub source. Decision, policy, authority, release, Host/Origin, and nonce-CSP
checks remain owned by the existing server and pipeline modules.

## Native source and delivery

`native_assets.py` contains exact UTF-8 constants projected from admitted brand
Git blobs. The Orbit 32 cut is rendered at 40px with 10px of clear space. No mark
geometry, colors, or metadata are redrawn. Canonical tokens supply both themes;
component CSS is local. The embedded upstream SOURCE manifest is unchanged and
describes its full upstream bundle. `native-frontend-projection.json` separately
records only the three constants actually installed here. It is unsigned
provenance metadata, not a cryptographic product receipt.

| Constant | Accepted brand source |
|---|---|
| `TOKEN_CSS` | `4309f6fce89179331b0b3ed8c99494e76c5be256:kanchay/szl-tokens.css` |
| `SOURCE_MANIFEST` | `4309f6fce89179331b0b3ed8c99494e76c5be256:kanchay/SOURCE.json` |
| `ORBIT_SVG` | `fd62fe5856ed8e5f660eaae5a9c52957cd71b0a7:kit/logos/orbit-v2/suite/szl-icon-32.svg` |

The token source qualified by the upstream manifest is
`27d12e77fc0f9f1a0e5fae8b34adf2380d51d070`. Art attribution is SZL Holdings /
Stephen Lutar, ORCID 0009-0001-0110-4173, CC BY 4.0; interface code is Apache-2.0.

To regenerate from an existing local canonical brand checkout, or check its
immutable source parity:

```sh
python scripts/project_native_frontend.py --brand-checkout /path/to/szl-brand
python scripts/project_native_frontend.py --brand-checkout /path/to/szl-brand --check
```

The command reads only the three fixed Git blobs and checks their admitted
SHA-256 values before writing. It neither contacts a provider nor publishes.
The existing Python package, wheel, Docker root `*.py` copy, canonical software
export, and independently verified exact source set already cover both new
Python modules. No asset path, CSP origin, publisher target, or credential is
added. The Space card writer changes only its outer native icon projection;
generated metadata, retained technical text, and source evidence limits remain.

## Visitor behavior

The interface has in-memory light/dark appearance, a skip link, 44px controls,
native keyboard behavior, no remote fonts or runtime art fetches, explicit
research boundaries, and useful no-JavaScript source links. The dark explanatory
card is an opaque nested surface in either theme. Its four steps describe the
configured deterministic path; they are not asserted as a live trace.

Opening the page sends only the existing read-only identity request. Examples
are loaded locally; the decision endpoint is called only after an explicit Run
triage action. While that request is pending the input and example controls are
disabled so the displayed response belongs to the submitted text. Responses have
an eight-second client timeout and a 256KiB streaming limit. Unreadable, rejected,
or unsupported responses stay explicit. A zero returned aggregate is displayed
as zero. Rationale, evidence, labels, and full JSON use text nodes; no returned
field becomes HTML. The interface does not verify cryptographic authenticity or
recompute decision mathematics.

## Qualification and publication boundary

The existing server, source-binding, and software publisher tests remain in the
full CI suite. Native tests verify exact constant hashes, nonce-only inline
resources, parser structure, and export inclusion/tamper rejection using clearly
synthetic Git authorization fixtures. These fixtures do not bypass or qualify
the production canonical-main/signature requirements.

`scripts/qualify_native_frontend.cjs` runs the actual local/public servers with
synthetic report inputs. The public startup binding is generated solely for the
local fixture. Dirty-source fixtures use an all-zero synthetic revision; clean
fixtures bind their actual checkout revision. Neither is a provider publisher
attestation. The browser is restricted to those two loopback origins. Recovery
responses are explicitly intercepted fixtures; real successful decisions run
only the local deterministic engine. No provider, model, training, release,
publication, or governed action is invoked.

The new contents-read browser job checks the exact PR head. It covers 320–2560px,
both themes, refusal results, zero, unsupported/malformed/oversized/timed-out
responses, absent source identity, hostile text, keyboard, no JavaScript, print,
forced colors, and reduced motion. Color checks use the actual computed roles
and the bounded source-owned atmospheric background. Rendered fixtures are
neither a comprehensive WCAG certification nor live performance/readiness proof.
Artifacts are unsigned observations.

```sh
# Requires an existing Playwright installation and its Chromium executable.
NODE_PATH=/path/to/node_modules TRIAGE_BROWSER=/path/to/chromium \
  TRIAGE_QA_OUT=/path/to/observations node scripts/qualify_native_frontend.cjs
```

Merging this frontend does not publish the public Space or promote a model.
`scripts/publish_software_space.py` still requires a full current canonical main
commit, its normal signature verification, immutable Git blobs, an explicit
publish operation, and provider authorization. Release and model-card publishers
remain separate owners. The blocked model release PR and its gates are unchanged.

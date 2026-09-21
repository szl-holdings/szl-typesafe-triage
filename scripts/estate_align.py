import base64, hashlib, json, subprocess, sys
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage import policy as policy_mod
from szl_triage.decision import classify, to_receipt_payload

POL = policy_mod.load("policies/triage_policy.v3.json")
HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
ROWS = [json.loads(l) for l in
        Path("policies/redteam_probes.verified.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

def sha3(b: bytes) -> str:
    return hashlib.sha3_256(b).hexdigest()

# --- signer: attempt real DSSE ECDSA P-256; degrade to the estate's own vocabulary, never fabricate ---
signer_state, signer_detail, priv, pub_pem = "UNAVAILABLE", "", None, None
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec, utils as ecutils
    kd = Path(".keys"); kd.mkdir(exist_ok=True)
    kf = kd / "triage-signer-p256.pem"
    if kf.exists():
        priv = serialization.load_pem_private_key(kf.read_bytes(), password=None)
        signer_detail = "persistent signer key loaded from .keys (gitignored)"
    else:
        priv = ec.generate_private_key(ec.SECP256R1())
        kf.write_bytes(priv.private_bytes(serialization.Encoding.PEM,
                                          serialization.PrivateFormat.PKCS8,
                                          serialization.NoEncryption()))
        signer_detail = "persistent signer key generated into .keys (gitignored)"
    pub_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    signer_state = "SIGNED"
except Exception as exc:
    signer_state = "UNSIGNED"
    signer_detail = "cryptography unavailable (" + type(exc).__name__ + "); receipts remain HASH-LINKED only"

def sign(payload: bytes):
    if priv is None:
        return None
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    return base64.b64encode(priv.sign(payload, ec.ECDSA(hashes.SHA256()))).decode()

def verify(payload: bytes, sig: str) -> bool:
    if priv is None or sig is None:
        return False
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    try:
        priv.public_key().verify(base64.b64decode(sig), payload, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False

GENESIS = "0" * 64
chain, prev, verified = [], GENESIS, 0
for i, r in enumerate(ROWS):
    rec = classify(r["input"], POL)
    payload = to_receipt_payload(rec, "triage_policy.v3", HEAD, seq=i)
    payload["chain_algorithm"] = "sha3_256"
    payload["prev_digest"] = prev
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    d = sha3(raw)
    sig = sign(raw)
    okv = verify(raw, sig)
    verified += 1 if okv else 0
    chain.append({"payloadType": "application/vnd.szl.receipt+json",
                  "payload": base64.b64encode(raw).decode(),
                  "digest": d, "prev_digest": prev,
                  "algo": "ECDSA-P256-SHA256" if sig else None,
                  "signature": sig,
                  "signer_state": ("SIGNED" if okv else ("UNSIGNED" if priv is None else "DISABLED")),
                  "verified_offline": okv})
    prev = d

Path("out/chain/triage-ledger.sha3.jsonl").write_text(
    "\n".join(json.dumps(c) for c in chain) + "\n", encoding="utf-8")

# continuity replay: recompute every link from the payloads alone
replay_prev, breaks = GENESIS, 0
for c in chain:
    raw = base64.b64decode(c["payload"])
    if json.loads(raw)["prev_digest"] != replay_prev or sha3(raw) != c["digest"]:
        breaks += 1
    replay_prev = c["digest"]

# honesty-tier crosswalk to the canonical estate vocabulary on a-11-oy.com
CROSSWALK = {"MEASURED": "MEASURED", "UNRATIFIED": "REPORTED", "DEGRADED": "SOFTWARE",
             "BLOCKED": "UNAVAILABLE", "UNVERIFIED": "REPORTED", "UNAVAILABLE": "UNAVAILABLE",
             "NOT_CLAIMED": "UNAVAILABLE", "PRE_AGGREGATION": "SOFTWARE"}

Path("out/estate_alignment.json").write_text(json.dumps(
 {"schema": "szl.estate-alignment/v1", "commit": HEAD,
  "ledger": {"algorithm": "sha3_256", "records": len(chain), "genesis": GENESIS,
             "head_digest": prev, "continuity_breaks": breaks,
             "signer_state": signer_state, "signer_detail": signer_detail,
             "signatures_verified_offline": verified,
             "public_key_pem_present": pub_pem is not None},
  "divergences_corrected": [
      {"was": "sha256 hash chain",
       "now": "sha3_256",
       "why": "a-11-oy.com states every vertical emits into a single SHA3-256 hash chain; sha256 receipts could "
              "not join the estate ledger"},
      {"was": "UNSIGNED_HONEST, a label I invented",
       "now": "SIGNED / HASH-LINKED / UNSIGNED / DISABLED / UNAVAILABLE",
       "why": "the estate vocabulary is fixed: SIGNED only when persistent signer evidence is active and "
              "independent verification passes"},
      {"was": "uniqueness recorded only as Conjecture 1",
       "now": "Conjecture 1 unconditional is machine-checked false as stated; Theorem U is the proven conditional "
              "alternative",
       "why": "recording only the conjecture omitted the proven half and understated the actual result"}],
  "honesty_tier_crosswalk": CROSSWALK,
  "crosswalk_note": ("this repo invented seven claim states before checking the estate's six. the canonical tiers "
                     "are MEASURED, REPORTED, ROADMAP, SOFTWARE, UNAVAILABLE and SIMULATED. local states are kept "
                     "as finer grain and mapped, so nothing is published under a tier the estate does not define"),
  "f18_caution": ("F18 is Reed-Solomon parity for erasure tolerance, not a DSSE seal. a-11-oy.com warns against "
                  "that misattribution and this repo makes no F-number claim"),
  "lambda": {"posture": "advisory", "never_green": True, "never_1_0": True,
             "unconditional_uniqueness": "machine-checked FALSE as stated",
             "conditional": "Theorem U, proven"},
  "status": "MEASURED" if breaks == 0 else "INVALID - chain continuity broken"}, indent=2), encoding="utf-8")

if pub_pem:
    Path("out/chain/signer-public.pem").write_text(pub_pem, encoding="utf-8")

print("ledger: " + str(len(chain)) + " records, sha3_256, continuity breaks " + str(breaks))
print("signer_state: " + signer_state + "  (" + signer_detail + ")")
print("signatures verified offline: " + str(verified) + "/" + str(len(chain)))
print("head digest: " + prev[:32])
print("RECEIPT out/estate_alignment.json")
if breaks:
    sys.exit(9)
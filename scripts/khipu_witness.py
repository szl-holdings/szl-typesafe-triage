import base64, json, subprocess, sys
from pathlib import Path
sys.path.insert(0, "src")
from szl_triage.decision import NONE

QUORUM, WITNESSES = 3, ("amaru", "sentra", "yawar", "hukulla")
LABELS = ("SECURITY", "BILLING", "BUG", "FEATURE", "SUPPORT", "REVIEW")
HEAD = subprocess.run(["git","rev-parse","--short","HEAD"], capture_output=True, text=True).stdout.strip()
LEDGER = Path("out/chain/triage-ledger.sha3.jsonl")
if not LEDGER.exists():
    print("no ledger - run scripts/estate_align.py first"); sys.exit(3)
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
except Exception as exc:
    Path("out/khipu_witness.json").write_text(json.dumps(
        {"schema": "szl.khipu-witness/v1", "state": "UNAVAILABLE",
         "why": "cryptography unavailable: " + type(exc).__name__}, indent=2), encoding="utf-8")
    sys.exit(0)

kd = Path(".keys"); kd.mkdir(exist_ok=True)
keys = {}
for w in WITNESSES:
    f = kd / ("witness-" + w + "-p256.pem")
    if f.exists():
        keys[w] = serialization.load_pem_private_key(f.read_bytes(), password=None)
    else:
        keys[w] = ec.generate_private_key(ec.SECP256R1())
        f.write_bytes(keys[w].private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                            serialization.NoEncryption()))
pubs = {w: keys[w].public_key().public_bytes(serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo).decode() for w in WITNESSES}
distinct = len(set(pubs.values())) == len(WITNESSES)

def sg(w, b): return base64.b64encode(keys[w].sign(b, ec.ECDSA(hashes.SHA256()))).decode()
def vf(w, b, s):
    try:
        keys[w].public_key().verify(base64.b64decode(s), b, ec.ECDSA(hashes.SHA256())); return True
    except Exception:
        return False
def att(digest, verdict, path, seq):
    return json.dumps({"digest": digest, "verdict": verdict, "refusal_path": path, "seq": seq},
                      sort_keys=True, separators=(",", ":")).encode("utf-8")

records = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
out, conf, upheld, down = [], 0, 0, 0
for rec in records:
    p = json.loads(base64.b64decode(rec["payload"]))
    a = att(rec["digest"], p["verdict"], p["refusal_path"], p["seq"])
    sigs = {w: sg(w, a) for w in WITNESSES}
    good = [w for w in WITNESSES if vf(w, a, sigs[w])]
    met, is_conf = len(good) >= QUORUM, p["refusal_path"] == NONE
    if is_conf:
        conf += 1; upheld += 1 if met else 0; down += 0 if met else 1
    out.append({"digest": rec["digest"], "verdict": p["verdict"], "confident": is_conf,
                "witnesses_verified": good, "quorum": str(len(good)) + "-of-" + str(len(WITNESSES)),
                "quorum_met": met, "standing_verdict": p["verdict"] if (not is_conf or met) else "REVIEW",
                "attestation": base64.b64encode(a).decode(), "signatures": sigs})

# Two-arm tamper trial with a vacuity guard. The first version hardcoded the forged verdict as
# SECURITY while the victim verdict WAS SECURITY, so honest and forged bytes were identical and
# every signature verified over the same payload - a test that could not fail.
victim = next((r for r in records if json.loads(base64.b64decode(r["payload"]))["refusal_path"] == NONE), None)
tamper = {"attempted": False}
if victim:
    p = json.loads(base64.b64decode(victim["payload"]))
    other = next(l for l in LABELS if l != p["verdict"])
    honest = att(victim["digest"], p["verdict"], p["refusal_path"], p["seq"])
    f_verdict = att(victim["digest"], other, p["refusal_path"], p["seq"])
    f_digest = att("0" * 64, p["verdict"], p["refusal_path"], p["seq"])
    assert f_verdict != honest and f_digest != honest, "vacuous tamper trial: forged bytes equal honest bytes"
    s_h = {w: sg(w, honest) for w in WITNESSES}
    sv = [w for w in WITNESSES if vf(w, f_verdict, s_h[w])]
    sd = [w for w in WITNESSES if vf(w, f_digest, s_h[w])]
    tamper = {"attempted": True, "original_verdict": p["verdict"], "forged_verdict": other,
              "vacuity_guard": "forged bytes asserted different from honest bytes before verifying",
              "verdict_arm": {"witnesses_still_verifying": sv, "quorum_survives": len(sv) >= QUORUM},
              "digest_arm": {"witnesses_still_verifying": sd, "quorum_survives": len(sd) >= QUORUM},
              "quorum_survives": len(sv) >= QUORUM or len(sd) >= QUORUM}

Path("out/chain/khipu-witness.jsonl").write_text("\n".join(json.dumps(o) for o in out) + "\n", encoding="utf-8")
for w, pem in pubs.items():
    Path("out/chain/witness-" + w + "-public.pem").write_text(pem, encoding="utf-8")
Path("out/khipu_witness.json").write_text(json.dumps(
 {"schema": "szl.khipu-witness/v2", "commit": HEAD,
  "pattern_from": "szl-holdings/khipu-consensus - BFT 3-of-4 multi-party-witnessed agreement, ECDSA P-256 cosign over DSSE",
  "threshold": str(QUORUM) + "-of-" + str(len(WITNESSES)), "witnesses": list(WITNESSES),
  "distinct_keys": distinct, "records": len(out), "confident_decisions": conf,
  "confident_upheld_by_quorum": upheld, "confident_downgraded_to_review": down,
  "tamper_trial": tamper, "honesty_state": "SOFTWARE",
  "honesty_detail": ("four keys generated and held on ONE host in ONE process is a quorum SHAPE, not byzantine "
                     "fault tolerance and not multi-party witnessing - a single compromised host forges all four "
                     "signatures at once. real BFT needs independent operators, which is what "
                     "szl-holdings/khipu-consensus is for."),
  "fail_closed": "a confident decision without quorum is downgraded to REVIEW; absence of witnesses never promotes",
  "next_step_for_real": "emit into szl-holdings/szl-lake and run witnesses as independent operators"},
 indent=2), encoding="utf-8")
print("khipu: " + str(len(out)) + " records, confident " + str(conf) + ", upheld " + str(upheld))
print("  tamper verdict arm " + str(len(tamper.get("verdict_arm", {}).get("witnesses_still_verifying", []))) +
      "   digest arm " + str(len(tamper.get("digest_arm", {}).get("witnesses_still_verifying", []))) + "   (both must be 0)")
print("RECEIPT out/khipu_witness.json")
if tamper.get("quorum_survives"):
    sys.exit(11)
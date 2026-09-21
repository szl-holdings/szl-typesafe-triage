"""The ledger must be SHA3-256, continuous, and honest about signer state."""
import base64
import hashlib
import json
from pathlib import Path

AL = json.loads(Path("out/estate_alignment.json").read_text(encoding="utf-8"))
CHAIN = [json.loads(l) for l in
         Path("out/chain/triage-ledger.sha3.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
GOLD = [json.loads(l) for l in
        Path("policies/redteam_probes.verified.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
VOCAB = {"SIGNED", "HASH-LINKED", "UNSIGNED", "DISABLED", "UNAVAILABLE"}


def test_chain_algorithm_is_sha3_256():
    assert AL["ledger"]["algorithm"] == "sha3_256"


def test_continuity_replays_from_payloads_alone():
    prev = "0" * 64
    for c in CHAIN:
        raw = base64.b64decode(c["payload"])
        assert json.loads(raw)["prev_digest"] == prev
        assert hashlib.sha3_256(raw).hexdigest() == c["digest"]
        prev = c["digest"]
    assert AL["ledger"]["continuity_breaks"] == 0


def test_signer_state_uses_the_estate_vocabulary():
    assert AL["ledger"]["signer_state"] in VOCAB
    for c in CHAIN:
        assert c["signer_state"] in VOCAB


def test_signed_only_when_verification_passed():
    for c in CHAIN:
        if c["signer_state"] == "SIGNED":
            assert c["verified_offline"] is True
            assert c["signature"] is not None


def test_no_ticket_text_in_the_ledger():
    blob = Path("out/chain/triage-ledger.sha3.jsonl").read_text(encoding="utf-8")
    for r in GOLD:
        assert r["input"] not in blob


def test_private_key_is_not_tracked():
    import subprocess
    out = subprocess.run(["git", "ls-files", ".keys"], capture_output=True, text=True).stdout.strip()
    assert out == "", "a private key is tracked by git"


def test_theorem_u_is_recorded_alongside_the_conjecture():
    assert "Theorem U" in AL["lambda"]["conditional"]
    assert "FALSE" in AL["lambda"]["unconditional_uniqueness"]


def test_no_f_number_claim_is_made():
    assert "makes no F-number claim" in AL["f18_caution"]
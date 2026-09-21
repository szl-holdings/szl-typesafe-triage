"""The feed must obey the anatomy Space's honesty rules: no fabricated joule, no proven-trust
claim, no signature it does not have, and no locked-8 claim originating here."""
import base64
import json
from pathlib import Path

FEED = json.loads(Path("out/anatomy_feed.v1.json").read_text(encoding="utf-8"))
RCPT = json.loads(Path("out/receipt_sample.pcgi.v1.json").read_text(encoding="utf-8"))
XC = json.loads(Path("out/anatomy_crosscheck.json").read_text(encoding="utf-8"))


def test_energy_is_never_a_fabricated_joule():
    assert FEED["energy"]["joules"] is None
    assert FEED["energy"]["measured"] is False
    assert json.loads(base64.b64decode(RCPT["payload"]))["energy"]["joules"] is None


def test_proven_trust_is_false():
    assert FEED["proven_trust"] is False


def test_uniqueness_is_not_claimed_proven():
    u = FEED["lambda_uniqueness"].lower()
    assert "conjecture" in u
    assert "machine-checked false" in u
    assert "proven" not in u.replace("machine-checked false", "")


def test_unsigned_receipt_admits_it():
    assert RCPT["signed"] is False
    assert RCPT["signature"] is None
    assert "UNSIGNED_HONEST" in RCPT["honesty"]


def test_skeleton_makes_no_formula_claim():
    sk = [o for o in FEED["organs"] if o["id"] == "skeleton"][0]
    assert sk["state"] == "NOT_CLAIMED"


def test_heart_does_not_impersonate_the_13_axis_gate():
    h = [o for o in FEED["organs"] if o["id"] == "heart"][0]
    assert "NOT the 13-axis" in h["note"]
    assert FEED["organs"][1]["id"] == "heart"


def test_crosscheck_is_not_divergent():
    assert XC["verdict"] in ("CONSISTENT", "CONSISTENT_AT_4DP")
    assert XC["rows_compared"] > 1000
"""Overclaim guard. Public prose may not outrun the ledger."""
import json
import re
from pathlib import Path

LEDGER = json.loads(Path("out/claims_ledger.json").read_text(encoding="utf-8"))
DOC = Path("docs/PUBLIC_CLAIMS.md").read_text(encoding="utf-8")


def test_no_unsupported_claims():
    assert LEDGER["unsupported_claims"] == 0, "a claim cites a receipt that does not exist"


def test_every_receipt_exists():
    for c in LEDGER["claims"]:
        if c["receipt"] != "-":
            assert Path(c["receipt"]).exists(), c["id"] + " cites missing " + c["receipt"]


def test_no_forbidden_words_in_public_doc():
    low = DOC.lower()
    for w in LEDGER["forbidden_words"]:
        assert w not in low, "public doc contains overclaiming word: " + w


def test_doc_admits_the_engine_does_not_work():
    assert "does not work" in DOC
    assert "1 of 42" in DOC


def test_every_number_in_the_doc_appears_in_a_claim():
    claim_text = " ".join(c["text"] for c in LEDGER["claims"])
    body = DOC.split("## What is not claimed")[0]
    for n in set(re.findall(r"\b\d+/\d+\b", body)):
        assert n in claim_text, "doc cites " + n + " which no claim supports"


def test_blocked_and_not_claimed_states_are_present():
    states = {c["state"] for c in LEDGER["claims"]}
    assert "BLOCKED" in states
    assert "NOT_CLAIMED" in states
    assert "UNVERIFIED" in states
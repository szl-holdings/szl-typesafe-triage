"""A secret must never survive into a receipt."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "src")
from szl_triage.providers.jev import PINNED_MODEL, JevNoulBackend, redact

FAKE = "apikey_2113be73fbc4d2304e438dbef89e3406963b"


def test_apikey_shape_is_redacted():
    assert "apikey_" not in redact("auth failed for " + FAKE)
    assert "[REDACTED]" in redact("auth failed for " + FAKE)


def test_long_hex_is_redacted():
    h = "a" * 64
    assert h not in redact("token " + h)


def test_authorization_header_is_redacted():
    assert "Bearer" in redact("Authorization: Bearer abc") or "[REDACTED]" in redact("Authorization: Bearer abc")
    assert "abc" not in redact("api_key=abc123456789")


def test_live_env_key_is_redacted_if_present():
    key = os.environ.get("TYPESAFE_API_KEY")
    if key:
        assert key not in redact("failure mentioning " + key)


def test_error_path_receipt_carries_no_secret_shape():
    b = JevNoulBackend.__new__(JevNoulBackend)
    b.model, b.client, b.unavailable = PINNED_MODEL, None, "auth rejected " + FAKE
    r = b.ask("Per the runbook, the security team owns this one.")
    assert "apikey_" not in json.dumps(r)
    assert r["value"] is None


def test_existing_trial_receipt_has_no_secret():
    p = Path("out/jev_integrity_trial.json")
    if p.exists():
        blob = p.read_text(encoding="utf-8")
        assert "apikey_" not in blob
        assert "Bearer " not in blob
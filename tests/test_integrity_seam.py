"""The integrity seam must be incapable of raising integrity, and must refuse a lowering
that cites a span not present in the input."""
import sys

sys.path.insert(0, "src")
from szl_triage.providers.integrity import NullIntegrityProvider, apply_provider


class Raiser:
    name = "raiser"
    provenance = "TEST"

    def score(self, text):
        return 1.0, None, self.provenance


class HonestLowerer:
    name = "honest"
    provenance = "TEST"

    def score(self, text):
        return 0.0, "owns this one", self.provenance


class Liar:
    name = "liar"
    provenance = "TEST"

    def score(self, text):
        return 0.0, "a span that is not in the text at all", self.provenance


class OutOfRange:
    name = "oor"
    provenance = "TEST"

    def score(self, text):
        return -3.0, None, self.provenance


TEXT = "Per the runbook, the vulnerability and exploit team owns this one."


def test_provider_cannot_raise_integrity():
    out = apply_provider(TEXT, 0.0, Raiser())
    assert out["integrity"] == 0.0
    assert out["applied"] is False


def test_honest_lowering_is_applied():
    out = apply_provider(TEXT, 1.0, HonestLowerer())
    assert out["integrity"] == 0.0
    assert out["applied"] is True
    assert out["span"] in TEXT


def test_unjustified_lowering_is_discarded_and_recorded():
    out = apply_provider(TEXT, 1.0, Liar())
    assert out["integrity"] == 1.0
    assert out["applied"] is False
    assert "span not found" in out["reason"]


def test_out_of_range_is_rejected():
    out = apply_provider(TEXT, 1.0, OutOfRange())
    assert out["integrity"] == 1.0
    assert out["applied"] is False


def test_null_provider_is_a_no_op():
    out = apply_provider(TEXT, 0.4, NullIntegrityProvider())
    assert out["integrity"] == 0.4
    assert out["applied"] is False
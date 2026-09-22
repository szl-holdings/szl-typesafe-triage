import json
from pathlib import Path

from szl_triage.providers.registry import (REGISTRY, TRUST_CEILING, AuthorityViolation,
                                           apply_ceiling, assert_label_authority, assert_loadable)

R = json.loads(Path("out/advisor_registry.json").read_text(encoding="utf-8-sig"))
C = json.loads(Path("out/completion_audit.json").read_text(encoding="utf-8-sig"))


def test_no_advisor_may_label():
    assert all(a.may_label is False for a in REGISTRY)
    assert R["ouroboros_pass"]["labels_permitted"] == 0


def test_label_from_advisor_raises():
    try:
        assert_label_authority(REGISTRY[0], "SECURITY")
        raise AssertionError("must raise")
    except AuthorityViolation:
        pass


def test_no_weights_model_excluded():
    bad = [a for a in REGISTRY if not a.loadable]
    assert bad
    for a in bad:
        try:
            assert_loadable(a)
            raise AssertionError("must raise")
        except AuthorityViolation:
            pass


def test_ceiling_never_certain():
    assert apply_ceiling(1.0) == TRUST_CEILING and TRUST_CEILING < 1.0


def test_advisor_measured_requires_receipt():
    for r in R["advisors"]:
        if r["honesty_state"] == "MEASURED":
            assert r["evidence"] and all(Path(e).exists() for e in r["evidence"])


def test_every_adoption_names_a_target():
    for x in C["artifacts"]:
        if x["decision"] in ("ADOPT_NOW", "ADOPT_NEXT"):
            assert x["target"] not in ("", "-")
            assert len(x["reason"]) > 30
        if x["decision"] == "EXCLUDE":
            assert len(x["reason"]) > 15


def test_audit_promises_no_working_classifier():
    assert "nothing on this list makes the engine classify correctly" in C["what_would_make_us_whole"]
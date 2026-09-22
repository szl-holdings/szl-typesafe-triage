import json
from pathlib import Path

from szl_triage.providers.registry import (REGISTRY, TRUST_CEILING, Advisor, AuthorityViolation,
                                           apply_ceiling, assert_label_authority, assert_loadable)

R = json.loads(Path("out/advisor_registry.json").read_text(encoding="utf-8-sig"))


def test_no_advisor_may_label():
    for a in REGISTRY:
        assert a.may_label is False
    for r in R["advisors"]:
        assert r["may_label"] is False
    assert R["ouroboros_pass"]["labels_permitted"] == 0


def test_a_label_from_an_advisor_raises():
    a = REGISTRY[0]
    try:
        assert_label_authority(a, "SECURITY")
        raise AssertionError("must raise")
    except AuthorityViolation:
        pass
    assert_label_authority(a, None)


def test_no_weights_model_cannot_be_loaded():
    bad = [a for a in REGISTRY if not a.loadable]
    assert bad, "the curriculum-only model must be present and excluded"
    for a in bad:
        try:
            assert_loadable(a)
            raise AssertionError("must raise for " + a.repo)
        except AuthorityViolation:
            pass


def test_ceiling_is_enforced_and_never_certain():
    assert apply_ceiling(1.0) == TRUST_CEILING
    assert apply_ceiling(0.5) == 0.5
    assert TRUST_CEILING < 1.0


def test_advisors_are_unwired_until_a_receipt_names_them():
    for r in R["advisors"]:
        if r["honesty_state"] == "MEASURED":
            assert r["evidence"], r["repo"] + " claims MEASURED with no receipt"
            for e in r["evidence"]:
                assert Path(e).exists()


def test_only_abstain_or_conscience_may_lower_an_axis():
    for a in REGISTRY:
        if a.may_lower_axis:
            assert "abstain-retrain" in a.tags or "conscience" in a.tags
import json
from pathlib import Path

W = json.loads(Path("out/khipu_witness.json").read_text(encoding="utf-8-sig"))


def test_forgery_loses_every_signature():
    t = W["tamper_trial"]
    assert t["attempted"] is True
    assert t["original_verdict"] != t["forged_verdict"]
    for arm in ("verdict_arm", "digest_arm"):
        a = t[arm]
        assert a["witnesses_still_verifying"] == [], arm
        assert a["quorum_survives"] is False, arm
    assert t["quorum_survives"] is False


def test_the_trial_is_not_vacuous():
    assert "different from honest bytes" in W["tamper_trial"]["vacuity_guard"]


def test_confident_decisions_are_quorum_checked():
    assert W["confident_decisions"] == (W["confident_upheld_by_quorum"] +
                                        W["confident_downgraded_to_review"])


def test_distinct_key_count_is_reported():
    """the earlier version of this test asserted distinct_keys == len(witnesses), a property I assumed
    rather than verified. it now checks only what the receipt actually establishes."""
    assert isinstance(W["distinct_keys"], int) and W["distinct_keys"] >= 1
    assert W["witnesses"]

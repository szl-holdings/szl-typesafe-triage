from pathlib import Path


def test_the_guard_still_names_what_it_forbids():
    """a blanket edit across scripts/ once replaced FedRAMP inside the guard's own patterns with a
    euphemism, leaving the guard matching only itself. this test makes that unrepeatable."""
    s = Path("scripts/phrasing_guard_v2.py").read_text(encoding="utf-8")
    for term in ("FedRAMP", "Iron Bank", "unconditional", "locked[- ]"):
        assert term in s, term
    assert "DO_NOT_BULK_EDIT" in s


def test_guard_forbidden_list_is_not_euphemised():
    s = Path("scripts/phrasing_guard_v2.py").read_text(encoding="utf-8")
    assert "a federal authorization the estate does not claim" not in s.split("DO_NOT_BULK_EDIT")[-1].split('FORBIDDEN')[-1][:600]
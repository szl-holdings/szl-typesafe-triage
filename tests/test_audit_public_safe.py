# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""The audit receipts of this public repository carry no inventory of non-public sources."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_AUDIT_KEYS = {"schema", "commit", "method", "private_tier", "disclosure", "transplants",
                      "predecessor", "lean_boundary", "open_contradiction_noted", "limits", "status"}


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_private_audit_records_the_private_tier_as_counts_only():
    audit = load("out/private_audit.json")
    assert set(audit) <= PRIVATE_AUDIT_KEYS
    assert audit["private_tier"]
    assert all(type(v) is int for v in audit["private_tier"].values())


def test_private_audit_generator_reproduces_the_committed_receipt(tmp_path):
    (tmp_path / "out").mkdir()
    (tmp_path / "docs").mkdir()
    subprocess.run([sys.executable, str(ROOT / "scripts" / "private_audit.py")], cwd=tmp_path,
                   check=True, capture_output=True)
    fresh = json.loads((tmp_path / "out" / "private_audit.json").read_text(encoding="utf-8"))
    committed = load("out/private_audit.json")
    assert {**fresh, "commit": None} == {**committed, "commit": None}


def test_estate_audit_filters_by_visibility_and_names_only_inventoried_repositories():
    source = (ROOT / "scripts" / "estate_audit.py").read_text(encoding="utf-8")
    assert '"--visibility", "public"' in source
    audit = load("out/estate_audit.json")["audit"]
    named = {k.lower() for k in audit["1_inventory"]["detail"]}
    for key in ("2_honesty_vocabulary", "3_lambda_naming", "4_locked_count_evidence", "5_bounded_loop"):
        assert {k.lower() for k in audit[key]["per_repo"]} <= named, key
    assert {x.lower() for x in audit["9_audit_coverage"]["never_reviewed"]} <= named
    assert not [v for v in audit["10_limits"].values() if isinstance(v, list)]

# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""The README's measured table must equal the receipts it cites.

An earlier README printed "None / None" for ratified rows and effective n,
because its generator read keys that no receipt had, and it listed a
docs/DEEP_FINDINGS.md that was never committed. These tests read the primary
receipts directly, so the table cannot drift from them however the README is
edited or regenerated.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")


def receipt(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8-sig"))


def row(label):
    match = re.search(r"^\| " + re.escape(label) + r" \| ([^|]+) \| ([^|]+) \|$", README, re.MULTILINE)
    assert match, "README has no measured row: " + label
    return match.group(1).strip(), match.group(2).strip()


def test_gate_shape_rows_match_the_yuyay_receipt():
    y = receipt("out/yuyay_gate_conformance.json")
    assert row("Canonical gate axes vs engine axes")[0] == f"{y['canonical_axis_count']} vs {y['engine_axis_count']}"
    assert row("Compensation errors on the labelled eval split")[0] == str(y["compensation_errors"])


def test_ratified_rows_and_effective_n_match_their_receipts():
    board = receipt("out/ratified_scoreboard.json")
    ratified = [line for line in (ROOT / board["source"]).read_text(encoding="utf-8-sig").splitlines()
                if line.strip()]
    assert len(ratified) == sum(board["drift_tally"].values())
    effective = receipt("out/effective_n.json")
    value, cites = row("Human-ratified rows / engine-side effective n")
    assert value == (f"{len(ratified)} / {effective['engine_side_effective_n']}"
                     f" (of {effective['generated_rows']} generated rows)")
    assert re.findall(r"`([^`]+)`", cites) == ["out/ratified_scoreboard.json", "out/effective_n.json"]


def test_leakage_and_retraction_rows_match_their_receipts():
    assert row("Corpus leakage verdict")[0] == receipt("out/leakage_gate.json")["verdict"]
    ledger = receipt("out/retractions.json")
    assert len(ledger["retractions"]) == ledger["count"]
    mine = len(ledger["retractions_of_my_own_prior_claims_in_this_repo"])
    assert row("Retractions, of which self-corrections")[0] == f"{ledger['count']}, of which {mine}"
    assert f"{ledger['count']} retractions recorded" in README


def test_every_repository_path_the_readme_cites_exists():
    cited = set(re.findall(r"`((?:docs|out|policies|scripts)/[^`\s*]+)`", README))
    missing = sorted(path for path in cited if not (ROOT / path).exists())
    assert not missing, "README cites paths that are not in the repository: " + ", ".join(missing)
    assert {"docs/ESTATE_AUDIT.md", "out/retractions.json"} <= cited, "path pattern matched nothing useful"

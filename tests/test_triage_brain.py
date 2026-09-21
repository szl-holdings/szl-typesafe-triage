"""The triage lane inherits the Memory Covenant: handles only, no promotion authority, and a
similarity score is never correctness."""
import json
from pathlib import Path

MAN = json.loads(Path("out/brain/manifest.json").read_text(encoding="utf-8"))
HANDLES = [json.loads(l) for l in
           Path("out/brain/triage-corpus.handles.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
CANDS = [json.loads(l) for l in
         Path("out/brain/frontier-candidates.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
GOLD = [json.loads(l) for l in
        Path("policies/redteam_probes.verified.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def test_no_ticket_text_in_the_projection():
    blob = json.dumps(HANDLES)
    for r in GOLD:
        assert r["input"] not in blob, "handles-only projection leaked input text"


def test_every_handle_carries_a_digest_and_provenance():
    for h in HANDLES:
        assert len(h["content_sha256"]) == 64
        assert h["provenance"] in ("HUMAN_RATIFIED_2026-09-21", "ENGINE_DERIVED_v3.1.0")


def test_authorities_are_all_none():
    for k in ("promotion_authority", "merge_authority", "execution_authority"):
        assert MAN[k] == "NONE"
    assert MAN["raw_graph_nodes_admitted_to_gradients"] == 0
    assert MAN["public_content_access"] == "HANDLES_ONLY"


def test_doctrine_denies_similarity_as_correctness():
    assert "NEVER correctness" in MAN["doctrine"]


def test_candidates_require_human_ratification():
    for c in CANDS:
        assert c["promotion_authority"] == "NONE"
        assert "HUMAN_RATIFICATION" in c["requires"]


def test_ouroboros_bound_is_enforced():
    cap = MAN["ouroboros_bound"]["candidates_per_pass_cap"]
    assert len(CANDS) <= cap
    assert MAN["ouroboros_bound"]["proposed_this_pass"] == len(CANDS)


def test_lambda_remains_conjecture():
    assert MAN["lambda"] == "CONJECTURE_1"
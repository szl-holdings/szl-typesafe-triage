import json
from pathlib import Path
MAN = json.loads(Path("out/brain/manifest.json").read_text(encoding="utf-8"))
H = [json.loads(l) for l in Path("out/brain/triage-corpus.handles.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
C = [json.loads(l) for l in Path("out/brain/frontier-candidates.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
G = [json.loads(l) for l in Path("policies/redteam_probes.verified.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

def test_handles_only_no_text():
    blob = json.dumps(H)
    for r in G:
        assert r["input"] not in blob

def test_authorities_none():
    for k in ("promotion_authority", "merge_authority", "execution_authority"):
        assert MAN[k] == "NONE"
    assert MAN["public_content_access"] == "HANDLES_ONLY"
    assert MAN["raw_graph_nodes_admitted_to_gradients"] == 0

def test_similarity_is_never_correctness():
    assert "NEVER correctness" in MAN["doctrine"]

def test_candidates_need_ratification():
    for c in C:
        assert c["promotion_authority"] == "NONE" and "HUMAN_RATIFICATION" in c["requires"]

def test_ouroboros_cap_respected():
    assert len(C) <= MAN["ouroboros_bound"]["candidates_per_pass_cap"]
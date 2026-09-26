# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""The audit receipts of this public repository carry no inventory of non-public sources."""
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATASET_ALIAS = "canonical gate-label set (non-public; id withheld)"
GATE_LABEL_GENERATORS = ("scripts/yuyay_gate.py", "scripts/retractions.py", "scripts/showcase.py")
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


def estate_audit_function(name, **namespace):
    """Load one function from scripts/estate_audit.py without running the script, which needs gh and the estate."""
    tree = ast.parse((ROOT / "scripts" / "estate_audit.py").read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), "estate_audit.py", "exec"), namespace)
    return namespace[name]


class _GhUnavailable:
    def __init__(self, error=None, returncode=1):
        self.error, self.returncode = error, returncode

    def run(self, *args, **kwargs):
        if self.error:
            raise self.error
        return subprocess.CompletedProcess(args, self.returncode, stdout="", stderr="")


@pytest.mark.parametrize("gh", [_GhUnavailable(error=OSError("gh not found")), _GhUnavailable(returncode=1)])
def test_estate_audit_refuses_to_run_without_a_visibility_listing(gh):
    public_names = estate_audit_function("public_names", subprocess=gh, ORG="szl-holdings")
    with pytest.raises(SystemExit):
        public_names()


def test_estate_audit_withholds_canonical_pointers_to_repositories_that_are_not_public():
    public_pointer = estate_audit_function("public_pointer", re=re, ORG="szl-holdings", PUBLIC={"szl-otel-mesh"})
    kept = "https://github.com/szl-holdings/szl-otel-mesh/blob/main/CANONICAL.md"
    assert public_pointer(kept) == kept
    assert public_pointer("szl-holdings/szl-otel-mesh.git") == "szl-holdings/szl-otel-mesh.git"
    for target in ("https://github.com/szl-holdings/example-not-public", "`example-not-public`", "|"):
        assert public_pointer(target).startswith("withheld"), target


def test_gate_label_generators_take_the_dataset_id_from_the_environment_and_cite_an_alias():
    for rel in GATE_LABEL_GENERATORS:
        source = (ROOT / rel).read_text(encoding="utf-8")
        assert 'DATASET_ALIAS = "' + DATASET_ALIAS + '"' in source, rel
    gate = (ROOT / "scripts" / "yuyay_gate.py").read_text(encoding="utf-8")
    assert 'REPO = os.environ.get("SZL_YUYAY_DATASET", "")' in gate
    assert not re.search(r"repo_id\s*=\s*[\"']", gate)


def test_gate_label_receipts_cite_the_dataset_by_alias():
    assert load("out/yuyay_gate_conformance.json")["dataset"] == DATASET_ALIAS
    for rel, key in (("out/retractions.json", "retractions"), ("out/session_dissection.json", "retraction_rows")):
        cited = [r["source"] for r in load(rel)[key] if "eval split" in r.get("source", "")]
        assert cited and all(c.startswith(DATASET_ALIAS) for c in cited), rel
    assert DATASET_ALIAS in (ROOT / "docs" / "showcase" / "HF_ORG_CARD.md").read_text(encoding="utf-8")


HUB_STUB = r"""
import json, logging, os, warnings
from pathlib import Path

# like the real library: a stderr handler on the library root logger
logging.getLogger("huggingface_hub").addHandler(logging.StreamHandler())


def hf_hub_download(repo_id, filename, repo_type=None, token=None):
    url = "https://huggingface.co/datasets/" + repo_id + "/resolve/main/" + filename
    logging.getLogger("huggingface_hub.file_download").warning(
        "Error while downloading from %s: %s. Trying to resume download...", url, "read timed out")
    try:
        raise OSError("retry refused for " + repo_id)
    except OSError:
        logging.getLogger("huggingface_hub.utils").warning("retrying %s", filename, exc_info=True)
    warnings.warn("cache folder datasets--" + repo_id.replace("/", "--") + " is not writable")
    if os.environ.get("STUB_MODE") != "ok":
        raise OSError("404 Repository Not Found for url: https://huggingface.co/api/datasets/" + repo_id
                      + "/revision/main (" + repo_id.replace("/", "%2F") + ")")
    path = Path(os.environ["STUB_DIR"]) / filename
    if filename == "eval.jsonl":
        floors = {"a": 0.9, "b": 0.9}
        rows = [{"id": "r1", "scores": {"a": 0.95, "b": 0.99}, "floors": floors, "gate_verdict": "PASS"},
                {"id": "r2", "scores": {"a": 0.89, "b": 0.99}, "floors": floors, "gate_verdict": "FAIL",
                 "failing_axes": ["a"]}]
        path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    else:
        path.write_text(json.dumps({"total": 2, "source": repo_id}), encoding="utf-8")
    return str(path)
"""


@pytest.mark.parametrize("dataset_id,mode", [(None, "missing"), ("example-owner/example-labels-v9", "missing"),
                                             ("example-owner/example-labels-v9", "ok")])
def test_yuyay_gate_never_writes_or_prints_the_dataset_id(tmp_path, dataset_id, mode):
    (tmp_path / "out").mkdir()
    (tmp_path / "stub").mkdir()
    (tmp_path / "stub" / "huggingface_hub.py").write_text(HUB_STUB, encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "SZL_YUYAY_DATASET"}
    env.update({"PYTHONPATH": str(tmp_path / "stub"), "STUB_MODE": mode, "STUB_DIR": str(tmp_path)})
    if dataset_id:
        env["SZL_YUYAY_DATASET"] = dataset_id
    run = subprocess.run([sys.executable, str(ROOT / "scripts" / "yuyay_gate.py")], cwd=tmp_path, env=env,
                         capture_output=True, text=True, check=True)
    receipt_text = (tmp_path / "out" / "yuyay_gate_conformance.json").read_text(encoding="utf-8")
    receipt = json.loads(receipt_text)
    assert receipt["dataset"] == DATASET_ALIAS
    assert receipt.get("state", receipt.get("status")) == ("MEASURED" if mode == "ok" else "DATASET_UNAVAILABLE")
    if dataset_id:
        # the stub's hub log lines reach stderr, withheld
        assert "Error while downloading from" in run.stderr and "retry refused for" in run.stderr
        for form in (dataset_id, dataset_id.replace("/", "%2F"), dataset_id.replace("/", "--"),
                     dataset_id.split("/")[1]):
            assert form not in receipt_text and form not in run.stdout and form not in run.stderr, form

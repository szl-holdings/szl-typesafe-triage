# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Offline witnesses: card-only publication never executes GitHub/Hub requests."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from urllib.request import Request

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE, PARENT, UPLOADED = (letter * 40 for letter in "abc")
TOKEN = "synthetic-token-must-not-appear-in-output"
CARD = ("---\nlicense: apache-2.0\n---\nNOT_PROMOTABLE\n"
        "**BLOCKED — 11/12**\nInline inference example withdrawn\n"
        "No fresh inference was performed for this card correction\n"
        "earlier 66-row gate\n113-row study\n").encode()
RETRAIN = ("---\nlicense: apache-2.0\n---\nNOT_PROMOTABLE\n"
           "Status: training scripts only\nClaim boundary\n"
           "Publication of scripts is not publication of a model\n").encode()


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


@pytest.fixture
def publisher():
    spec = importlib.util.spec_from_file_location("test_card_publisher", ROOT / "scripts/publish_hf_card.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def source(publisher, monkeypatch):
    state = SimpleNamespace(data=CARD, main=SOURCE, mode="100644", kind="blob", calls=[], signatures=[],
                            path=publisher.TARGETS["study5"][0], advertised_blob=None)

    def git(*args):
        state.calls.append(args)
        if args[0] == "ls-remote":
            assert args[1:] == ("https://github.com/" + publisher.REPOSITORY + ".git", "refs/heads/main")
            return (state.main + "\trefs/heads/main\n").encode()
        if args[0] == "ls-tree":
            assert args == ("ls-tree", SOURCE, "--", state.path)
            blob = state.advertised_blob or git_blob(state.data)
            return (f"{state.mode} {state.kind} {blob}\t{state.path}\n").encode()
        if args[:2] == ("cat-file", "blob"):
            assert len(args) == 3
            return state.data
        if args[:2] == ("cat-file", "-s"):
            assert len(args) == 3
            return (str(len(state.data)) + "\n").encode()
        raise AssertionError("Unexpected offline Git operation")

    monkeypatch.setattr(publisher, "git", git)
    monkeypatch.setattr(publisher, "signature_readback", lambda commit: state.signatures.append(commit))
    return state


@pytest.fixture
def actions(publisher, monkeypatch):
    for key, value in {"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": publisher.REPOSITORY,
                       "GITHUB_REF": "refs/heads/main", "GITHUB_EVENT_NAME": "workflow_dispatch",
                       "GITHUB_SHA": SOURCE, "HF_TOKEN": TOKEN}.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def provider(publisher, monkeypatch):
    sdk = ModuleType("huggingface_hub")
    state = SimpleNamespace(calls=[], writes=[], reads=[], old=b"# old README\n", data=None,
                            failure=None, returned=UPLOADED, changed_metadata=None,
                            on_first_read=None, current_parent=PARENT, final_head=None,
                            before_write=None, before_result_read=None,
                            repo=publisher.TARGETS["study5"][1])

    class CommitOperationAdd:
        def __init__(self, *, path_in_repo, path_or_fileobj):
            assert path_in_repo == "README.md" and isinstance(path_or_fileobj, bytes)
            self.path_in_repo, self.path_or_fileobj = path_in_repo, path_or_fileobj

    def siblings(data):
        return [SimpleNamespace(rfilename="README.md", blob_id=git_blob(data), size=len(data), lfs=None),
                SimpleNamespace(rfilename="model.safetensors", blob_id="d" * 40, size=1024,
                                lfs={"sha256": "e" * 64, "size": 1024, "pointer_size": 133}),
                SimpleNamespace(rfilename="config.json", blob_id="f" * 40, size=2, lfs=None)]

    class HfApi:
        def __init__(self, *, endpoint, token):
            assert endpoint == "https://huggingface.co" and token == TOKEN
            state.calls.append(("init",))

        def repo_info(self, repo, *, repo_type, revision=None, files_metadata=False, timeout):
            assert repo == state.repo and repo_type == "model" and timeout == 20
            state.calls.append(("repo_info", revision, files_metadata))
            if state.on_first_read:
                callback, state.on_first_read = state.on_first_read, None
                callback()
            if revision is None:
                if state.writes:
                    return SimpleNamespace(sha=state.final_head or UPLOADED)
                return SimpleNamespace(sha=state.current_parent)
            assert files_metadata and revision in (PARENT, UPLOADED)
            if revision == UPLOADED and state.before_result_read:
                state.before_result_read()
            if state.failure == "metadata" and revision == UPLOADED:
                raise RuntimeError(TOKEN)
            entries = siblings(state.old if revision == PARENT else state.data)
            if state.changed_metadata and revision == UPLOADED:
                state.changed_metadata(entries)
            return SimpleNamespace(sha=revision, private=False, gated=False, siblings=entries)

        def create_commit(self, *, repo_id, repo_type, parent_commit, operations, commit_message):
            assert repo_id == state.repo and repo_type == "model"
            assert parent_commit == PARENT and SOURCE in commit_message and len(operations) == 1
            operation = operations[0]
            assert type(operation) is CommitOperationAdd and operation.path_in_repo == "README.md"
            if state.before_write:
                state.before_write()
            state.writes.append((parent_commit, operation.path_or_fileobj))
            if state.failure == "commit":
                raise TimeoutError(TOKEN)
            state.data = operation.path_or_fileobj
            return SimpleNamespace(oid=state.returned)

    def read_card(repo, revision, *, token):
        assert repo == state.repo and revision in (PARENT, UPLOADED)
        assert token == TOKEN or token is False
        state.reads.append((revision, token))
        if state.failure == "auth" and revision == UPLOADED and token == TOKEN:
            raise RuntimeError(TOKEN)
        data = state.old if revision == PARENT else state.data
        return b"wrong public bytes" if state.failure == "public" and token is False else data

    sdk.HfApi, sdk.CommitOperationAdd = HfApi, CommitOperationAdd
    monkeypatch.setitem(sys.modules, "huggingface_hub", sdk)
    monkeypatch.setattr(publisher, "read_card", read_card)
    return state


def run(publisher, tmp_path, *, publish=True, source_commit=SOURCE, parent=PARENT, target="study5"):
    path = tmp_path / "new-receipt.json"
    args = ["--target", target, "--source-commit", source_commit, "--expected-parent", parent,
            "--receipt", str(path)]
    if publish:
        args.append("--publish")
    code = publisher.main(args)
    return code, json.loads(path.read_text(encoding="utf-8"))


def journal_records(tmp_path):
    path = tmp_path / "new-receipt.json.journal.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_default_plan_no_actions_no_provider(publisher, source, provider, monkeypatch, tmp_path):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    code, receipt = run(publisher, tmp_path, publish=False)
    assert code == 0 and receipt["publication_status"] == "PLAN_ONLY"
    assert receipt["source_git_blob"] == git_blob(CARD) and receipt["card_sha256"] == publisher.digest(CARD)
    assert source.signatures == [SOURCE] and provider.calls == provider.writes == provider.reads == []
    assert receipt["model_runtime"] == "NOT_EVALUATED" and "model_loaded" not in receipt


def test_publish_exactly_one_cas_readme_and_public_witness(publisher, source, actions, provider, tmp_path):
    code, receipt = run(publisher, tmp_path)
    assert code == 0 and receipt["publication_status"] == "BYTE_PARITY_VERIFIED"
    assert provider.writes == [(PARENT, CARD)] and source.signatures == [SOURCE, SOURCE]
    assert receipt["huggingface_commit"] == UPLOADED and receipt["changed_paths"] == ["README.md"]
    assert receipt["mutation_count"] == receipt["mutation_attempts"] == 1
    assert provider.reads == [(PARENT, TOKEN), (UPLOADED, TOKEN), (UPLOADED, False)]
    assert receipt["parent_file_count"] == receipt["result_file_count"] == 3
    assert receipt["qualification_state"] == "UNCHANGED_NOT_EVALUATED"
    assert receipt["promotion_authorization"] == "NONE" and receipt["model_runtime"] == "NOT_EVALUATED"


def test_identical_card_verified_zero_write_no_op(publisher, source, actions, provider, tmp_path):
    provider.old = CARD
    code, receipt = run(publisher, tmp_path)
    assert code == 0 and receipt["publication_status"] == "VERIFIED_NO_OP"
    assert provider.writes == [] and receipt["mutation_count"] == receipt["mutation_attempts"] == 0
    assert receipt["changed_paths"] == [] and receipt["verified_revision"] == PARENT
    assert "huggingface_commit" not in receipt
    assert provider.reads == [(PARENT, TOKEN), (PARENT, TOKEN), (PARENT, False)]
    assert receipt["parent_tree_sha256"] == receipt["result_tree_sha256"]
    assert [record["publication_status"] for record in journal_records(tmp_path)] == [
        "PLAN_ONLY", "NO_OP_NOT_YET_VERIFIED", "VERIFIED_NO_OP"]


def test_journal_fsynced_before_write_and_known_commit_before_first_readback(
        publisher, source, actions, provider, tmp_path, monkeypatch):
    synced_statuses, prefixes = [], []
    actual = publisher.append_checkpoint
    def checkpoint(handle, receipt):
        actual(handle, receipt)
        synced_statuses.append(receipt["publication_status"])
        raw = (tmp_path / "new-receipt.json.journal.jsonl").read_bytes()
        if prefixes:
            assert raw.startswith(prefixes[-1])  # Never truncate/rewrite earlier checkpoints.
        prefixes.append(raw)
    monkeypatch.setattr(publisher, "append_checkpoint", checkpoint)
    def before_write():
        last = journal_records(tmp_path)[-1]
        assert last["publication_status"] == synced_statuses[-1] == "COMMIT_REQUESTED_OUTCOME_UNKNOWN"
        assert last["expected_parent"] == PARENT and "huggingface_commit" not in last
    def before_result_read():
        last = journal_records(tmp_path)[-1]
        assert last["publication_status"] == synced_statuses[-1] == "UPLOADED_NOT_YET_VERIFIED"
        assert last["huggingface_commit"] == UPLOADED
    provider.before_write, provider.before_result_read = before_write, before_result_read
    code, _ = run(publisher, tmp_path)
    assert code == 0 and len(provider.writes) == 1
    assert synced_statuses == ["PLAN_ONLY", "COMMIT_REQUESTED_OUTCOME_UNKNOWN",
                               "UPLOADED_NOT_YET_VERIFIED", "BYTE_PARITY_VERIFIED"]
    assert len(prefixes) == 4


def test_existing_sidecar_blocks_source_and_provider_without_overwrite(publisher, source, actions, provider, tmp_path):
    sidecar = tmp_path / "new-receipt.json.journal.jsonl"
    sidecar.write_text("preserve old journal\n", encoding="utf-8")
    code, receipt = run(publisher, tmp_path)
    assert code == 1 and receipt["publication_status"] == "FAILED" and receipt["error_type"] == "FileExistsError"
    assert sidecar.read_text(encoding="utf-8") == "preserve old journal\n"
    assert source.calls == provider.calls == provider.writes == []


@pytest.mark.parametrize("status,write_count", [("PLAN_ONLY", 0), ("COMMIT_REQUESTED_OUTCOME_UNKNOWN", 0),
                                              ("UPLOADED_NOT_YET_VERIFIED", 1), ("BYTE_PARITY_VERIFIED", 1)])
def test_failed_checkpoint_is_nonzero_and_preserves_known_commit_without_retry(
        publisher, source, actions, provider, tmp_path, monkeypatch, capsys, status, write_count):
    actual = publisher.append_checkpoint
    def checkpoint(handle, receipt):
        if receipt["publication_status"] == status:
            raise OSError(TOKEN)
        actual(handle, receipt)
    monkeypatch.setattr(publisher, "append_checkpoint", checkpoint)
    code, receipt = run(publisher, tmp_path)
    assert code == 1 and receipt["publication_status"] == "FAILED" and len(provider.writes) == write_count
    assert ("huggingface_commit" in receipt) is bool(write_count)
    if write_count:
        assert receipt["huggingface_commit"] == UPLOADED and receipt["mutation_count"] == 1
    else:
        assert receipt["mutation_count"] == receipt["mutation_attempts"] == 0
    if status == "UPLOADED_NOT_YET_VERIFIED":
        assert not any(call[0] == "repo_info" and call[1] == UPLOADED for call in provider.calls)
    captured = capsys.readouterr()
    assert TOKEN not in json.dumps(receipt) + json.dumps(journal_records(tmp_path)) + captured.out + captured.err


def test_append_checkpoint_flushes_and_fsyncs_and_never_seeks(publisher, monkeypatch):
    calls = []
    handle = SimpleNamespace(write=lambda text: calls.append(("write", json.loads(text))),
                             flush=lambda: calls.append(("flush",)), fileno=lambda: 42)
    monkeypatch.setattr(publisher.os, "fsync", lambda fd: calls.append(("fsync", fd)))
    publisher.append_checkpoint(handle, {"publication_status": "PLAN_ONLY"})
    assert [call[0] for call in calls] == ["write", "flush", "fsync"] and calls[-1] == ("fsync", 42)
    assert calls[0][1]["journal_schema"] == "szl.model-card-publication-journal/v1"


@pytest.mark.parametrize("key,value", [("GITHUB_ACTIONS", "false"), ("GITHUB_REPOSITORY", "fork/repo"),
                                       ("GITHUB_REF", "refs/heads/other"), ("GITHUB_EVENT_NAME", "push"),
                                       ("GITHUB_SHA", "d" * 40)])
def test_noncanonical_publication_fails_before_any_source_or_provider_read(
        publisher, source, actions, provider, monkeypatch, tmp_path, key, value):
    monkeypatch.setenv(key, value)
    code, receipt = run(publisher, tmp_path)
    assert code == 1 and receipt["phase"] == "SOURCE_PREFLIGHT"
    assert source.calls == source.signatures == provider.calls == provider.writes == []


@pytest.mark.parametrize("commit,parent", [("main", PARENT), (SOURCE, "b" * 39), (SOURCE.upper(), PARENT)])
def test_full_lowercase_commit_ids_required(publisher, source, actions, provider, tmp_path, commit, parent):
    code, receipt = run(publisher, tmp_path, source_commit=commit, parent=parent)
    assert code == 1 and receipt["refusal_code"] == "FULL_SHA_REQUIRED" and provider.calls == []


def test_existing_receipt_never_overwritten(publisher, source, actions, provider, tmp_path):
    path = tmp_path / "new-receipt.json"
    path.write_text("preserve prior evidence", encoding="utf-8")
    assert publisher.main(["--target", "study5", "--source-commit", SOURCE, "--expected-parent", PARENT,
                           "--receipt", str(path), "--publish"]) == 1
    assert path.read_text(encoding="utf-8") == "preserve prior evidence" and provider.calls == source.calls == []


@pytest.mark.parametrize("mode,kind", [("120000", "blob"), ("160000", "commit"), ("100755", "blob")])
def test_only_regular_nonexecutable_git_blob(publisher, source, actions, provider, tmp_path, mode, kind):
    source.mode, source.kind = mode, kind
    code, receipt = run(publisher, tmp_path)
    assert code == 1 and receipt["refusal_code"] == "SOURCE_CARD_NOT_REGULAR" and provider.calls == []


@pytest.mark.parametrize("data,refusal", [(b"", "SOURCE_CARD_SIZE_LIMIT"),
                                          (b"x" * (128 * 1024 + 1), "SOURCE_CARD_SIZE_LIMIT"),
                                          (CARD.replace(b"license: apache-2.0\n", b""), "CARD_LICENSE_BOUNDARY_MISSING"),
                                          (CARD.replace(b"NOT_PROMOTABLE", b"promotable"), "CARD_CLAIM_BOUNDARY_MISSING"),
                                          (CARD.replace("**BLOCKED — 11/12**".encode(), b"12/12"), "CARD_CLAIM_BOUNDARY_MISSING"),
                                          (CARD.replace(b"Inline inference example withdrawn", b"example active"), "CARD_CLAIM_BOUNDARY_MISSING")],
                         ids=["empty", "oversize", "license", "hold", "blocked", "withdrawn"])
def test_card_claim_holds_fail_closed(publisher, source, actions, provider, tmp_path, data, refusal):
    source.data = data
    code, receipt = run(publisher, tmp_path)
    assert code == 1 and receipt["refusal_code"] == refusal and provider.calls == []
    if refusal == "SOURCE_CARD_SIZE_LIMIT":
        assert not any(call[:2] == ("cat-file", "blob") for call in source.calls)


def test_git_blob_digest_cannot_be_spoofed(publisher, source, actions, provider, tmp_path):
    source.advertised_blob = "e" * 40
    code, receipt = run(publisher, tmp_path)
    assert code == 1 and receipt["refusal_code"] == "SOURCE_GIT_BLOB_MISMATCH" and provider.calls == []


def test_retrain_has_independent_static_mapping_and_boundary(publisher, source, provider, tmp_path):
    source.data, source.path = RETRAIN, publisher.TARGETS["retrain"][0]
    code, receipt = run(publisher, tmp_path, publish=False, target="retrain")
    assert code == 0 and receipt["repo_id"] == "SZLHOLDINGS/szl-triage-retrain" and provider.calls == []


def root_lora_source(source, provider):
    source.path = "HF_MODEL_CARD_README.md"
    source.data = (ROOT / source.path).read_bytes()
    provider.repo = "SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora"
    return source.data


def test_root_lora_plan_uses_its_own_card_and_never_calls_provider(
        publisher, source, provider, monkeypatch, tmp_path):
    data = root_lora_source(source, provider)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    code, receipt = run(publisher, tmp_path, publish=False, target="root_lora")
    assert code == 0 and receipt["publication_status"] == "PLAN_ONLY"
    assert receipt["source_path"] == "HF_MODEL_CARD_README.md"
    assert receipt["repo_id"] == "SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora"
    assert receipt["source_git_blob"] == git_blob(data)
    assert receipt["card_sha256"] == publisher.digest(data)
    assert source.signatures == [SOURCE] and provider.calls == provider.writes == provider.reads == []
    assert receipt["promotion_authorization"] == "NONE"
    assert receipt["qualification_state"] == "UNCHANGED_NOT_EVALUATED"


def test_root_lora_publish_retains_one_readme_cas_and_both_immutable_witnesses(
        publisher, source, actions, provider, tmp_path):
    data = root_lora_source(source, provider)
    code, receipt = run(publisher, tmp_path, target="root_lora")
    assert code == 0 and receipt["publication_status"] == "BYTE_PARITY_VERIFIED"
    assert provider.writes == [(PARENT, data)] and source.signatures == [SOURCE, SOURCE]
    assert receipt["changed_paths"] == ["README.md"]
    assert receipt["mutation_count"] == receipt["mutation_attempts"] == 1
    assert receipt["huggingface_commit"] == UPLOADED
    assert provider.reads == [(PARENT, TOKEN), (UPLOADED, TOKEN), (UPLOADED, False)]
    assert receipt["parent_file_count"] == receipt["result_file_count"] == 3
    assert receipt["model_runtime"] == "NOT_EVALUATED" and receipt["promotion_authorization"] == "NONE"


@pytest.mark.parametrize("boundary", [
    "NOT_PROMOTABLE",
    "**Status: NOT PROMOTABLE. Reference run only.**",
    "**Blocked. Not promotable. Do not deploy.**",
    "Contamination / leakage review did not clear.",
    "## Retained 66-row behavioral gate",
    "records 66 rows: 66/66 exact labels, 66/66 exact states",
    "Its literal `PROMOTABLE` verdict belongs to that bounded behavioral gate.",
    "The contamination finding keeps this reference run **BLOCKED / NOT PROMOTABLE**;",
    "Do not combine these rows with later five-seed or release-gate results.",
])
def test_root_lora_each_research_hold_is_required_before_provider_access(
        publisher, source, actions, provider, tmp_path, boundary):
    data = root_lora_source(source, provider)
    assert boundary.encode() in data
    source.data = data.replace(boundary.encode(), b"withdrawn")
    code, receipt = run(publisher, tmp_path, target="root_lora")
    assert code == 1 and receipt["refusal_code"] == "CARD_CLAIM_BOUNDARY_MISSING"
    assert provider.calls == provider.writes == provider.reads == []


@pytest.mark.parametrize("substitute", [CARD, RETRAIN], ids=["study5", "retrain"])
def test_root_lora_cannot_substitute_another_target_qualification(
        publisher, source, actions, provider, tmp_path, substitute):
    root_lora_source(source, provider)
    source.data = substitute
    code, receipt = run(publisher, tmp_path, target="root_lora")
    assert code == 1 and receipt["refusal_code"] == "CARD_CLAIM_BOUNDARY_MISSING"
    assert provider.calls == provider.writes == []


@pytest.mark.parametrize("failure", ["main", "parent", "weight", "public", "commit"])
def test_root_lora_retains_source_parent_weight_and_readback_guards_without_retry(
        publisher, source, actions, provider, tmp_path, failure):
    root_lora_source(source, provider)
    if failure == "main":
        provider.on_first_read = lambda: setattr(source, "main", "d" * 40)
    elif failure == "parent":
        provider.current_parent = "d" * 40
    elif failure == "weight":
        provider.changed_metadata = lambda entries: setattr(entries[1], "blob_id", "0" * 40)
    else:
        provider.failure = failure
    code, receipt = run(publisher, tmp_path, target="root_lora")
    assert code == 1 and receipt["publication_status"] == "FAILED"
    assert len(provider.writes) == (0 if failure in {"main", "parent"} else 1)
    assert receipt["promotion_authorization"] == "NONE"
    if failure == "commit":
        assert receipt["prior_publication_status"] == "COMMIT_REQUESTED_OUTCOME_UNKNOWN"
        assert receipt["mutation_count"] is None and "huggingface_commit" not in receipt
    elif failure in {"weight", "public"}:
        assert receipt["huggingface_commit"] == UPLOADED


def test_main_changed_preflight_has_no_provider_access(publisher, source, actions, provider, tmp_path):
    source.main = "d" * 40
    code, receipt = run(publisher, tmp_path)
    assert code == 1 and receipt["refusal_code"] == "CANONICAL_MAIN_CHANGED" and provider.calls == []


def test_main_rechecked_immediately_before_mutation(publisher, source, actions, provider, tmp_path):
    provider.on_first_read = lambda: setattr(source, "main", "d" * 40)
    code, receipt = run(publisher, tmp_path)
    assert code == 1 and receipt["phase"] == "PRE_MUTATION_SOURCE_CHECK" and provider.writes == []


def test_dirty_source_change_after_capture_does_not_change_payload(publisher, source, actions, provider, tmp_path):
    provider.on_first_read = lambda: setattr(source, "data", b"dirty file bytes never used")
    code, _ = run(publisher, tmp_path)
    assert code == 0 and provider.writes == [(PARENT, CARD)]


def test_missing_hf_token_never_constructs_provider(publisher, source, actions, provider, monkeypatch, tmp_path):
    monkeypatch.delenv("HF_TOKEN")
    code, receipt = run(publisher, tmp_path)
    assert code == 1 and receipt["refusal_code"] == "HF_AUTHORITY_MISSING" and provider.calls == []


def test_changed_hf_parent_rejected_without_mutation(publisher, source, actions, provider, tmp_path):
    provider.current_parent = "d" * 40
    code, receipt = run(publisher, tmp_path)
    assert code == 1 and receipt["refusal_code"] == "HF_PARENT_CHANGED" and provider.writes == []


@pytest.mark.parametrize("failure,phase,known", [("commit", "README_COMMIT", False),
                                                ("metadata", "IMMUTABLE_TREE_READBACK", True),
                                                ("auth", "AUTHENTICATED_CARD_READBACK", True),
                                                ("public", "PUBLIC_CARD_READBACK", True)])
def test_failure_receipt_redacts_secrets_retains_phase_and_returned_commit(
        publisher, source, actions, provider, tmp_path, capsys, failure, phase, known):
    provider.failure = failure
    code, receipt = run(publisher, tmp_path)
    assert code == 1 and receipt["publication_status"] == "FAILED" and receipt["phase"] == phase
    assert receipt["mutation_attempts"] == 1
    assert ("huggingface_commit" in receipt) is known
    assert receipt["mutation_count"] == (1 if known else None)
    assert receipt["prior_publication_status"] == ("UPLOADED_NOT_YET_VERIFIED" if known else "COMMIT_REQUESTED_OUTCOME_UNKNOWN")
    captured = capsys.readouterr()
    assert TOKEN not in json.dumps(receipt) + captured.out + captured.err
    records = journal_records(tmp_path)
    assert records[-1]["publication_status"] == "FAILED" and records[-1]["phase"] == phase
    assert ("huggingface_commit" in records[-1]) is known
    if known:
        assert records[-2]["publication_status"] == "UPLOADED_NOT_YET_VERIFIED"
        assert records[-2]["huggingface_commit"] == UPLOADED
    else:
        assert records[-2]["publication_status"] == "COMMIT_REQUESTED_OUTCOME_UNKNOWN"
    assert TOKEN not in json.dumps(records)


def test_invalid_returned_commit_never_claimed_as_verified(publisher, source, actions, provider, tmp_path):
    provider.returned = "not-a-commit"
    code, receipt = run(publisher, tmp_path)
    assert code == 1 and receipt["refusal_code"] == "RETURNED_COMMIT_ID_INVALID"
    assert receipt["mutation_count"] == 1 and "huggingface_commit" not in receipt


@pytest.mark.parametrize("change", ["blob", "size", "lfs_sha", "lfs_size", "pointer_size", "add", "delete", "readme"])
def test_complete_other_file_identity_and_set_unchanged(publisher, source, actions, provider, tmp_path, change):
    def mutate(entries):
        if change == "blob":
            entries[1].blob_id = "0" * 40
        elif change == "size":
            entries[1].size += 1
        elif change.startswith("lfs_"):
            key = change.removeprefix("lfs_")
            entries[1].lfs["sha256" if key == "sha" else key] = "0" * 64 if key == "sha" else 999
        elif change == "pointer_size":
            entries[1].lfs["pointer_size"] += 1
        elif change == "add":
            entries.append(SimpleNamespace(rfilename="new.txt", blob_id="0" * 40, size=0, lfs=None))
        elif change == "delete":
            entries.pop()
        else:
            entries[0].size += 1
    provider.changed_metadata = mutate
    code, receipt = run(publisher, tmp_path)
    assert code == 1 and receipt["phase"] == "IMMUTABLE_TREE_READBACK"
    assert receipt["huggingface_commit"] == UPLOADED and receipt["publication_status"] == "FAILED"


def test_concurrent_head_change_after_successful_immutable_readback_fails(publisher, source, actions, provider, tmp_path):
    provider.final_head = "d" * 40
    code, receipt = run(publisher, tmp_path)
    assert code == 1 and receipt["refusal_code"] == "HF_HEAD_CHANGED_AFTER_READBACK"
    assert receipt["phase"] == "CURRENT_HEAD_READBACK" and receipt["huggingface_commit"] == UPLOADED


@pytest.mark.parametrize("verified,reason,sha", [(False, "valid", SOURCE), (True, "unsigned", SOURCE),
                                                (True, "valid", "d" * 40), (1, "valid", SOURCE)])
def test_exact_current_signature_provider_attestation(publisher, monkeypatch, verified, reason, sha):
    monkeypatch.setenv("GITHUB_TOKEN", TOKEN)
    calls = []
    def fetch(url, **kwargs):
        calls.append((url, kwargs))
        return json.dumps({"sha": sha, "commit": {"verification": {"verified": verified, "reason": reason}}}).encode()
    monkeypatch.setattr(publisher, "fetch_bytes", fetch)
    with pytest.raises(publisher.Refusal, match="SOURCE_SIGNATURE_NOT_VERIFIED"):
        publisher.signature_readback(SOURCE)
    assert calls[0][0] == "https://api.github.com/repos/" + publisher.REPOSITORY + "/commits/" + SOURCE
    assert calls[0][1]["host"] == "api.github.com" and calls[0][1]["limit"] == publisher.MAX_JSON_BYTES
    assert calls[0][1]["headers"]["Authorization"] == "Bearer " + TOKEN


def test_valid_signature_readback_succeeds_without_trust_store_mutation(publisher, monkeypatch):
    monkeypatch.setattr(publisher, "fetch_bytes", lambda *a, **k: json.dumps(
        {"sha": SOURCE, "commit": {"verification": {"verified": True, "reason": "valid"}}}).encode())
    publisher.signature_readback(SOURCE)


def test_git_subprocess_has_deadline_and_never_inherits_stderr(publisher, monkeypatch):
    calls = []
    def output(argv, **kwargs):
        calls.append((argv, kwargs))
        return b"immutable bytes"
    monkeypatch.setattr(publisher.subprocess, "check_output", output)
    assert publisher.git("cat-file", "blob", "d" * 40) == b"immutable bytes"
    assert calls[0][1] == {"stderr": publisher.subprocess.PIPE, "timeout": 20}


@pytest.mark.parametrize("redirect", ["https://cdn.example/README.md", "http://huggingface.co/README.md",
                                     "https://user@huggingface.co/README.md", "https://huggingface.co:444/README.md"])
def test_authenticated_redirect_never_forwards_to_other_origin(publisher, redirect):
    request = Request("https://huggingface.co/model/raw/commit/README.md", headers={"Authorization": "Bearer " + TOKEN})
    with pytest.raises(publisher.Refusal, match="CROSS_ORIGIN_READBACK_REDIRECT"):
        publisher.SameOriginRedirect().redirect_request(request, None, 302, "redirect", {}, redirect)


@pytest.mark.parametrize("failure", ["host", "final_host", "status", "length", "chunks", "time"])
def test_http_readback_is_origin_byte_and_time_bounded(publisher, monkeypatch, failure):
    url = "https://huggingface.co/repo/raw/commit/README.md"
    class Response:
        status = 500 if failure == "status" else 200
        headers = {"Content-Length": "5"} if failure == "length" else {}
        chunks = [b"12345", b""] if failure == "chunks" else [b"ok", b""]
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def geturl(self):
            return "https://evil.example/x" if failure == "final_host" else url
        def read1(self, size):
            assert size == 8192
            return self.chunks.pop(0)
    response = Response()
    calls = []
    def open_request(request, timeout):
        assert timeout == 5
        calls.append(request)
        return response
    monkeypatch.setattr(publisher, "build_opener", lambda *a: SimpleNamespace(open=open_request))
    ticks = iter([0, 31]) if failure == "time" else iter([0, 0, 0])
    monkeypatch.setattr(publisher.time, "monotonic", lambda: next(ticks))
    with pytest.raises(publisher.Refusal):
        publisher.fetch_bytes("https://evil.example/x" if failure == "host" else url,
                              host="huggingface.co", headers={}, limit=4)
    if failure == "host":
        assert calls == []


def test_raw_public_request_explicitly_disables_cached_and_environment_auth(publisher, monkeypatch):
    utils = ModuleType("huggingface_hub.utils")
    header_calls, fetch_calls = [], []
    def headers(*, token):
        header_calls.append(token)
        return {} if token is False else {"Authorization": "Bearer " + token}
    utils.build_hf_headers = headers
    monkeypatch.setitem(sys.modules, "huggingface_hub.utils", utils)
    monkeypatch.setenv("HF_TOKEN", TOKEN)
    monkeypatch.setattr(publisher, "fetch_bytes", lambda url, **kwargs: fetch_calls.append((url, kwargs)) or CARD)
    assert publisher.read_card(publisher.TARGETS["study5"][1], UPLOADED, token=False) == CARD
    assert header_calls == [False] and "Authorization" not in fetch_calls[0][1]["headers"]
    assert fetch_calls[0][0].endswith("/raw/" + UPLOADED + "/README.md")
    assert fetch_calls[0][1]["host"] == "huggingface.co" and fetch_calls[0][1]["limit"] == publisher.MAX_CARD_BYTES


@pytest.mark.parametrize("problem", ["private", "gated", "missing_metadata", "missing_blob", "bool_size", "missing_lfs",
                                     "duplicate", "traversal", "readme_lfs", "wrong_revision", "unknown_gated"])
def test_incomplete_or_unsafe_metadata_never_counts_as_full_proof(publisher, problem):
    entries = [SimpleNamespace(rfilename="README.md", blob_id=git_blob(CARD), size=len(CARD), lfs=None),
               SimpleNamespace(rfilename="weights", blob_id="d" * 40, size=10,
                               lfs={"sha256": "e" * 64, "size": 10, "pointer_size": 133})]
    info = SimpleNamespace(sha=PARENT, private=False, gated=False, siblings=entries)
    if problem == "private":
        info.private = True
    elif problem == "gated":
        info.gated = "auto"
    elif problem == "missing_metadata":
        info.siblings = None
    elif problem == "missing_blob":
        entries[1].blob_id = None
    elif problem == "bool_size":
        entries[1].size = True
    elif problem == "missing_lfs":
        del entries[1].lfs["pointer_size"]
    elif problem == "duplicate":
        entries.append(entries[0])
    elif problem == "traversal":
        entries[1].rfilename = "../weights"
    elif problem == "readme_lfs":
        entries[0].lfs = entries[1].lfs
    elif problem == "unknown_gated":
        del info.gated
    else:
        info.sha = UPLOADED
    api = SimpleNamespace(repo_info=lambda *a, **k: info)
    with pytest.raises(publisher.Refusal):
        publisher.snapshot(api, publisher.TARGETS["study5"][1], PARENT)


def test_workflow_one_manual_serialized_main_only_writer():
    text = (ROOT / ".github/workflows/publish-hf-card.yml").read_text(encoding="utf-8")
    assert "options: [retrain, study5, root_lora]" in text and "default: false" in text
    assert "huggingface_hub==1.33.0" in text and "cancel-in-progress: false" in text
    assert 'test "$GITHUB_REF" = "refs/heads/main"' in text and 'test "$GITHUB_EVENT_NAME" = "workflow_dispatch"' in text
    assert "if: ${{ always() }}" in text and "if-no-files-found: error" in text
    assert "card-publication-receipt.json.journal.jsonl" in text
    assert "persist-credentials: false" in text and "contents: read" in text
    assert "repo_id:" not in text and "path:" not in text.split("Retain the success or failure receipt")[0]
    assert "parent_commit" not in text  # CAS lives only in the tested helper.
    assert "upload_folder" not in text and "create_repo" not in text and "set -" not in text


@pytest.mark.parametrize("status,expected", [(400, "BAD_REQUEST"), (401, "UNAUTHORIZED"),
    (403, "FORBIDDEN"), (404, "NOT_FOUND"), (409, "CONFLICT"), (429, "RATE_LIMITED"),
    (503, "SERVER_ERROR"), (418, "HTTP_ERROR"), (True, "STATUS_UNAVAILABLE"),
    (99, "STATUS_UNAVAILABLE"), (600, "STATUS_UNAVAILABLE"), ("401", "STATUS_UNAVAILABLE"),
    (None, "STATUS_UNAVAILABLE")])
def test_failure_metadata_only_retains_fixed_categories(publisher, status, expected):
    class HfHubHTTPError(RuntimeError):
        pass
    error = HfHubHTTPError(TOKEN + " https://provider.example/?token=" + TOKEN)
    error.response = SimpleNamespace(status_code=status)
    metadata = publisher.failure_metadata(error)
    assert metadata["provider_failure_code"] == expected
    assert metadata["provider_http_status"] == (None if expected == "STATUS_UNAVAILABLE" else status)
    assert metadata["error_type"] == "HfHubHTTPError"
    assert TOKEN not in json.dumps(metadata) and "provider.example" not in json.dumps(metadata)


def test_failure_metadata_redacts_arbitrary_exception_class_and_url(publisher):
    from urllib.error import HTTPError
    error = HTTPError("https://provider.example/?token=" + TOKEN, 401, TOKEN, {}, None)
    assert publisher.failure_metadata(error) == {
        "error_type": "HTTPError", "provider_http_status": 401, "provider_failure_code": "UNAUTHORIZED"}
    unknown = type(TOKEN, (Exception,), {})(TOKEN)
    assert publisher.failure_metadata(unknown)["error_type"] == "UNCLASSIFIED_EXCEPTION"
    receipt = {"publication_status": "FAILED"}
    publisher.record_failure(receipt, unknown)
    assert receipt["checkpoint_error_type"] == "UNCLASSIFIED_EXCEPTION"
    assert TOKEN not in json.dumps(receipt)


@pytest.mark.parametrize("failed_revision,phase", [(None, "PARENT_HEAD_METADATA"),
    (PARENT, "PARENT_IMMUTABLE_FILE_METADATA")])
def test_parent_metadata_error_is_typed_before_zero_write(
        publisher, source, actions, provider, monkeypatch, tmp_path, capsys, failed_revision, phase):
    class BadRequestError(RuntimeError):
        pass
    api = sys.modules["huggingface_hub"].HfApi
    actual = api.repo_info
    def repo_info(self, *args, **kwargs):
        if kwargs.get("revision") == failed_revision:
            error = BadRequestError(TOKEN + " https://provider.example/private-request")
            error.response = SimpleNamespace(status_code=400)
            raise error
        return actual(self, *args, **kwargs)
    monkeypatch.setattr(api, "repo_info", repo_info)
    code, receipt = run(publisher, tmp_path)
    assert code == 1 and receipt["phase"] == phase
    assert receipt["error_type"] == "BadRequestError" and receipt["provider_http_status"] == 400
    assert receipt["provider_failure_code"] == "BAD_REQUEST"
    assert receipt["mutation_count"] == receipt["mutation_attempts"] == 0
    assert provider.writes == provider.reads == []
    captured = capsys.readouterr()
    output = json.dumps(receipt) + json.dumps(journal_records(tmp_path)) + captured.out + captured.err
    assert TOKEN not in output and "provider.example" not in output


@pytest.fixture
def diagnostic_provider(publisher, monkeypatch):
    sdk = ModuleType("huggingface_hub")
    primary, fallback = TOKEN + "-primary", TOKEN + "-fallback"
    monkeypatch.setenv("HF_PROVIDER_ORG_TOKEN", primary)
    monkeypatch.setenv("HF_PROVIDER_FALLBACK_TOKEN", fallback)
    state = SimpleNamespace(calls=[], failed_operation=None, head=PARENT,
                            who={"name": "fixture-account", "orgs": [{"name": "SZLHOLDINGS", "roleInOrg": "admin"}],
                                 "auth": {"accessToken": {"role": "write"}}})
    class HfHubHTTPError(RuntimeError):
        pass
    class HfApi:
        def __init__(self, *, endpoint, token):
            assert endpoint == "https://huggingface.co" and token in (primary, fallback)
            self.label = "org_primary" if token == primary else "fallback"
        def check(self, operation):
            state.calls.append((self.label, operation))
            if self.label == "org_primary" and operation == state.failed_operation:
                error = HfHubHTTPError(TOKEN + " https://provider.example/?secret=" + TOKEN)
                error.response = SimpleNamespace(status_code=401)
                raise error
        def whoami(self):
            self.check("identity")
            return state.who
        def repo_info(self, repo, *, repo_type, timeout, revision=None, files_metadata=False):
            assert repo == publisher.TARGETS["study5"][1] and repo_type == "model" and timeout == 20
            if revision is None:
                assert files_metadata is False
                self.check("current_metadata")
                return SimpleNamespace(sha=state.head)
            assert revision == PARENT and files_metadata is True
            self.check("immutable_file_metadata")
            return SimpleNamespace(sha=PARENT, private=False, gated=False, siblings=[
                SimpleNamespace(rfilename="README.md", blob_id=git_blob(CARD), size=len(CARD), lfs=None)])
        def create_commit(self, **kwargs):
            raise AssertionError("A read-only diagnostic must never call a mutation API")
    sdk.HfApi = HfApi
    monkeypatch.setitem(sys.modules, "huggingface_hub", sdk)
    monkeypatch.setattr(publisher, "read_card", lambda *a, **k: pytest.fail("Diagnostic must not read artifact bytes"))
    return state


def run_diagnostic(publisher, tmp_path):
    path = tmp_path / "new-receipt.json"
    code = publisher.main(["--target", "study5", "--source-commit", SOURCE,
        "--expected-parent", PARENT, "--receipt", str(path), "--diagnose"])
    return code, json.loads(path.read_text(encoding="utf-8"))


def test_diagnostic_compares_both_entries_without_write_or_promotion(
        publisher, source, actions, diagnostic_provider, tmp_path):
    code, receipt = run_diagnostic(publisher, tmp_path)
    assert code == 0 and receipt["publication_status"] == "DIAGNOSTIC_ONLY" and receipt["phase"] == "COMPLETE"
    assert receipt["mutation_count"] == receipt["mutation_attempts"] == 0
    assert receipt["model_runtime"] == "NOT_EVALUATED" and receipt["promotion_authorization"] == "NONE"
    assert [row["status"] for row in receipt["provider_diagnostics"]] == ["VERIFIED_READ_ONLY"] * 2
    assert len(diagnostic_provider.calls) == 6
    for row in receipt["provider_diagnostics"]:
        identity = row["operations"][0]
        assert identity["account"] == "fixture-account" and identity["organization_role"] == "admin"
        assert identity["identity_metadata"] == "OBSERVED"
        assert identity["token_role"] == "write"
        assert row["operations"][2]["file_count"] == 1
    assert TOKEN not in json.dumps(receipt) + json.dumps(journal_records(tmp_path))


@pytest.mark.parametrize("operation", ["identity", "current_metadata", "immutable_file_metadata"])
def test_diagnostic_failure_retains_fallback_probe_but_stays_red_and_secret_free(
        publisher, source, actions, diagnostic_provider, tmp_path, capsys, operation):
    diagnostic_provider.failed_operation = operation
    code, receipt = run_diagnostic(publisher, tmp_path)
    assert code == 1 and receipt["publication_status"] == "FAILED"
    assert receipt["prior_publication_status"] == "DIAGNOSTIC_ONLY"
    assert receipt["refusal_code"] == "PROVIDER_DIAGNOSTIC_FAILED"
    assert receipt["mutation_count"] == receipt["mutation_attempts"] == 0
    primary, fallback = receipt["provider_diagnostics"]
    assert primary["status"] == "PROVIDER_FAILURE" and fallback["status"] == "VERIFIED_READ_ONLY"
    failed = next(item for item in primary["operations"] if item["operation"] == operation)
    assert failed["provider_http_status"] == 401 and failed["provider_failure_code"] == "UNAUTHORIZED"
    assert failed["error_type"] == "HfHubHTTPError" and len(diagnostic_provider.calls) == 6
    captured = capsys.readouterr()
    output = json.dumps(receipt) + json.dumps(journal_records(tmp_path)) + captured.out + captured.err
    assert TOKEN not in output and "provider.example" not in output


def test_diagnostic_missing_primary_does_not_silently_select_fallback(
        publisher, source, actions, diagnostic_provider, monkeypatch, tmp_path):
    monkeypatch.delenv("HF_PROVIDER_ORG_TOKEN")
    code, receipt = run_diagnostic(publisher, tmp_path)
    assert code == 1 and receipt["mutation_count"] == 0
    assert receipt["provider_diagnostics"][0]["status"] == "CREDENTIAL_MISSING"
    assert receipt["provider_diagnostics"][1]["status"] == "VERIFIED_READ_ONLY"
    assert len(diagnostic_provider.calls) == 3


def test_diagnostic_nullable_token_metadata_and_unsafe_identity_are_redacted(
        publisher, source, actions, diagnostic_provider, tmp_path):
    diagnostic_provider.who = {"name": TOKEN + " https://provider.example", "orgs": [],
                               "auth": {"accessToken": None}}
    code, receipt = run_diagnostic(publisher, tmp_path)
    assert code == 0
    for row in receipt["provider_diagnostics"]:
        identity = row["operations"][0]
        assert identity["account"] is identity["organization_role"] is identity["token_role"] is None
        assert identity["identity_metadata"] == "UNKNOWN"
    assert TOKEN not in json.dumps(receipt) and "provider.example" not in json.dumps(receipt)


def test_diagnostic_changed_parent_fails_with_zero_writes(
        publisher, source, actions, diagnostic_provider, tmp_path):
    diagnostic_provider.head = UPLOADED
    code, receipt = run_diagnostic(publisher, tmp_path)
    assert code == 1 and receipt["mutation_count"] == receipt["mutation_attempts"] == 0
    for row in receipt["provider_diagnostics"]:
        assert row["operations"][1]["refusal_code"] == "HF_PARENT_CHANGED"


@pytest.mark.parametrize("variable,prefix,suffix", [
    ("HF_PROVIDER_ORG_TOKEN", "", ""), ("HF_PROVIDER_FALLBACK_TOKEN", "", ""),
    ("HF_TOKEN", "", ""), ("HF_PROVIDER_ORG_TOKEN", "p_", "_s"),
    ("HF_PROVIDER_FALLBACK_TOKEN", "p_", "_s"), ("HF_TOKEN", "p_", "_s")])
def test_regex_valid_identity_credential_echo_is_unknown_and_never_retained(
        publisher, source, actions, diagnostic_provider, tmp_path, capsys, variable, prefix, suffix):
    credential = publisher.os.environ[variable]
    account = prefix + credential + suffix
    assert publisher.re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", account)
    diagnostic_provider.who["name"] = account
    code, receipt = run_diagnostic(publisher, tmp_path)
    assert code == 0 and receipt["mutation_count"] == receipt["mutation_attempts"] == 0
    for row in receipt["provider_diagnostics"]:
        identity = row["operations"][0]
        assert identity["identity_metadata"] == "UNKNOWN"
        assert identity["account"] is identity["organization_role"] is identity["token_role"] is None
    captured = capsys.readouterr()
    output = json.dumps(receipt) + json.dumps(journal_records(tmp_path)) + captured.out + captured.err
    assert credential not in output and account not in output and TOKEN not in output


def test_diagnostic_requires_actions_before_source_or_provider(
        publisher, source, diagnostic_provider, monkeypatch, tmp_path):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    code, receipt = run_diagnostic(publisher, tmp_path)
    assert code == 1 and receipt["refusal_code"] == "ACTIONS_REQUIRED"
    assert source.calls == diagnostic_provider.calls == []


def test_diagnose_and_publish_are_mutually_exclusive_before_io(publisher, tmp_path):
    path = tmp_path / "new-receipt.json"
    with pytest.raises(SystemExit) as failure:
        publisher.main(["--target", "study5", "--source-commit", SOURCE, "--expected-parent", PARENT,
                        "--receipt", str(path), "--publish", "--diagnose"])
    assert failure.value.code == 2 and not path.exists()


def test_workflow_keeps_publishing_priority_and_read_only_diagnostics_explicit():
    text = (ROOT / ".github/workflows/publish-hf-card.yml").read_text(encoding="utf-8")
    assert "HF_TOKEN: ${{ secrets.HF_ORG_TOKEN || secrets.HF_TOKEN }}" in text
    assert "HF_PROVIDER_ORG_TOKEN: ${{ secrets.HF_ORG_TOKEN }}" in text
    assert "HF_PROVIDER_FALLBACK_TOKEN: ${{ secrets.HF_TOKEN }}" in text
    assert 'if [ "$DIAGNOSE_REQUESTED" = "true" ]; then args+=(--diagnose); fi' in text

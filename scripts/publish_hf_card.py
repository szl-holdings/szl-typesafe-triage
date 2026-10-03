# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Plan or publish one canonical card; never train, load, or publish weights."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import time
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

REPOSITORY = "szl-holdings/szl-typesafe-triage"
ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    "retrain": ("hf/szl-triage-retrain/README.md", "SZLHOLDINGS/szl-triage-retrain"),
    "study5": ("out/publish/triage-lora-study5/README.md",
               "SZLHOLDINGS/szl-triage-qwen3.5-0.8b-lora-study5"),
}
MAX_CARD_BYTES = 128 * 1024
MAX_JSON_BYTES = 256 * 1024


class Refusal(ValueError):
    """Fixed non-secret refusal code, safe for receipts."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise Refusal(code)


def full_sha(value: str) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], stderr=subprocess.PIPE, timeout=20)


def check_main(commit: str) -> None:
    rows = git("ls-remote", "https://github.com/" + REPOSITORY + ".git",
               "refs/heads/main").decode("ascii").splitlines()
    require(rows == [commit + "\trefs/heads/main"], "CANONICAL_MAIN_CHANGED")


def check_actions(commit: str) -> None:
    require(os.environ.get("GITHUB_ACTIONS") == "true", "ACTIONS_REQUIRED")
    require(os.environ.get("GITHUB_REPOSITORY") == REPOSITORY, "NONCANONICAL_REPOSITORY")
    require(os.environ.get("GITHUB_REF") == "refs/heads/main", "MAIN_REF_REQUIRED")
    require(os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch", "MANUAL_DISPATCH_REQUIRED")
    require(os.environ.get("GITHUB_SHA") == commit, "DISPATCH_SOURCE_MISMATCH")


class SameOriginRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        before, after = urlparse(req.full_url), urlparse(newurl)
        require(after.scheme == "https" and after.hostname == before.hostname
                and after.port in (None, 443) and after.username is None,
                "CROSS_ORIGIN_READBACK_REDIRECT")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_bytes(url: str, *, host: str, headers: dict, limit: int) -> bytes:
    parsed = urlparse(url)
    require(parsed.scheme == "https" and parsed.hostname == host
            and parsed.port in (None, 443) and parsed.username is None,
            "NONCANONICAL_READBACK_HOST")
    started = time.monotonic()
    with build_opener(SameOriginRedirect()).open(Request(url, headers=headers), timeout=5) as response:
        final = urlparse(response.geturl())
        require(final.scheme == "https" and final.hostname == host
                and final.port in (None, 443) and final.username is None,
                "NONCANONICAL_FINAL_READBACK_HOST")
        require(response.status == 200, "READBACK_HTTP_STATUS")
        length = response.headers.get("Content-Length")
        if length is not None:
            require(length.isdecimal() and int(length) <= limit, "READBACK_SIZE_LIMIT")
        chunks, size = [], 0
        while True:
            require(time.monotonic() - started <= 30, "READBACK_TIME_LIMIT")
            chunk = response.read1(8192)
            if not chunk:
                break
            size += len(chunk)
            require(size <= limit, "READBACK_SIZE_LIMIT")
            chunks.append(chunk)
    return b"".join(chunks)


def signature_readback(commit: str) -> None:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    raw = fetch_bytes("https://api.github.com/repos/" + REPOSITORY + "/commits/" + commit,
                      host="api.github.com", headers=headers, limit=MAX_JSON_BYTES)
    data = json.loads(raw)
    verification = data.get("commit", {}).get("verification", {})
    require(data.get("sha") == commit and verification.get("verified") is True
            and verification.get("reason") == "valid", "SOURCE_SIGNATURE_NOT_VERIFIED")


def capture_source(target: str, commit: str) -> tuple[bytes, str]:
    require(target in TARGETS and full_sha(commit), "INVALID_SOURCE_SELECTION")
    check_main(commit)
    signature_readback(commit)
    path, _ = TARGETS[target]
    row = git("ls-tree", commit, "--", path).decode("utf-8").rstrip("\n")
    require("\t" in row, "SOURCE_CARD_MISSING")
    metadata, observed_path = row.split("\t", 1)
    fields = metadata.split()
    require(len(fields) == 3 and fields[0] == "100644" and fields[1] == "blob"
            and full_sha(fields[2]) and observed_path == path, "SOURCE_CARD_NOT_REGULAR")
    size_text = git("cat-file", "-s", fields[2]).strip()
    require(size_text.isdigit() and 0 < int(size_text) <= MAX_CARD_BYTES,
            "SOURCE_CARD_SIZE_LIMIT")
    size = int(size_text)
    data = git("cat-file", "blob", fields[2])
    require(len(data) == size, "SOURCE_CARD_SIZE_MISMATCH")
    actual_blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    require(actual_blob == fields[2], "SOURCE_GIT_BLOB_MISMATCH")
    text = data.decode("utf-8")
    require(re.match(r"^---\nlicense: [a-z0-9.-]+\n", text) is not None,
            "CARD_LICENSE_BOUNDARY_MISSING")
    specific = (("**BLOCKED — 11/12**", "Inline inference example withdrawn",
                 "No fresh inference was performed for this card correction",
                 "earlier 66-row gate", "113-row study") if target == "study5"
                else ("Status: training scripts only", "Claim boundary",
                      "Publication of scripts is not publication of a model"))
    require(all(needle in text for needle in ("NOT_PROMOTABLE",) + specific),
            "CARD_CLAIM_BOUNDARY_MISSING")
    return data, fields[2]


def read_card(repo: str, revision: str, *, token: str | bool) -> bytes:
    from huggingface_hub.utils import build_hf_headers
    require(repo in {target[1] for target in TARGETS.values()} and full_sha(revision),
            "INVALID_READBACK_SELECTION")
    url = "https://huggingface.co/" + repo + "/raw/" + revision + "/README.md"
    return fetch_bytes(url, host="huggingface.co", headers=build_hf_headers(token=token),
                       limit=MAX_CARD_BYTES)


def _integer(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _field(value, name):
    return value.get(name) if isinstance(value, dict) else getattr(value, name, None)


def snapshot(api, repo: str, revision: str) -> dict:
    info = api.repo_info(repo, repo_type="model", revision=revision,
                         files_metadata=True, timeout=20)
    require(info.sha == revision, "IMMUTABLE_METADATA_REVISION_MISMATCH")
    require(info.private is False and getattr(info, "gated", None) is False,
            "TARGET_NOT_PUBLIC_UNGATED")
    require(isinstance(info.siblings, list) and 0 < len(info.siblings) <= 10000,
            "FILE_METADATA_UNAVAILABLE")
    result = {}
    for entry in info.siblings:
        name = entry.rfilename
        require(isinstance(name, str) and bool(name) and "\\" not in name
                and not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts
                and name not in result, "FILE_METADATA_PATH_INVALID")
        require(full_sha(entry.blob_id) and _integer(entry.size), "FILE_IDENTITY_UNAVAILABLE")
        lfs = None
        if entry.lfs is not None:
            lfs = {key: _field(entry.lfs, key) for key in ("sha256", "size", "pointer_size")}
            require(isinstance(lfs["sha256"], str)
                    and re.fullmatch(r"[0-9a-f]{64}", lfs["sha256"]) is not None
                    and _integer(lfs["size"]) and _integer(lfs["pointer_size"]),
                    "LFS_IDENTITY_UNAVAILABLE")
        result[name] = {"blob": entry.blob_id, "size": entry.size, "lfs": lfs}
    require("README.md" in result and result["README.md"]["lfs"] is None,
            "PARENT_CARD_IDENTITY_UNAVAILABLE")
    return result


def snapshot_digest(tree: dict) -> str:
    return digest(json.dumps(tree, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def append_checkpoint(handle, receipt: dict) -> None:
    record = dict(receipt, checkpoint_utc=datetime.now(timezone.utc).isoformat(),
                  journal_schema="szl.model-card-publication-journal/v1")
    handle.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
    handle.flush()
    os.fsync(handle.fileno())


def failure_metadata(exc: Exception) -> dict:
    """Retain only fixed exception categories and a validated HTTP status."""
    known_types = {
        "BadRequestError", "HfHubHTTPError", "RepositoryNotFoundError",
        "RevisionNotFoundError", "GatedRepoError", "HTTPError", "ReadTimeout",
        "ConnectTimeout", "ConnectError", "ReadError", "RemoteProtocolError",
        "LocalProtocolError", "Refusal", "TimeoutError", "ValueError", "OSError",
        "RuntimeError", "AttributeError", "TypeError", "FileExistsError",
        "FileNotFoundError", "CalledProcessError", "UnicodeDecodeError",
        "ModuleNotFoundError", "ImportError", "JSONDecodeError",
    }
    kind = type(exc).__name__
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status is None:
        status = getattr(exc, "code", None)
    if not isinstance(status, int) or isinstance(status, bool) or not 100 <= status <= 599:
        status = None
    code = {400: "BAD_REQUEST", 401: "UNAUTHORIZED", 403: "FORBIDDEN",
            404: "NOT_FOUND", 409: "CONFLICT", 429: "RATE_LIMITED"}.get(status)
    if code is None:
        code = "STATUS_UNAVAILABLE" if status is None else ("SERVER_ERROR" if status >= 500 else "HTTP_ERROR")
    return {"error_type": kind if kind in known_types else "UNCLASSIFIED_EXCEPTION",
            "provider_http_status": status, "provider_failure_code": code}


def record_failure(receipt: dict, exc: Exception) -> None:
    if receipt["publication_status"] == "FAILED":
        receipt["checkpoint_error_type"] = failure_metadata(exc)["error_type"]
        return
    receipt.update(prior_publication_status=receipt["publication_status"],
                   publication_status="FAILED", **failure_metadata(exc))
    if isinstance(exc, Refusal):
        receipt["refusal_code"] = str(exc)


def publish_card(data: bytes, receipt: dict, *, checkpoint=None) -> None:
    check_actions(receipt["source_commit"])
    checkpoint = checkpoint or (lambda current: None)
    from huggingface_hub import CommitOperationAdd, HfApi
    token = os.environ.get("HF_TOKEN")
    require(bool(token), "HF_AUTHORITY_MISSING")
    api = HfApi(endpoint="https://huggingface.co", token=token)
    repo, parent = receipt["repo_id"], receipt["expected_parent"]
    receipt["phase"] = "PARENT_HEAD_METADATA"
    current = api.repo_info(repo, repo_type="model", timeout=20)
    require(current.sha == parent, "HF_PARENT_CHANGED")
    receipt["phase"] = "PARENT_IMMUTABLE_FILE_METADATA"
    before = snapshot(api, repo, parent)
    receipt["phase"] = "PARENT_CARD_READBACK"
    old = read_card(repo, parent, token=token)
    require(len(old) == before["README.md"]["size"] and
            hashlib.sha1(b"blob " + str(len(old)).encode() + b"\0" + old).hexdigest()
            == before["README.md"]["blob"], "PARENT_CARD_METADATA_MISMATCH")
    receipt.update({"parent_tree_sha256": snapshot_digest(before),
                    "parent_file_count": len(before), "prior_card_sha256": digest(old)})
    receipt["phase"] = "PRE_MUTATION_SOURCE_CHECK"
    check_actions(receipt["source_commit"])
    check_main(receipt["source_commit"])
    signature_readback(receipt["source_commit"])
    if old == data:
        revision = parent
        receipt.update({"publication_status": "NO_OP_NOT_YET_VERIFIED",
                        "mutation_count": 0, "changed_paths": []})
        checkpoint(receipt)
    else:
        receipt["phase"] = "README_COMMIT"
        receipt.update({"publication_status": "COMMIT_REQUESTED_OUTCOME_UNKNOWN",
                        "mutation_attempts": 1, "mutation_count": None})
        try:
            checkpoint(receipt)
        except Exception:
            receipt.update(publication_status="PRE_COMMIT_CHECKPOINT_FAILED",
                           mutation_attempts=0, mutation_count=0)
            raise
        result = api.create_commit(
            repo_id=repo, repo_type="model", parent_commit=parent,
            operations=[CommitOperationAdd(path_in_repo="README.md", path_or_fileobj=data)],
            commit_message="Publish canonical card from " + REPOSITORY + "@" + receipt["source_commit"])
        revision = getattr(result, "oid", None)
        receipt.update({"publication_status": "UPLOADED_NOT_YET_VERIFIED", "mutation_count": 1})
        if full_sha(revision):
            receipt["huggingface_commit"] = revision
        require(full_sha(revision), "RETURNED_COMMIT_ID_INVALID")
        checkpoint(receipt)
    receipt["verified_revision"] = revision
    receipt["phase"] = "IMMUTABLE_TREE_READBACK"
    after = snapshot(api, repo, revision)
    require(set(after) == set(before), "REMOTE_FILE_SET_CHANGED")
    changed = sorted(name for name in before if before[name] != after[name])
    require(changed == ([] if old == data else ["README.md"]), "NONCARD_FILE_CHANGED")
    new_blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    require(after["README.md"] == {"blob": new_blob, "size": len(data), "lfs": None},
            "RESULT_CARD_METADATA_MISMATCH")
    receipt["phase"] = "AUTHENTICATED_CARD_READBACK"
    require(read_card(repo, revision, token=token) == data, "AUTHENTICATED_BYTE_MISMATCH")
    receipt["phase"] = "PUBLIC_CARD_READBACK"
    require(read_card(repo, revision, token=False) == data, "PUBLIC_BYTE_MISMATCH")
    receipt["phase"] = "CURRENT_HEAD_READBACK"
    require(api.repo_info(repo, repo_type="model", timeout=20).sha == revision,
            "HF_HEAD_CHANGED_AFTER_READBACK")
    receipt.update({"publication_status": "VERIFIED_NO_OP" if old == data else "BYTE_PARITY_VERIFIED",
                    "changed_paths": changed, "result_tree_sha256": snapshot_digest(after),
                    "result_file_count": len(after), "authenticated_card_sha256": digest(data),
                    "public_card_sha256": digest(data), "phase": "COMPLETE"})


def diagnose_provider(receipt: dict) -> None:
    """Read both existing credential entries without selecting or changing one."""
    check_actions(receipt["source_commit"])
    from huggingface_hub import HfApi
    receipt.update(phase="PROVIDER_DIAGNOSTICS", publication_status="DIAGNOSTIC_ONLY",
                   provider_diagnostics=[])
    for label, variable in (("org_primary", "HF_PROVIDER_ORG_TOKEN"),
                            ("fallback", "HF_PROVIDER_FALLBACK_TOKEN")):
        token = os.environ.get(variable)
        row = {"credential_label": label, "credential_present": bool(token), "operations": []}
        receipt["provider_diagnostics"].append(row)
        if not token:
            row["status"] = "CREDENTIAL_MISSING"
            continue
        api = HfApi(endpoint="https://huggingface.co", token=token)
        for operation in ("identity", "current_metadata", "immutable_file_metadata"):
            observed = {"operation": operation}
            row["operations"].append(observed)
            try:
                if operation == "identity":
                    who = api.whoami()
                    require(isinstance(who, dict), "IDENTITY_UNAVAILABLE")
                    account = who.get("name")
                    role = next((org.get("roleInOrg") for org in who.get("orgs", [])
                                 if isinstance(org, dict) and org.get("name") == "SZLHOLDINGS"), None)
                    token_role = ((who.get("auth") or {}).get("accessToken") or {}).get("role")
                    observed.update(account=account if isinstance(account, str)
                                    and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", account) else None,
                                    organization_role=role if role in {"admin", "write", "read", "contributor"} else None,
                                    token_role=token_role if token_role in {"read", "write", "fineGrained"} else None)
                elif operation == "current_metadata":
                    info = api.repo_info(receipt["repo_id"], repo_type="model", timeout=20)
                    require(info.sha == receipt["expected_parent"], "HF_PARENT_CHANGED")
                    observed["revision"] = info.sha
                else:
                    tree = snapshot(api, receipt["repo_id"], receipt["expected_parent"])
                    observed.update(revision=receipt["expected_parent"], file_count=len(tree),
                                    tree_sha256=snapshot_digest(tree))
                observed["status"] = "VERIFIED"
            except Exception as exc:
                observed.update(status="FAILED", **failure_metadata(exc))
                if isinstance(exc, Refusal):
                    observed["refusal_code"] = str(exc)
        row["status"] = ("VERIFIED_READ_ONLY" if all(item["status"] == "VERIFIED"
                                                    for item in row["operations"]) else "PROVIDER_FAILURE")
    require(all(row["status"] == "VERIFIED_READ_ONLY" for row in receipt["provider_diagnostics"]),
            "PROVIDER_DIAGNOSTIC_FAILED")
    receipt["phase"] = "COMPLETE"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=sorted(TARGETS), required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--expected-parent", required=True)
    parser.add_argument("--receipt", type=Path, required=True, help="New exclusive output file")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--publish", action="store_true", help="Canonical main Actions dispatch only")
    mode.add_argument("--diagnose", action="store_true", help="Read-only canonical main Actions credential probes")
    args = parser.parse_args(argv)
    receipt = {"schema": "szl.model-card-publication/v1", "source_repository": REPOSITORY,
               "source_commit": args.source_commit, "target": args.target,
               "source_path": TARGETS[args.target][0], "repo_id": TARGETS[args.target][1],
               "expected_parent": args.expected_parent, "publication_status": "NOT_STARTED",
               "phase": "SOURCE_PREFLIGHT", "mutation_count": 0, "mutation_attempts": 0,
               "qualification_state": "UNCHANGED_NOT_EVALUATED", "model_runtime": "NOT_EVALUATED",
               "promotion_authorization": "NONE"}
    code = 0
    try:
        with args.receipt.open("x", encoding="utf-8") as handle:
            journal = None
            try:
                journal = Path(str(args.receipt) + ".journal.jsonl").open("x", encoding="utf-8")
                checkpoint = lambda current: append_checkpoint(journal, current)
                require(full_sha(args.source_commit) and full_sha(args.expected_parent), "FULL_SHA_REQUIRED")
                if args.publish or args.diagnose:
                    check_actions(args.source_commit)
                data, blob = capture_source(args.target, args.source_commit)
                receipt.update({"source_git_blob": blob, "card_sha256": digest(data), "card_bytes": len(data),
                                "source_signature": "GITHUB_VERIFIED_CURRENT_COMMIT_ONLY",
                                "publication_status": "PLAN_ONLY"})
                checkpoint(receipt)
                if args.diagnose:
                    diagnose_provider(receipt)
                elif args.publish:
                    receipt["phase"] = "PROVIDER_PREFLIGHT"
                    publish_card(data, receipt, checkpoint=checkpoint)
                else:
                    receipt["phase"] = "COMPLETE"
            except Exception as exc:
                code = 1
                record_failure(receipt, exc)
            finally:
                receipt["created_utc"] = datetime.now(timezone.utc).isoformat()
                if journal is not None:
                    try:
                        append_checkpoint(journal, receipt)
                    except Exception as exc:
                        code = 1
                        record_failure(receipt, exc)
                    try:
                        journal.close()
                    except Exception as exc:
                        code = 1
                        record_failure(receipt, exc)
                json.dump(receipt, handle, indent=2, allow_nan=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
    except Exception as exc:
        print("card publication receipt unavailable: " + failure_metadata(exc)["error_type"], file=sys.stderr)
        return 1
    print(json.dumps({"target": args.target, "publication_status": receipt["publication_status"],
                      "phase": receipt["phase"]}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

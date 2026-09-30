# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
"""Explicit public deterministic software lab; no model or training entry point.

TLS belongs to the managed external proxy. Host and Origin checks never trust
Forwarded headers. Source digests are content binding, not a publisher signature.
"""
from __future__ import annotations

from collections import Counter
import json
import math
import os
import platform
from pathlib import Path, PurePosixPath
import re
from typing import Any, Sequence

from . import policy as policy_module
from . import server as local

MODE = "DETERMINISTIC_SOFTWARE_LAB"
RUNTIME_SCHEMA = "szl.triage-public-runtime/v1"
ENVELOPE_SCHEMA = "szl.public-decision-envelope/v1"
BINDING_SCHEMA = "szl.triage-source-binding/v1"
GITHUB_REPOSITORY = "szl-holdings/szl-typesafe-triage"
MAX_BINDING_BYTES = 65536
MAX_SOURCE_FILES = 256
# Only these fields affect routing, origin, decoding or HTTP framing. Managed
# proxies may repeat tracing/forwarding metadata; none of that metadata grants
# trust or participates in decisions. Ambiguous security fields still fail shut.
_SINGLETON_HEADERS = frozenset({
    "host", "origin", "content-length", "content-type", "content-encoding",
    "transfer-encoding", "connection", "expect", "te", "upgrade",
})
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_AUTHORITY = re.compile(
    r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?::([0-9]{1,5}))?\Z"
)

_LANDING_PAGE = (local._LANDING_PAGE
    .replace("Local triage", "TypeSafe Triage software lab")
    .replace("DETERMINISTIC LOCAL RESEARCH", "DETERMINISTIC SOFTWARE LAB · HOLD")
    .replace("Loading policy identity…", "Loading source and policy identity…")
    .replace("'Policy '+r.policy.version+' · SHA-256 '+r.policy.sha256.slice(0,16)",
             "'GitHub '+r.source_binding.github_commit+' · Model promotion: '+r.disposition")
    .replace("The local service could not be reached.", "The software lab could not be reached.")
    .replace("Digests check that the returned contents agree.",
             "Model promotion remains HOLD. This public software lab uses deterministic rules. "
             "Digests check that the returned contents agree."))


def _source_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _safe_file(root: Path, relative: str) -> Path:
    if (not isinstance(relative, str) or not relative or "\\" in relative
            or ":" in relative or "\x00" in relative):
        raise ValueError("Invalid source binding path")
    parts = PurePosixPath(relative)
    if (parts.is_absolute() or any(part in {".", ".."} for part in parts.parts)
            or parts.as_posix() != relative):
        raise ValueError("Invalid source binding path")
    target = root.joinpath(*parts.parts)
    if any(path.is_symlink() for path in [target, *target.parents] if path != root.parent):
        raise ValueError("Symlinks are not source binding files")
    try:
        target.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (ValueError, OSError) as error:
        raise ValueError("Source binding path is absent or outside the source root") from error
    if not target.is_file():
        raise ValueError("Source binding path is not a file")
    return target


def verify_source_binding(binding_path: str | Path,
                          source_root: str | Path | None = None) -> dict[str, Any]:
    """Verify an exact package source set and policy, before opening any socket.

    The publisher creates this manifest from the immutable GitHub commit. This
    check binds those declared hashes to disk; it does not authenticate GitHub.
    """
    root = Path(source_root) if source_root is not None else _source_root()
    path = Path(binding_path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BINDING_BYTES:
        raise ValueError("Source binding must be a bounded regular file")
    raw = path.read_bytes()
    if len(raw) > MAX_BINDING_BYTES:
        raise ValueError("Source binding is too large")
    value = local._decode_json(raw)
    if (not isinstance(value, dict)
            or set(value) != {"schema", "github_repository", "github_commit", "source_files"}
            or value["schema"] != BINDING_SCHEMA
            or value["github_repository"] != GITHUB_REPOSITORY
            or not isinstance(value["github_commit"], str)
            or not _COMMIT.fullmatch(value["github_commit"])):
        raise ValueError("Invalid source binding identity")
    files = value["source_files"]
    if not isinstance(files, dict) or not 1 <= len(files) <= MAX_SOURCE_FILES:
        raise ValueError("Invalid source binding file set")
    # Validate every declared path even when the complete set is wrong.
    declared = {}
    for relative, digest in files.items():
        target = _safe_file(root, relative)
        if not isinstance(digest, str) or not local._HASH.fullmatch(digest):
            raise ValueError("Invalid source file digest")
        declared[relative] = target
    package = root / "src" / "szl_triage"
    if package.is_symlink() or any(item.is_symlink() for item in package.rglob("*")):
        raise ValueError("Symlinks are not source binding files")
    expected = {file.relative_to(root).as_posix() for file in package.rglob("*.py")}
    expected.add("src/szl_triage/data/triage_policy.v3.json")
    if set(files) != expected:
        raise ValueError("Source binding does not cover the exact package and default policy")
    for relative, target in declared.items():
        if local._sha(target.read_bytes()) != files[relative]:
            raise ValueError("Source binding byte mismatch")
    if path.read_bytes() != raw:
        raise ValueError("Source binding changed during verification")
    return {"schema": BINDING_SCHEMA, "github_repository": GITHUB_REPOSITORY,
            "github_commit": value["github_commit"],
            "manifest_sha256": local._sha(raw),
            "source_files_sha256": local._sha(local._canonical(files)),
            "source_file_count": len(files), "verified": True,
            "authenticity": "UNSIGNED_CONTENT_BINDING_ONLY"}


def _authorities(values: Sequence[str]) -> frozenset[str]:
    if isinstance(values, (str, bytes)) or not values:
        raise ValueError("An explicit trusted authority list is required")
    result = set()
    for value in values:
        match = _AUTHORITY.fullmatch(value) if isinstance(value, str) else None
        if (match is None or len(value) > 253 or value in result
                or value.split(":", 1)[0] in {"localhost", "127.0.0.1"}
                or (match.group(1) is not None and
                    (not 1 <= int(match.group(1)) <= 65535
                     or str(int(match.group(1))) != match.group(1)))):
            raise ValueError("Trusted authorities must be unique exact lowercase DNS authorities")
        result.add(value)
    return frozenset(result)


class _PublicHandler(local._Handler):
    server_version = "SZLSoftwareLab/1"

    def _trusted_request(self) -> bool:
        names = Counter(name.lower() for name in self.headers.keys())
        duplicated = sorted(name for name, count in names.items()
                            if count != 1 and name in _SINGLETON_HEADERS)
        if duplicated:
            self._json(400, {"error": "duplicate_header", "headers": duplicated})
            return False
        hosts = self.headers.get_all("Host", [])
        if len(hosts) != 1:
            self._json(403, {"error": "host_not_allowed"})
            return False
        authority = hosts[0]
        if authority in self.server.trusted_authorities:
            expected_origin = f"https://{authority}"
        elif (self.server.allow_loopback_probes
              and authority in {f"127.0.0.1:{self.server.server_port}",
                                f"localhost:{self.server.server_port}"}
              and self.client_address[0] in {"127.0.0.1", "::1"}):
            expected_origin = f"http://{authority}"
        else:
            self._json(403, {"error": "host_not_allowed"})
            return False
        origins = self.headers.get_all("Origin", [])
        if origins and origins != [expected_origin]:
            self._json(403, {"error": "origin_not_allowed"})
            return False
        return True

    def _decision_envelope(self, decision: dict[str, Any]) -> dict[str, Any]:
        envelope = {"schema": ENVELOPE_SCHEMA, "mode": MODE,
                    "authenticity": "UNSIGNED_CONTENT_INTEGRITY_ONLY",
                    "policy": self.server.identity["policy"],
                    "implementation": self.server.identity["implementation"],
                    "source_binding": self.server.identity["source_binding"],
                    "model_loaded": False, "disposition": "HOLD",
                    "decision": decision, "decision_sha256": local._sha(local._canonical(decision))}
        envelope["envelope_sha256"] = local._sha(local._canonical(envelope))
        return envelope


def make_public_server(*, trusted_authorities: Sequence[str], port: int = 7860,
                       allow_loopback_probes: bool = False,
                       frame_ancestor: str | None = None,
                       binding_path: str | Path | None = None) -> local._LocalServer:
    """Bind 0.0.0.0 only through this explicitly selected public entry point."""
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("Port must be an integer between 0 and 65535")
    if type(allow_loopback_probes) is not bool:
        raise ValueError("Loopback probe option must be a boolean")
    if frame_ancestor not in {None, "https://huggingface.co"}:
        raise ValueError("Only the explicit Hugging Face HTTPS iframe ancestor is supported")
    authorities = _authorities(trusted_authorities)
    path = Path(binding_path) if binding_path is not None else _source_root() / "SOURCE_BINDING.json"
    binding = verify_source_binding(path)
    policy_path = policy_module.default_policy_path()
    before = policy_path.read_bytes()
    local._decode_json(before)
    policy = policy_module.load(policy_path)
    if not all(math.isfinite(weight) and weight > 0 for weight in policy.axis_weights.values()):
        raise ValueError("Policy axis weights must be finite and positive")
    if policy_path.read_bytes() != before or verify_source_binding(path) != binding:
        raise ValueError("Public source or policy changed while loading")
    runtime = local._LocalServer(policy, local._sha(before), port, bind_address="0.0.0.0",
                                 handler=_PublicHandler, mode=MODE, landing_page=_LANDING_PAGE,
                                 frame_ancestors=frame_ancestor or "'none'")
    runtime.trusted_authorities = authorities
    runtime.allow_loopback_probes = allow_loopback_probes
    runtime.identity.update({"schema": RUNTIME_SCHEMA, "source_binding": binding,
                             "disposition": "HOLD", "model_loaded": False,
                             "python_version": platform.python_version(),
                             "scope": "DETERMINISTIC_RULE_BASED_SOFTWARE_ONLY"})
    return runtime


def main() -> int:
    """Environment-configured managed Space runtime; never train or load a model."""
    probes = os.environ.get("TRIAGE_ALLOW_LOOPBACK_PROBES", "0")
    if probes not in {"0", "1"}:
        raise ValueError("TRIAGE_ALLOW_LOOPBACK_PROBES must be 0 or 1")
    values = os.environ.get("TRIAGE_TRUSTED_AUTHORITIES", "").split(",")
    runtime = make_public_server(trusted_authorities=tuple(values), port=7860,
                                 allow_loopback_probes=probes == "1",
                                 frame_ancestor=os.environ.get("TRIAGE_FRAME_ANCESTOR") or None)
    print(json.dumps({"bind": "0.0.0.0:7860", **runtime.identity}), flush=True)
    try:
        runtime.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass  # Operator stop; the owned socket is closed below without evidence writes.
    finally:
        runtime.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

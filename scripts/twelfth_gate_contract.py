"""Fail-closed source and artifact bindings for the twelfth-gate study.

This module imports no ML framework. Provider source approval, model loading, and
GPU execution are separate boundaries and remain unavailable until explicitly
qualified.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
from typing import Any


BASE_MODEL = "Qwen/Qwen3.5-0.8B"
BASE_REVISION = "2fc06364715b967f1860aea9cf38778875588b17"
# Exact versions observed in evidence/five-seed-study/environment-receipt.json.
# Version equality is necessary but not sufficient; reviewed source digests are
# separately required below before any provider import or model load.
UNSLOTH_VERSION = "2026.9.10"
UNSLOTH_ZOO_VERSION = "2026.9.7"

# No reviewed provider source archive or distribution digest is committed yet.
# Production preflight must therefore remain blocked. Never fill these from an
# observed installation without a separate source review and owner admission.
APPROVED_PROVIDER_DISTRIBUTION_SHA256: dict[str, str] = {}

ADAPTER_BINDING = "SZL_ADAPTER_BINDING.json"
TOKENIZER_FILES = (
    "tokenizer.json",
    "tokenizer_config.json",
    "chat_template.jinja",
    "special_tokens_map.json",
    "processor_config.json",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def tokenizer_files_sha256(adapter: Path) -> dict[str, str]:
    adapter = Path(adapter)
    return {name: sha256_file(adapter / name) for name in TOKENIZER_FILES
            if (adapter / name).is_file()}


def adapter_snapshot(adapter: Path) -> dict[str, Any]:
    adapter = Path(adapter)
    weights = adapter / "adapter_model.safetensors"
    config = adapter / "adapter_config.json"
    if not weights.is_file() or not config.is_file():
        raise ValueError("adapter weights/config are incomplete")
    tokenizer = tokenizer_files_sha256(adapter)
    if not {"tokenizer.json", "tokenizer_config.json"}.issubset(tokenizer):
        raise ValueError("adapter text tokenizer files are incomplete")
    return {
        "adapter_sha256": sha256_file(weights),
        "adapter_config_sha256": sha256_file(config),
        "tokenizer_files_sha256": tokenizer,
    }


def load_adapter_binding(
    adapter: Path,
    *,
    expected_source_commit: str | None = None,
    expected_trainer_sha256: str | None = None,
) -> dict[str, Any]:
    adapter = Path(adapter)
    path = adapter / ADAPTER_BINDING
    if not path.is_file():
        raise ValueError("adapter binding receipt is absent")
    binding = json.loads(path.read_text(encoding="utf-8-sig"))
    expected = {
        "schema": "szl.twelfth-gate-adapter-binding/v1",
        "base_model": BASE_MODEL,
        "base_revision": BASE_REVISION,
    }
    problems = [key for key, value in expected.items() if binding.get(key) != value]
    if expected_source_commit is not None and binding.get("source_commit") != expected_source_commit:
        problems.append("source_commit")
    if expected_trainer_sha256 is not None \
            and binding.get("trainer_sha256") != expected_trainer_sha256:
        problems.append("trainer_sha256")
    snapshot = adapter_snapshot(adapter)
    for key, value in snapshot.items():
        if binding.get(key) != value:
            problems.append(key)
    config = json.loads((adapter / "adapter_config.json").read_text(encoding="utf-8-sig"))
    if config.get("base_model_name_or_path") != BASE_MODEL:
        problems.append("adapter_config.base_model_name_or_path")
    if config.get("revision") != BASE_REVISION:
        problems.append("adapter_config.revision")
    if problems:
        raise ValueError("adapter binding mismatch: " + ", ".join(sorted(set(problems))))
    return binding


def assert_resolved_repository(name: str) -> None:
    """Reject provider remapping before the resolved repository is fetched."""
    if name != BASE_MODEL:
        raise RuntimeError("provider resolved an unapproved model repository: " + str(name))


def assert_loaded_model_identity(model: Any) -> dict[str, Any]:
    """Require an observed immutable base identity after the provider returns."""
    configs, queue, seen = [], [model], set()
    while queue and len(seen) < 32:
        owner = queue.pop(0)
        if owner is None or id(owner) in seen:
            continue
        seen.add(id(owner))
        config = getattr(owner, "config", None)
        if config is not None and all(config is not item for item in configs):
            configs.append(config)
        queue.extend(getattr(owner, name, None) for name in ("base_model", "model", "module"))
    revisions = {getattr(config, "_commit_hash", None) for config in configs}
    names = {getattr(config, "_name_or_path", None) for config in configs}
    names.update(getattr(config, "name_or_path", None) for config in configs)
    revisions.discard(None)
    names.discard(None)
    if revisions != {BASE_REVISION}:
        raise RuntimeError("loaded model revision is missing, remapped, or not the approved revision")
    if names != {BASE_MODEL}:
        raise RuntimeError("loaded model identity includes a missing or unapproved base model")
    return {"base_model": BASE_MODEL, "base_revision": BASE_REVISION,
            "observed_names": sorted(str(name) for name in names),
            "observed_revisions": sorted(str(item) for item in revisions)}


def distribution_source_sha256(name: str) -> str:
    distribution = importlib.metadata.distribution(name)
    files = sorted(str(path) for path in (distribution.files or ())
                   if str(path).lower().endswith((".py", ".json", ".toml")))
    digest = hashlib.sha256()
    for relative in files:
        path = Path(distribution.locate_file(relative))
        if not path.is_file():
            raise RuntimeError("provider distribution file is missing: " + relative)
        digest.update(relative.replace("\\", "/").encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    if not files:
        raise RuntimeError("provider distribution exposes no reviewable source files")
    return digest.hexdigest()


def validate_provider_runtime() -> dict[str, Any]:
    required = {"unsloth": UNSLOTH_VERSION, "unsloth_zoo": UNSLOTH_ZOO_VERSION}
    observed = {}
    for name, version in required.items():
        actual = importlib.metadata.version(name)
        if actual != version:
            raise RuntimeError("{} version {} is not approved {}".format(name, actual, version))
        digest = distribution_source_sha256(name)
        approved = APPROVED_PROVIDER_DISTRIBUTION_SHA256.get(name)
        if approved is None:
            raise RuntimeError("{} provider source digest has not been independently approved ({})".format(
                name, digest))
        if digest != approved:
            raise RuntimeError("{} provider source digest differs from the approved source".format(name))
        observed[name] = {"version": actual, "distribution_sha256": digest}
    return observed

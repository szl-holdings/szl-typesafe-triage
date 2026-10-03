"""The legacy study helper must never turn training state into Hub payloads."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def publisher(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "triage_publish_guard_test", ROOT / "scripts" / "train_eval_publish.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    run1 = tmp_path / "run1" / "adapter"
    study = tmp_path / "study"
    evidence = tmp_path / "evidence"
    output = tmp_path / "publish"
    for seed in module.SEEDS:
        adapter = run1 if seed == 11 else study / f"seed-{seed:03d}" / "adapter"
        adapter.mkdir(parents=True)
        for name in module.ADAPTER_FILES:
            (adapter / name).write_bytes(f"seed={seed}; file={name}".encode())
    for name in module.EVIDENCE_FILES:
        path = evidence / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("evidence", encoding="utf-8")

    monkeypatch.setattr(module, "RUN1_ADAPTER", run1)
    monkeypatch.setattr(module, "STUDY", study)
    monkeypatch.setattr(module, "EVIDENCE", evidence)
    monkeypatch.setattr(module, "PUBLISH", output)
    return SimpleNamespace(module=module, run1=run1, study=study,
                           evidence=evidence, output=output)


def test_build_contains_only_reviewed_adapter_card_and_evidence_files(publisher):
    module = publisher.module
    module.build_publish_directory("research card")
    assert module.require_exact_regular_files(publisher.output, module.PUBLISH_FILES) == sorted(
        module.PUBLISH_FILES
    )
    assert (publisher.output / "adapter_model.safetensors").is_file()
    assert (publisher.output / "adapters/seed-071/adapter_config.json").is_file()
    assert (publisher.output / "evidence/evaluation/metrics.csv").is_file()
    assert not any(name.endswith((".bin", ".pt", ".pth")) for name in module.PUBLISH_FILES)


@pytest.mark.parametrize("where,name", [
    ("run1", "training_args.bin"),
    ("seed", "runs/checkpoint-387/optimizer.pt"),
    ("evidence", "evaluation/rng_state.pth"),
    ("run1", "unreviewed.json"),
])
def test_source_contamination_fails_before_replacing_previous_build(
    publisher, where, name
):
    source = {
        "run1": publisher.run1,
        "seed": publisher.study / "seed-023" / "adapter",
        "evidence": publisher.evidence,
    }[where]
    contaminant = source / name
    contaminant.parent.mkdir(parents=True, exist_ok=True)
    contaminant.write_bytes(b"unsafe or unreviewed")
    publisher.output.mkdir()
    (publisher.output / "previous-build.txt").write_text("preserve", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Publication file contract mismatch"):
        publisher.module.build_publish_directory("research card")
    assert (publisher.output / "previous-build.txt").read_text(encoding="utf-8") == "preserve"


def test_source_symlink_is_refused(publisher, tmp_path):
    destination = tmp_path / "outside.json"
    destination.write_text("outside", encoding="utf-8")
    try:
        (publisher.run1 / "tokenizer.json").unlink()
        (publisher.run1 / "tokenizer.json").symlink_to(destination)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"file symlinks are unavailable: {exc}")

    with pytest.raises(RuntimeError, match="contains a link"):
        publisher.module.build_publish_directory("research card")


def test_stray_file_blocks_provider_access(publisher, monkeypatch):
    module = publisher.module
    module.build_publish_directory("research card")
    (publisher.output / "training_args.bin").write_bytes(b"unsafe")
    monkeypatch.setitem(sys.modules, "huggingface_hub", None)
    with pytest.raises(RuntimeError, match="Publication file contract mismatch"):
        module.publish_to_hub()


def test_upload_uses_exact_allow_patterns(publisher, monkeypatch):
    module = publisher.module
    module.build_publish_directory("research card")
    calls = []
    api = SimpleNamespace(
        create_repo=lambda **kwargs: "https://huggingface.co/example/repo",
        upload_folder=lambda **kwargs: calls.append(kwargs) or "https://huggingface.co/example/repo/commit/abc",
        model_info=lambda **kwargs: SimpleNamespace(sha="a" * 40, private=False),
        upload_file=lambda **kwargs: calls.append(kwargs),
    )
    fake_hub = ModuleType("huggingface_hub")
    fake_hub.HfApi = lambda token: api
    monkeypatch.setitem(sys.modules, "huggingface_hub", fake_hub)
    monkeypatch.setenv("HF_TOKEN", "test-token")

    assert module.publish_to_hub() == f"https://huggingface.co/{module.HF_REPO}"
    assert calls[0]["allow_patterns"] == sorted(module.PUBLISH_FILES)
    assert not any(path.endswith((".bin", ".pt", ".pth"))
                   for path in calls[0]["allow_patterns"])

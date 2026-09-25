"""Guard public entry points against accidental training and publication."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_pipeline():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("triage_test_pipeline", ROOT / "scripts/train_eval_publish.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("script", ["codex_finish.py", "train_eval_publish.py"])
def test_help_is_bounded_and_has_no_cwd_side_effects(script, tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / script), "--help"],
                            cwd=tmp_path, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert "publish-plan" in result.stdout
    assert list(tmp_path.iterdir()) == []
    assert "PREFLIGHT" not in result.stdout


def test_pipeline_import_does_not_create_output_dirs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    def refuse_mkdir(*args, **kwargs):
        pytest.fail("Import must not create directories anywhere, including SOURCE_ROOT")
    monkeypatch.setattr(Path, "mkdir", refuse_mkdir)
    load_pipeline()
    assert list(tmp_path.iterdir()) == []


def test_default_action_replays_without_loading_model(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / "scripts/codex_finish.py")],
                            cwd=tmp_path, capture_output=True, text=True, timeout=20)
    report = json.loads(result.stdout)
    assert report["schema"] == "szl.study-evidence-audit/v1"
    assert report["provenance"]["status"] == "HISTORICAL_REPLAY_ONLY"
    assert list(tmp_path.iterdir()) == []


def test_output_cannot_overwrite_an_existing_receipt(tmp_path):
    receipt = tmp_path / "receipt.json"
    receipt.write_text("preserve", encoding="utf-8")
    result = subprocess.run([sys.executable, str(ROOT / "scripts/codex_finish.py"),
                             "--output", str(receipt)], capture_output=True, text=True, timeout=20)
    assert result.returncode == 2
    assert receipt.read_text(encoding="utf-8") == "preserve"


def test_smoke_refuses_without_artifact_root_before_ml_import():
    result = subprocess.run([sys.executable, str(ROOT / "scripts/codex_finish.py"), "smoke"],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 2
    assert "requires --artifact-root" in result.stdout


@pytest.mark.parametrize("raw", [
    '{"label":"BUG","label":"HELP","state":"MEASURED","evidence":[]}',
    '{"label":NaN,"state":"MEASURED","evidence":[]}',
    '{"label":5,"state":"MEASURED","evidence":[]}',
    '{"label":"BUG","state":"MEASURED","evidence":[false]}',
    '{"label":"BUG","state":"MEASURED","evidence":[],"extra":true}',
])
def test_strict_json_rejects_ambiguous_or_untyped_outputs(raw):
    assert load_pipeline().strict_json(raw) is None


def test_existing_evaluation_is_never_silently_reused_or_overwritten(tmp_path, monkeypatch):
    pipeline = load_pipeline()
    monkeypatch.setattr(pipeline, "EVALUATION", tmp_path)
    path = tmp_path / "metrics-seed-011.json"
    path.write_text('{"held_rows":113}', encoding="utf-8")
    monkeypatch.setattr(pipeline, "load_model", lambda _: pytest.fail("Model must not load"))
    with pytest.raises(RuntimeError, match="new output namespace"):
        pipeline.evaluate_target("seed-011", "unused", [])
    assert path.read_text(encoding="utf-8") == '{"held_rows":113}'


@pytest.fixture
def fake_smoke(tmp_path, monkeypatch):
    """Exercise control flow without importing the GPU stack."""
    from types import SimpleNamespace
    import importlib.metadata
    sys.path.insert(0, str(ROOT / "scripts"))
    import codex_finish as finish
    evidence = tmp_path / "evidence"
    (evidence / "frozen").mkdir(parents=True)
    adapter = tmp_path / "alternate" / "seed11"
    adapter.mkdir(parents=True)
    (adapter / "adapter_model.safetensors").write_bytes(b"test-adapter")
    (adapter / "adapter_config.json").write_text("{}", encoding="utf-8")
    index = [{"seed": 11, "local_path": "alternate/seed11",
              "adapter_sha256": finish.digest(adapter / "adapter_model.safetensors")}]
    (evidence / "adapter-index.json").write_text(json.dumps(index), encoding="utf-8")
    target = {"label": "BUG", "state": "MEASURED", "evidence": ["freeze"]}
    row = {"row_id": "r1", "target": target, "prompt": "freeze"}
    (evidence / "frozen" / "held.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    report = {"integrity_status": "PASS", "bundle_sha256": "same",
              "promotion_status": "NOT_PROMOTABLE", "release_gate": {"status": "BLOCKED"}}
    monkeypatch.setattr(finish, "audit", lambda _: report.copy())
    monkeypatch.setattr(finish, "source_identity", lambda: {"head": "original"})
    monkeypatch.setattr(importlib.metadata, "version", lambda _: "test")
    loaded = []
    model = SimpleNamespace(config=SimpleNamespace(_commit_hash="observed"))
    def load(name):
        loaded.append(name)
        return model, object()
    pipeline = SimpleNamespace(load_model=load, generate=lambda *a: (json.dumps(target), 0.1), strict_json=json.loads)
    monkeypatch.setitem(sys.modules, "train_eval_publish", pipeline)
    monkeypatch.setitem(sys.modules, "triage_text", SimpleNamespace(template_contract=lambda _: {"mode": "test"}))
    cuda = SimpleNamespace(is_available=lambda: True, get_device_capability=lambda: (12, 0),
                           get_arch_list=lambda: ["sm_120"], get_device_name=lambda _: "test-device")
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(cuda=cuda, __version__="test"))
    for key in ("SZL_ALLOW_HUB_PUSH", "TOKENIZERS_PARALLELISM", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        monkeypatch.setenv(key, "test")
    args = finish.parser().parse_args(["smoke", "--artifact-root", str(tmp_path),
                                      "--evidence", str(evidence), "--output", str(tmp_path / "new.json")])
    return finish, args, report, loaded, adapter


def test_smoke_loads_the_indexed_adapter_in_an_alternate_layout(fake_smoke):
    finish, args, _, loaded, adapter = fake_smoke
    report = finish.smoke(args)
    assert loaded == [str(adapter)]
    assert report["state"] == "EXECUTED"


def test_smoke_rejects_a_post_audit_failure_even_with_unchanged_hash(fake_smoke, monkeypatch):
    finish, args, report, _, _ = fake_smoke
    reports = iter([report, {**report, "integrity_status": "FAIL"}])
    monkeypatch.setattr(finish, "audit", lambda _: next(reports))
    with pytest.raises(RuntimeError, match="changed during smoke"):
        finish.smoke(args)


def test_smoke_rejects_source_changes_during_inference(fake_smoke, monkeypatch):
    finish, args, _, _, _ = fake_smoke
    versions = iter([{"head": "original"}, {"head": "changed"}])
    monkeypatch.setattr(finish, "source_identity", lambda: next(versions))
    with pytest.raises(RuntimeError, match="changed during smoke"):
        finish.smoke(args)


def test_smoke_rejects_unindexed_weights_before_model_load(fake_smoke):
    finish, args, _, loaded, adapter = fake_smoke
    (adapter / "adapter_model.safetensors").write_bytes(b"different")
    with pytest.raises(ValueError, match="indexed"):
        finish.smoke(args)
    assert loaded == []

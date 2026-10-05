"""Offline source-contract tests for the v1.1.0 twelfth-gate preflight."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "twelfth_gate_preflight_test", ROOT / "scripts" / "twelfth_gate_v110.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def generated_trainer(module, seed=11):
    source = module.TRAINER.read_text(encoding="utf-8")
    patches = module.trainer_patches(seed, "frozen", "augmentation", False)
    return module.apply_trainer_patches(source, patches)


def test_generated_trainer_pins_base_revision_and_requires_response_masking():
    module = load_runner()
    patched = generated_trainer(module)
    contract = module.validate_trainer_contract(patched)

    assert contract == {
        "base_model": "Qwen/Qwen3.5-0.8B",
        "base_revision": "2fc06364715b967f1860aea9cf38778875588b17",
        "train_on_responses_only": "REQUIRED_FAIL_CLOSED",
    }
    assert 'revision=BASE_REVISION' in patched
    assert '"base_revision": BASE_REVISION' in patched
    assert "train_on_responses_only unavailable" not in patched


@pytest.mark.parametrize(
    "tamper",
    [
        lambda source: source.replace("revision=BASE_REVISION, ", "", 1),
        lambda source: source.replace("Qwen/Qwen3.5-0.8B", "unsloth/Qwen3.5-0.8B", 1),
        lambda source: source.replace("trainer = train_on_responses_only", "trainer = object", 1),
    ],
)
def test_generated_trainer_contract_rejects_unbound_or_optional_training(tamper):
    module = load_runner()
    with pytest.raises(ValueError):
        module.validate_trainer_contract(tamper(generated_trainer(module)))


def test_powershell_runner_is_local_only_and_enforces_host_limits():
    module = load_runner()
    source = module.POWERSHELL_RUNNER.read_text(encoding="utf-8")
    contract = module.validate_powershell_runner(source)

    assert contract == {
        "publish": "DISABLED_FAIL_CLOSED",
        "max_wallclock_minutes": 180,
        "thermal_guard_celsius": 78,
        "preflight_only_supported": True,
    }
    assert "git push " not in source
    assert "gh pr " not in source
    assert "publish-adapters" not in source


def test_powershell_runner_contract_rejects_a_publication_sink():
    module = load_runner()
    source = module.POWERSHELL_RUNNER.read_text(encoding="utf-8") + "\ngit push origin unsafe\n"
    with pytest.raises(ValueError, match="banned"):
        module.validate_powershell_runner(source)


def test_offline_preflight_binds_inputs_and_never_imports_model_stack(tmp_path, monkeypatch):
    module = load_runner()
    monkeypatch.setattr(module, "WORK", tmp_path / "preflight-output")

    assert module.cmd_preflight(SimpleNamespace(skip_gpu=True)) == 0
    receipt = json.loads((module.WORK / "preflight.json").read_text(encoding="utf-8"))
    assert receipt["gpu"] == "SKIPPED_BY_FLAG"
    assert receipt["challenge"]["probe_classes"] == {"PARAPHRASE": 30, "STEERING": 12}
    assert receipt["challenge"]["criterion"].startswith("12 steering refusals gated")
    assert receipt["trainer"]["contract"]["base_revision"] == module.BASE_REVISION
    assert receipt["runner"]["contract"]["publish"] == "DISABLED_FAIL_CLOSED"
    assert set(receipt["trainer"]["generated_sha256"]) == {
        "seed-011", "seed-023", "seed-037", "seed-053", "seed-071"
    }

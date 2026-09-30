"""Legacy commands must no longer execute models or overwrite receipt history."""
import importlib.util
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_gate_requires_explicit_input_and_output():
    result = subprocess.run([sys.executable, str(ROOT/'scripts/gate.py')],
                            capture_output=True, text=True)
    assert result.returncode == 2
    assert '--output' in result.stderr
    assert 'Traceback' not in result.stderr


def test_both_legacy_entrypoints_are_import_safe(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    for name in ('gate', 'release_gate'):
        spec = importlib.util.spec_from_file_location('import_safe_' + name, ROOT/'scripts'/f'{name}.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert callable(module.main)
    assert 'unsloth' not in sys.modules


def test_help_works_without_model_dependencies():
    for name in ('gate', 'release_gate'):
        result = subprocess.run([sys.executable, str(ROOT/'scripts'/f'{name}.py'), '--help'],
                                capture_output=True, text=True)
        assert result.returncode == 0
        assert 'usage:' in result.stdout
        assert 'Traceback' not in result.stderr

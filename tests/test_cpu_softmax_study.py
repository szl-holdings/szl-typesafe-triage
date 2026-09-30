"""Independent CPU study: isolation, exact replay and frozen-artifact rejection."""
import copy
import json
import math
from pathlib import Path
import shutil

import pytest

from experiments.cpu_softmax.model import LABELS, SPEC, choose, fit, predict, stable_json
from experiments.cpu_softmax.predict import load_recorded_model, verify_study
from experiments.cpu_softmax.reproduce import ReproductionMismatch, reproduce
from szl_triage.proposal_task import make_task

ROOT = Path(__file__).resolve().parents[1]


def examples():
    texts = {
        'BUG': 'App crashes with exception on save', 'BILLING': 'Card charged twice for invoice',
        'FEATURE': 'Please add calendar export capability', 'REVIEW': 'Ambiguous report insufficient information',
        'SECURITY': 'Stranger accessed private account records', 'SUPPORT': 'How do I change my password'}
    rows = [{'split': 'train', 'input': text, 'label': label,
             'state': 'REVIEW' if label == 'REVIEW' else 'MEASURED'}
            for label, text in texts.items() for _ in range(2)]
    rows.append({'split': 'eval', 'input': 'unseen heldonlyword', 'label': 'BUG', 'state': 'MEASURED'})
    return rows


def copied_study(tmp_path):
    manifest = verify_study()
    for name in manifest['files']:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, path)
    destination = tmp_path / 'experiments/cpu_softmax/STUDY_MANIFEST.json'
    shutil.copyfile(ROOT / 'experiments/cpu_softmax/STUDY_MANIFEST.json', destination)
    return tmp_path


def test_held_input_and_label_cannot_change_weights_or_vocabulary():
    rows = examples()
    spec = dict(SPEC, epochs=12)
    model = fit(rows, spec=spec)
    changed = copy.deepcopy(rows)
    changed[-1].update(input='evaluation secret sentinel', label='NOT_A_TRAINING_LABEL', state='INVALID')
    assert stable_json(model) == stable_json(fit(changed, spec=spec))
    assert 'u:heldonlyword' not in model['vocabulary_index']


def test_exact_seed_and_training_bytes_reproduce_model():
    rows = examples()
    assert stable_json(fit(rows, spec=dict(SPEC, epochs=12))) == stable_json(fit(rows, spec=dict(SPEC, epochs=12)))


def test_probabilities_are_complete_finite_and_consistent_with_argmax():
    model = fit(examples(), spec=dict(SPEC, epochs=12))
    for text in ('App crashes with exception', '未知 out of vocabulary', 'Card charged twice'):
        label, probabilities, _ = choose(text, model)
        assert set(probabilities) == set(LABELS)
        assert all(math.isfinite(p) and 0 <= p <= 1 for p in probabilities.values())
        assert math.fsum(probabilities.values()) == pytest.approx(1, abs=1e-14)
        assert label == max(probabilities, key=probabilities.get)


def test_predictions_and_offsets_bind_exact_unicode_input():
    model = fit(examples(), spec=dict(SPEC, epochs=12))
    text = '  App crashes \U0001f680 with exception on save.  '
    output = predict(text, model, make_task)
    decoded = output['decoded']
    parsed = json.loads(output['raw_output'])
    assert parsed['state'] == ('REVIEW' if parsed['label'] == 'REVIEW' else 'MEASURED')
    assert decoded['evidence']
    for span, offsets in zip(decoded['evidence'], decoded['source_offsets']):
        assert text[offsets['start']:offsets['end']] == span
        assert span.encode('utf-8') in text.encode('utf-8')
    assert make_task(text.replace('crashes', 'works')).input_sha256 != decoded['input_sha256']


def test_model_learns_small_separable_training_problem():
    rows = examples()
    model = fit(rows, spec=dict(SPEC, epochs=12))
    assert sum(choose(row['input'], model)[0] == row['label'] for row in rows if row['split'] == 'train') == 12


def test_conflicting_training_state_fails_closed():
    broken = examples()
    broken[0]['state'] = 'REVIEW'
    with pytest.raises(ValueError, match='state conflict'):
        fit(broken, spec=dict(SPEC, epochs=12))


def test_recorded_artifact_load_and_model_tamper_rejection(tmp_path):
    model, sha = load_recorded_model()
    assert sha == 'afee69cbbabc5de2fa117ca91b7d201f6b146afc1ccc49a2caf1bcc666f090f2'
    assert model['train_rows'] == 527
    repository = copied_study(tmp_path)
    path = repository / 'experiments/cpu_softmax/artifacts/model.json'
    path.write_bytes(path.read_bytes().replace(b'0.25', b'0.24', 1))
    with pytest.raises(ValueError, match='differs from manifest'):
        load_recorded_model(repository)


def test_source_dependency_tamper_rejection(tmp_path):
    repository = copied_study(tmp_path)
    path = repository / 'src/szl_triage/proposal_task.py'
    path.write_bytes(path.read_bytes() + b'\n# changed task\n')
    with pytest.raises(ValueError, match='differs from manifest'):
        verify_study(repository)


def test_invalid_inputs_fail_before_feature_extraction(monkeypatch):
    import experiments.cpu_softmax.model as module
    def forbidden(*args):
        raise AssertionError('Invalid input was featurized')
    monkeypatch.setattr(module, 'choose', forbidden)
    for text in ('', 'x' * 2049, 'word ' * 65):
        with pytest.raises(ValueError):
            predict(text, {}, make_task)


def test_full_canonical_training_and_development_predictions_replay(tmp_path):
    try:
        receipt = reproduce(tmp_path / 'new-replay')
    except ReproductionMismatch as failure:
        receipt = failure.receipt
        # Cross-runtime differences must remain explicit and fail exact replay.
        assert not all(receipt[k] for k in ('exact_model_reproduction',
            'exact_prediction_reproduction', 'exact_qualification_reproduction'))
        retained = json.loads((tmp_path / 'new-replay/replay-receipt.json').read_text())
        assert retained == receipt
        print('CROSS_RUNTIME_REPRODUCTION_MISMATCH', stable_json(receipt))
    assert receipt['literal_prediction_matches'] == 42
    assert receipt['qualification_criteria_status_match']
    assert receipt['frozen_model_sha256'] == 'afee69cbbabc5de2fa117ca91b7d201f6b146afc1ccc49a2caf1bcc666f090f2'
    assert receipt['promotion_status'] == 'NOT_PROMOTABLE'
    with pytest.raises(FileExistsError):
        reproduce(tmp_path / 'new-replay')


def test_canonical_training_is_repeatable_within_the_same_runtime():
    dataset = ROOT / 'output/triage_distill_split_v0.4.0.jsonl'
    rows = [json.loads(line) for line in dataset.read_text(encoding='utf-8').splitlines() if line.strip()]
    assert stable_json(fit(rows)) == stable_json(fit(rows))


def test_manifest_path_traversal_and_overclaim_rejection(tmp_path):
    repository = copied_study(tmp_path)
    path = repository / 'experiments/cpu_softmax/STUDY_MANIFEST.json'
    manifest = json.loads(path.read_text())
    manifest['files']['../outside'] = 'a' * 64
    path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError, match='Invalid study file binding'):
        verify_study(repository)
    manifest['files'].pop('../outside')
    manifest['promotion_status'] = 'PROMOTABLE'
    path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError, match='overclaiming'):
        verify_study(repository)

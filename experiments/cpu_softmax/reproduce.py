"""Replay the frozen study into a new directory without changing its receipts."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import time

from .model import digest_bytes, fit, predict, stable_json
from .predict import REPOSITORY, load_recorded_model, verify_study
from szl_triage.proposal_task import make_task
from szl_triage.qualification import evaluate_records, strict_json


class ReproductionMismatch(ValueError):
    """The diagnostic receipt is retained; exact reproduction was not achieved."""
    def __init__(self, receipt):
        self.receipt = receipt
        super().__init__('Exact frozen study reproduction failed; diagnostic receipt retained')


def reproduce(output_dir, repository=REPOSITORY):
    repository = Path(repository).resolve()
    destination = Path(output_dir).resolve()
    # A new destination prevents accidental overwriting of sealed study receipts.
    destination.mkdir(parents=True, exist_ok=False)
    manifest = verify_study(repository)
    frozen, frozen_hash = load_recorded_model(repository)
    dataset_path = repository / manifest['training_input']['path']
    data = dataset_path.read_bytes()
    if digest_bytes(data) == manifest['training_input']['git_blob_sha256']:
        # Restore the exact historical eol=crlf checkout before receipt comparison.
        if b'\r\n' in data:
            raise ValueError('Declared Git dataset blob must use LF lines')
        data = data.replace(b'\n', b'\r\n')
    if digest_bytes(data) != manifest['training_input']['sha256']:
        raise ValueError('Canonical dataset bytes changed')
    rows = [strict_json(line) for line in data.decode('utf-8').splitlines() if line.strip()]
    train_start = time.perf_counter()
    model = fit(rows)
    elapsed = time.perf_counter() - train_start
    model_bytes = (stable_json(model) + '\n').encode('utf-8')
    (destination / 'model.json').write_bytes(model_bytes)
    exact_model = model_bytes == (repository / 'experiments/cpu_softmax/artifacts/model.json').read_bytes()
    frozen_numbers = frozen['idf'] + frozen['bias'] + [v for row in frozen['weights'] for v in row]
    replay_numbers = model['idf'] + model['bias'] + [v for row in model['weights'] for v in row]
    if len(frozen_numbers) != len(replay_numbers):
        raise ValueError('Replayed parameter shape differs from the frozen model')
    # Evaluation inputs/targets become available only after the model is frozen.
    artifacts = repository / 'experiments/cpu_softmax/artifacts'
    recorded = strict_json((artifacts / 'qualification-records.json').read_text(encoding='utf-8'))
    training_inputs = {r['input'] for r in rows if r.get('split') == 'train'}
    output_records, literal_matches, exact_probability_vectors = [], 0, 0
    probability_differences = []
    for record in recorded:
        if record['input'] in training_inputs:
            raise ValueError('Train/development input overlap')
        output = predict(record['input'], model, make_task)
        literal_matches += output['raw_output'] == record['raw_output']
        exact_probability_vectors += output['probabilities'] == record['probabilities']
        probability_differences.extend(abs(output['probabilities'][label] - value)
                                       for label, value in record['probabilities'].items())
        output_records.append({**record, 'raw_output': output['raw_output'],
                               'probabilities': output['probabilities']})
    thresholds = strict_json((repository / 'PROMOTION_THRESHOLDS.json').read_text(encoding='utf-8'))
    qualification = evaluate_records(output_records, thresholds, evaluation_scope='DEVELOPMENT')
    original_qualification = strict_json((artifacts / 'qualification.json').read_text(encoding='utf-8'))
    exact_qualification = qualification == original_qualification
    for name, value in (('qualification.json', qualification), ('records.json', output_records)):
        (destination / name).write_text(stable_json(value) + '\n', encoding='utf-8')
    receipt = {'schema': 'szl.cpu-softmax-replay/v1',
               'completed_utc': datetime.now(timezone.utc).isoformat(),
               'frozen_model_sha256': frozen_hash, 'replayed_model_sha256': digest_bytes(model_bytes),
               'exact_model_reproduction': exact_model,
               'parameter_values_differing': sum(a != b for a, b in zip(frozen_numbers, replay_numbers)),
               'maximum_absolute_parameter_difference': max(abs(a-b) for a,b in zip(frozen_numbers,replay_numbers)),
               'literal_prediction_matches': literal_matches, 'rows': len(recorded),
               'exact_probability_vector_matches': exact_probability_vectors,
               'maximum_absolute_probability_difference': max(probability_differences),
               'exact_prediction_reproduction': literal_matches == len(recorded) and exact_probability_vectors == len(recorded),
               'exact_qualification_reproduction': exact_qualification,
               'qualification_criteria_status_match': all(qualification['criteria'][k]['status'] == v['status']
                                                         for k,v in original_qualification['criteria'].items()),
               'replayed_expected_calibration_error': qualification['metrics']['expected_calibration_error'],
               'expected_calibration_error_difference': qualification['metrics']['expected_calibration_error'] - original_qualification['metrics']['expected_calibration_error'],
               'runtime': {'python': platform.python_version(), 'platform': platform.platform(),
                           'libc': list(platform.libc_ver())},
               'training_input_git_blob_sha256': manifest['training_input']['git_blob_sha256'],
               'training_input_original_checkout_sha256': digest_bytes(data),
               'training_seconds': elapsed, 'promotion_status': 'NOT_PROMOTABLE',
               'evaluation_scope': 'DEVELOPMENT_PREVIOUSLY_EXPOSED_CHALLENGE',
               'semantic_family_independence': 'NOT_ESTABLISHED', 'release_authorization': 'NONE'}
    (destination / 'replay-receipt.json').write_text(stable_json(receipt) + '\n', encoding='utf-8')
    if not all(receipt[k] for k in ('exact_model_reproduction', 'exact_prediction_reproduction',
                                   'exact_qualification_reproduction')):
        raise ReproductionMismatch(receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    try:
        receipt = reproduce(args.output_dir)
    except ReproductionMismatch as failure:
        print(json.dumps(failure.receipt, indent=2))
        raise SystemExit(1) from failure
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()

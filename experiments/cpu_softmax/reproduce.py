"""Replay the frozen study into a new directory without changing its receipts."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from .model import digest_bytes, fit, predict, stable_json
from .predict import REPOSITORY, load_recorded_model, verify_study
from szl_triage.proposal_task import make_task
from szl_triage.qualification import evaluate_records, strict_json


def reproduce(output_dir, repository=REPOSITORY):
    repository = Path(repository).resolve()
    destination = Path(output_dir).resolve()
    # A new destination prevents accidental overwriting of sealed study receipts.
    destination.mkdir(parents=True, exist_ok=False)
    manifest = verify_study(repository)
    frozen, frozen_hash = load_recorded_model(repository)
    dataset_path = repository / manifest['training_input']['path']
    data = dataset_path.read_bytes()
    if digest_bytes(data) != manifest['training_input']['sha256']:
        raise ValueError('Canonical dataset bytes changed')
    rows = [strict_json(line) for line in data.decode('utf-8').splitlines() if line.strip()]
    train_start = time.perf_counter()
    model = fit(rows)
    elapsed = time.perf_counter() - train_start
    model_bytes = (stable_json(model) + '\n').encode('utf-8')
    (destination / 'model.json').write_bytes(model_bytes)
    if model_bytes != (repository / 'experiments/cpu_softmax/artifacts/model.json').read_bytes():
        raise ValueError('Training replay does not reproduce the frozen model exactly')
    # Evaluation inputs/targets become available only after the model is frozen.
    artifacts = repository / 'experiments/cpu_softmax/artifacts'
    recorded = strict_json((artifacts / 'qualification-records.json').read_text(encoding='utf-8'))
    training_inputs = {r['input'] for r in rows if r.get('split') == 'train'}
    output_records = []
    for record in recorded:
        if record['input'] in training_inputs:
            raise ValueError('Train/development input overlap')
        output = predict(record['input'], model, make_task)
        if (output['raw_output'] != record['raw_output']
                or output['probabilities'] != record['probabilities']):
            raise ValueError('Recorded predictions do not reproduce exactly')
        output_records.append({**record, 'raw_output': output['raw_output'],
                               'probabilities': output['probabilities']})
    thresholds = strict_json((repository / 'PROMOTION_THRESHOLDS.json').read_text(encoding='utf-8'))
    qualification = evaluate_records(output_records, thresholds, evaluation_scope='DEVELOPMENT')
    if qualification != strict_json((artifacts / 'qualification.json').read_text(encoding='utf-8')):
        raise ValueError('Qualification replay differs from the original report')
    for name, value in (('qualification.json', qualification), ('records.json', output_records)):
        (destination / name).write_text(stable_json(value) + '\n', encoding='utf-8')
    receipt = {'schema': 'szl.cpu-softmax-replay/v1',
               'completed_utc': datetime.now(timezone.utc).isoformat(),
               'model_sha256': frozen_hash, 'exact_model_reproduction': model == frozen,
               'exact_prediction_reproduction': True, 'exact_qualification_reproduction': True,
               'training_seconds': elapsed, 'promotion_status': 'NOT_PROMOTABLE',
               'evaluation_scope': 'DEVELOPMENT_PREVIOUSLY_EXPOSED_CHALLENGE',
               'semantic_family_independence': 'NOT_ESTABLISHED', 'release_authorization': 'NONE'}
    (destination / 'replay-receipt.json').write_text(stable_json(receipt) + '\n', encoding='utf-8')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(reproduce(args.output_dir), indent=2))


if __name__ == '__main__':
    main()

"""Train before reading the immutable development challenge, then score all rows."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
import time

from model import SPEC, digest_bytes, fit, predict, selected_training_rows, stable_json

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent.parent
CANONICAL = WORKSPACE / 'work' / 'triage-promotion-build'
DATASET = CANONICAL / 'output' / 'triage_distill_split_v0.4.0.jsonl'
CHALLENGE = WORKSPACE / 'outputs' / 'triage-fresh-challenge-seed11.json'
sys.path.insert(0, str(CANONICAL / 'src'))
from szl_triage.proposal_task import make_task
from szl_triage.qualification import evaluate_records


def save(name, value):
    path = HERE / name
    content = (stable_json(value) + '\n').encode('utf-8')
    path.write_bytes(content)
    return digest_bytes(content)


def main():
    started = datetime.now(timezone.utc).isoformat()
    start = time.perf_counter()
    spec_hash = save('training-spec.json', SPEC)
    dataset_bytes = DATASET.read_bytes()
    rows = [json.loads(line) for line in dataset_bytes.decode('utf-8').splitlines() if line.strip()]
    training = selected_training_rows(rows)
    training_texts = {r['input'] for r in training}
    held_texts = {r['input'] for r in rows if r.get('split') != 'train'}
    canonical_overlap = training_texts & held_texts
    if canonical_overlap:
        raise ValueError('Canonical train and held inputs overlap exactly')
    train_start = time.perf_counter()
    model = fit(rows)
    train_seconds = time.perf_counter() - train_start
    # Freeze the trained artifact before opening any challenge input/target.
    model_hash = save('model.json', model)
    challenge_bytes = CHALLENGE.read_bytes()
    challenge = json.loads(challenge_bytes.decode('utf-8'))
    challenge_rows = challenge['results']
    if len(challenge_rows) != 42:
        raise ValueError('Expected every one of the 42 recorded development challenge rows')
    overlap = [row['corpus_row'] for row in challenge_rows if row['input'] in training_texts]
    if overlap:
        raise ValueError('Development challenge overlaps canonical training data')
    records, raw_predictions, prediction_seconds = [], [], []
    for row in challenge_rows:
        text = row['input']
        if digest_bytes(text.encode('utf-8')) != row['input_sha256']:
            raise ValueError('Challenge input hash mismatch')
        predict_start = time.perf_counter()
        proposal = predict(text, model, make_task)
        latency = time.perf_counter() - predict_start
        prediction_seconds.append(latency)
        # Targets are supplied to the auditor only after predictions exist.
        target = {key: row['target'][key] for key in ('label', 'state')}
        probe_class = row['probe_class']
        if probe_class not in ('STEERING', 'PARAPHRASE'):
            raise ValueError('Undeclared challenge class')
        stratum = 'NOVEL_ATTACK' if probe_class == 'STEERING' else 'LEXICON_FREE'
        identity = f"development-{row['corpus_row']}"
        records.append({'id': identity, 'input': text, 'stratum': stratum,
                        'target': target, 'raw_output': proposal['raw_output'],
                        'probabilities': proposal['probabilities']})
        raw_predictions.append({'id': identity, 'input': text, 'input_sha256': row['input_sha256'],
                                'probe_class': probe_class, 'declared_target': target,
                                'prediction_seconds': latency, **proposal})
    thresholds_path = CANONICAL / 'PROMOTION_THRESHOLDS.json'
    thresholds_bytes = thresholds_path.read_bytes()
    thresholds = json.loads(thresholds_bytes.decode('utf-8'))
    report = evaluate_records(records, thresholds, evaluation_scope='DEVELOPMENT')
    # Negative control is selected from training counts, never challenge labels.
    majority_label = max(model['labels'], key=lambda label: model['train_label_counts'][label])
    prior_probabilities = {label: model['train_label_counts'][label] / model['train_rows']
                           for label in model['labels']}
    majority_records = []
    for record in records:
        baseline_output = {'label': majority_label,
                           'state': 'REVIEW' if majority_label == 'REVIEW' else 'MEASURED',
                           'evidence': [] if majority_label == 'REVIEW' else [record['input']]}
        majority_records.append({**record, 'raw_output': stable_json(baseline_output),
                                 'probabilities': prior_probabilities})
    majority_report = evaluate_records(majority_records, thresholds, evaluation_scope='DEVELOPMENT')
    save('majority-control.json', {'selection': 'ARGMAX_TRAINING_LABEL_FREQUENCY',
                                   'label': majority_label, 'probabilities': prior_probabilities,
                                   'qualification': majority_report,
                                   'limitations': ['A majority classifier may score better on raw accuracy while failing every positive report; neither descriptive ECE nor attack refusal alone establishes usefulness.']})
    save('predictions.json', raw_predictions)
    save('qualification.json', report)
    save('qualification-records.json', records)
    provenance = Counter(r['label_provenance'] for r in training)
    elapsed = time.perf_counter() - start
    receipt = {
        'schema': 'szl.cpu-model-experiment/v1', 'state': 'EXECUTED',
        'started_utc': started, 'completed_utc': datetime.now(timezone.utc).isoformat(),
        'evaluation_scope': 'DEVELOPMENT_PREVIOUSLY_EXPOSED_CHALLENGE',
        'promotion_status': 'NOT_PROMOTABLE', 'release_authorization': 'NONE',
        'training_spec_sha256': spec_hash, 'model_sha256': model_hash,
        'canonical_dataset_sha256': digest_bytes(dataset_bytes),
        'challenge_sha256': digest_bytes(challenge_bytes),
        'thresholds_sha256': digest_bytes(thresholds_bytes),
        'training_projection_sha256': model['training_projection_sha256'],
        'train_rows': model['train_rows'], 'train_label_counts': model['train_label_counts'],
        'train_label_provenance': dict(provenance),
        'held_rows_not_trained': sum(r.get('split') != 'train' for r in rows),
        'exact_train_held_input_overlap': len(canonical_overlap),
        'exact_train_challenge_input_overlap': len(overlap),
        'challenge_labels_used_for_training_or_selection': False,
        'model_saved_before_challenge_read': True,
        'semantic_family_independence': 'NOT_ESTABLISHED',
        'additional_training_data': 'NONE',
        'training_seconds': train_seconds, 'wall_seconds': elapsed,
        'prediction_seconds_total': sum(prediction_seconds),
        'prediction_seconds_max': max(prediction_seconds),
        'runtime': {'python': platform.python_version(), 'platform': platform.platform(), 'processor': 'CPU'},
        'rows_scored': len(records), 'joint_correct': report['joint_correct'],
        'metrics': report['metrics'], 'criteria': report['criteria'],
        'majority_negative_control': {'selected_label': majority_label,
                                      'joint_correct': majority_report['joint_correct'],
                                      'metrics': majority_report['metrics'],
                                      'classification_usefulness': 'Evaluate positive accuracy alongside aggregate accuracy and refusal'},
        'historical_adapter_comparison': {
            'rows': len(challenge_rows),
            'joint_correct': sum(bool(r['joint_exact']) for r in challenge_rows),
            'refusal_correct': sum(bool(r['refusal_correct']) for r in challenge_rows),
            'scope': 'Same previously exposed challenge; different model and runtime; neither is independently qualified'},
        'source_sha256': {str(path.relative_to(WORKSPACE)): digest_bytes(path.read_bytes())
                          for path in (HERE / 'model.py', Path(__file__),
                                       CANONICAL / 'src/szl_triage/proposal_task.py',
                                       CANONICAL / 'src/szl_triage/qualification.py')},
        'limitations': [
            'CPU linear baseline is a newly trained independent model; it is not the historical adapter or an SZL-1 release.',
            'Training labels are engine-derived; no independent semantic label ratification is established.',
            'The 42-row challenge has already been inspected in prior development; exact disjoint inputs do not establish semantic independence.',
            'PARAPHRASE-to-LEXICON_FREE is a declared evaluation mapping; IN_LEXICON is absent and remains UNAVAILABLE.',
            'Probabilities are coherent softmax model scores; measured ECE is descriptive, not a calibrated selective-risk guarantee.',
            'Literal span extraction establishes occurrence only; semantic relevance is NOT_ESTABLISHED.',
            'No training thresholds or model configurations were selected using challenge outcomes.',
            'No GitHub, Hugging Face, GPU, billing, or deployment mutations occurred in this experiment.']}
    save('receipt.json', receipt)
    if digest_bytes(DATASET.read_bytes()) != receipt['canonical_dataset_sha256']:
        raise ValueError('Canonical training bytes changed during the experiment')
    if digest_bytes(CHALLENGE.read_bytes()) != receipt['challenge_sha256']:
        raise ValueError('Challenge bytes changed during the experiment')
    print(json.dumps({'state': receipt['state'], 'training_rows': model['train_rows'],
                      'features': len(model['vocabulary']), 'joint_correct': report['joint_correct'],
                      'rows': len(records), 'metrics': report['metrics'],
                      'promotion_status': receipt['promotion_status'],
                      'training_seconds': train_seconds}, indent=2))


if __name__ == '__main__':
    main()

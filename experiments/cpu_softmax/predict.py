"""Use an immutable diagnostic study locally; never authorizes promotion."""
from __future__ import annotations

import argparse
import math
from pathlib import Path, PurePosixPath
import sys

from .model import LABELS, SPEC, digest_bytes, predict, stable_json
from szl_triage.proposal_task import make_task
from szl_triage.qualification import strict_json

HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parents[1]


def verify_study(repository=REPOSITORY):
    repository = Path(repository).resolve()
    manifest_path = repository / 'experiments/cpu_softmax/STUDY_MANIFEST.json'
    manifest = strict_json(manifest_path.read_text(encoding='utf-8'))
    if (manifest.get('schema') != 'szl.cpu-softmax-study-manifest/v1'
            or manifest.get('promotion_status') != 'NOT_PROMOTABLE'
            or manifest.get('runtime_integration') != 'NONE'
            or manifest.get('evaluation_scope') != 'DEVELOPMENT_PREVIOUSLY_EXPOSED_CHALLENGE'):
        raise ValueError('Unrecognized or overclaiming study manifest')
    files = manifest.get('files')
    if not isinstance(files, dict) or not files:
        raise ValueError('Study manifest has no file bindings')
    for name, expected in files.items():
        path = PurePosixPath(name)
        if (path.is_absolute() or path.as_posix() != name or '..' in path.parts
                or '\\' in name or ':' in name or not isinstance(expected, str)
                or len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected)):
            raise ValueError('Invalid study file binding')
        file_path = repository / name
        if not file_path.resolve().is_relative_to(repository):
            raise ValueError('Study binding escapes the repository')
        if digest_bytes(file_path.read_bytes()) != expected:
            raise ValueError(f'Study file differs from manifest: {name}')
    required = {
        'experiments/cpu_softmax/model.py', 'experiments/cpu_softmax/predict.py',
        'experiments/cpu_softmax/artifacts/model.json',
        'experiments/cpu_softmax/artifacts/receipt.json',
        'src/szl_triage/proposal_task.py', 'src/szl_triage/qualification.py',
        'PROMOTION_THRESHOLDS.json',
    }
    if not required <= files.keys():
        raise ValueError('Study manifest omits a required source or artifact')
    return manifest


def load_recorded_model(repository=REPOSITORY):
    repository = Path(repository)
    verify_study(repository)
    artifacts = repository / 'experiments/cpu_softmax/artifacts'
    model_bytes = (artifacts / 'model.json').read_bytes()
    if len(model_bytes) > 1_000_000:
        raise ValueError('Recorded model exceeds the bounded baseline size')
    receipt = strict_json((artifacts / 'receipt.json').read_text(encoding='utf-8'))
    if digest_bytes(model_bytes) != receipt['model_sha256']:
        raise ValueError('Model bytes no longer bind the recorded experiment')
    model = strict_json(model_bytes.decode('utf-8'))
    vocabulary = model['vocabulary']
    if (model['schema'] != 'szl.cpu-softmax-model/v1' or model['labels'] != list(LABELS)
            or model['spec'] != SPEC or not vocabulary or any(type(t) is not str for t in vocabulary)
            or len(set(vocabulary)) != len(vocabulary)
            or len(vocabulary) > SPEC['maximum_features']
            or model['vocabulary_index'] != {t: i for i, t in enumerate(vocabulary)}
            or len(model['idf']) != len(vocabulary) or len(model['weights']) != len(LABELS)
            or len(model['bias']) != len(LABELS)
            or any(len(row) != len(vocabulary) for row in model['weights'])):
        raise ValueError('Recorded model structure differs from the frozen baseline')
    numbers = model['idf'] + model['bias'] + [v for row in model['weights'] for v in row]
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in numbers):
        raise ValueError('Recorded model contains invalid numeric parameters')
    if any(value <= 0 for value in model['idf']):
        raise ValueError('Recorded IDF values must be positive')
    return model, digest_bytes(model_bytes)


def main():
    parser = argparse.ArgumentParser(description='CPU diagnostic baseline; unqualified advisory only')
    parser.add_argument('--text', help='Exact report; omit to read a bounded report from standard input')
    args = parser.parse_args()
    report = args.text if args.text is not None else sys.stdin.read(2049)
    model, model_hash = load_recorded_model()
    result = predict(report, model, make_task)
    print(stable_json({'schema': 'szl.cpu-baseline-advisory/v1', 'report': report,
                       'model_sha256': model_hash, 'promotion_status': 'NOT_PROMOTABLE',
                       'release_authorization': 'NONE',
                       'receipt_binding': 'CONTENT_IDENTITY_ONLY_REQUIRES_TRUSTED_GIT_SOURCE', **result}))


if __name__ == '__main__':
    main()

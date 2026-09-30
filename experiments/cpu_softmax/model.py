"""Independent, standard-library six-class softmax baseline; advisory only.

Training and inference know no evaluation labels. Probabilities are normalized
model scores, not demonstrated calibration or semantic evidence guarantees.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
import random
import re

LABELS = ('BILLING', 'BUG', 'FEATURE', 'REVIEW', 'SECURITY', 'SUPPORT')
SPEC = {
    'schema': 'szl.cpu-softmax-training-spec/v1', 'seed': 11,
    'feature_method': 'Unicode casefolded word unigrams and adjacent word bigrams; train-only TF-IDF; L2 normalized',
    'minimum_document_frequency': 2, 'maximum_features': 1536,
    'epochs': 80, 'initial_learning_rate': 0.25,
    'learning_rate_decay_per_epoch': 0.02, 'l2_epoch_decay': 0.0001,
    'class_weighting': 'NONE', 'temperature': 1.0,
    'decision': 'Argmax of six-class softmax, alphabetical tie break; no test-label overrides or manually chosen abstention threshold',
    'training_source': 'Canonical split=train rows only; no authority augmentation',
    'label_status': 'ENGINE_DERIVED; semantic ratification and family independence not established',
    'evaluation_scope': 'DEVELOPMENT', 'promotion_status': 'NOT_PROMOTABLE',
    'release_authorization': 'NONE',
}
WORD_PATTERN = re.compile(r"[^\W_]+(?:['\u2019][^\W_]+)?", re.UNICODE)


def stable_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def terms(text: str) -> Counter:
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Input must be nonempty text')
    text.encode('utf-8')
    words = WORD_PATTERN.findall(text.casefold())
    result = Counter('u:' + word for word in words)
    result.update('b:' + a + ' ' + b for a, b in zip(words, words[1:]))
    return result


def selected_training_rows(rows):
    selected = []
    for row in rows:
        # Held rows are never a source of labels or learned vocabulary.
        if row.get('split') != 'train':
            continue
        text, label = row.get('input'), row.get('label')
        if label not in LABELS:
            raise ValueError('Unknown training label')
        terms(text)
        if row.get('state') != ('REVIEW' if label == 'REVIEW' else 'MEASURED'):
            raise ValueError('Training label/state conflict')
        selected.append({'input': text, 'label': label,
                         'state': row['state'],
                         'template_family': row.get('template_family'),
                         'content_family': row.get('content_family'),
                         'label_provenance': row.get('label_provenance', 'UNKNOWN')})
    if not selected:
        raise ValueError('No canonical training rows')
    if set(r['label'] for r in selected) != set(LABELS):
        raise ValueError('Training data must represent all six labels')
    return selected


def features(text, model):
    counts = terms(text)
    index = model['vocabulary_index']
    result = {index[t]: (1 + math.log(n)) * model['idf'][index[t]]
              for t, n in counts.items() if t in index}
    norm = math.sqrt(math.fsum(v * v for v in result.values()))
    return {i: v / norm for i, v in result.items()} if norm else {}


def probabilities_from_features(x, model):
    logits = [model['bias'][k] + math.fsum(model['weights'][k][i] * v for i, v in x.items())
              for k in range(len(LABELS))]
    maximum = max(logits)
    exp = [math.exp(score - maximum) for score in logits]
    total = math.fsum(exp)
    return [value / total for value in exp]


def fit(rows, *, spec=None):
    spec = dict(SPEC if spec is None else spec)
    train = selected_training_rows(rows)
    doc_frequency = Counter()
    for row in train:
        doc_frequency.update(terms(row['input']).keys())
    vocabulary = [t for t, n in sorted(doc_frequency.items(), key=lambda pair: (-pair[1], pair[0]))
                  if n >= spec['minimum_document_frequency']][:spec['maximum_features']]
    # Selection order is deterministic; feature index itself is alphabetical.
    vocabulary.sort()
    if not vocabulary:
        raise ValueError('Training vocabulary is empty')
    model = {
        'schema': 'szl.cpu-softmax-model/v1', 'labels': list(LABELS), 'spec': spec,
        'vocabulary': vocabulary, 'vocabulary_index': {t: i for i, t in enumerate(vocabulary)},
        'idf': [math.log((1 + len(train)) / (1 + doc_frequency[t])) + 1 for t in vocabulary],
        'weights': [[0.0] * len(vocabulary) for _ in LABELS], 'bias': [0.0] * len(LABELS),
        'train_rows': len(train), 'train_label_counts': dict(Counter(r['label'] for r in train)),
        'training_projection_sha256': digest_bytes(stable_json(train).encode('utf-8')),
    }
    examples = [(features(row['input'], model), LABELS.index(row['label'])) for row in train]
    rng = random.Random(spec['seed'])
    order = list(range(len(examples)))
    for epoch in range(spec['epochs']):
        rng.shuffle(order)
        learning_rate = spec['initial_learning_rate'] / (1 + spec['learning_rate_decay_per_epoch'] * epoch)
        for position in order:
            x, gold = examples[position]
            probabilities = probabilities_from_features(x, model)
            for k in range(len(LABELS)):
                gradient = probabilities[k] - (1.0 if k == gold else 0.0)
                model['bias'][k] -= learning_rate * gradient
                for i, value in x.items():
                    model['weights'][k][i] -= learning_rate * gradient * value
        decay = 1 - learning_rate * spec['l2_epoch_decay']
        for weight in model['weights']:
            for i in range(len(weight)):
                weight[i] *= decay
    return model


def choose(text, model):
    x = features(text, model)
    values = probabilities_from_features(x, model)
    # Python max selects the first label on exact ties; LABELS is alphabetical.
    predicted = max(range(len(LABELS)), key=lambda k: values[k])
    return LABELS[predicted], dict(zip(LABELS, values)), x


def evidence_id(task, label, model):
    """Select one exact canonical candidate. Selection cannot prove support."""
    k = LABELS.index(label)
    index = model['vocabulary_index']
    candidates = [s for s in task.candidates if s.id != 's000']
    if not candidates:
        candidates = list(task.candidates)
    if not candidates:
        raise ValueError('No valid literal evidence candidate')
    def contribution(span):
        return math.fsum(model['weights'][k][index[t]] * n
                         for t, n in terms(span.text).items() if t in index)
    return max(candidates, key=contribution).id


def predict(text, model, make_task):
    task = make_task(text)
    label, probabilities, _ = choose(text, model)
    ids = [] if label == 'REVIEW' else [evidence_id(task, label, model)]
    raw_choice = stable_json({'label': label, 'evidence_ids': ids})
    decoded = task.decode(raw_choice)
    output = {k: decoded[k] for k in ('label', 'state', 'evidence')}
    return {'raw_choice': raw_choice, 'raw_output': stable_json(output),
            'probabilities': probabilities, 'decoded': decoded,
            'confidence_status': 'UNVALIDATED_NORMALIZED_MODEL_PROBABILITIES'}

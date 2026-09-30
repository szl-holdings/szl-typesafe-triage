"""Audit all six sealed performance criteria offline; no model load or writes to history."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from szl_triage.qualification import evaluate_records, strict_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--records', type=Path, help='Versioned evaluation rows as JSONL')
    source.add_argument('--challenge-receipt', type=Path, help='Re-audit the entire existing challenge as DEVELOPMENT')
    parser.add_argument('--thresholds', type=Path, default=ROOT / 'PROMOTION_THRESHOLDS.json')
    parser.add_argument('--output', type=Path, required=True, help='New, exclusive output path')
    args = parser.parse_args(argv)
    path = args.records or args.challenge_receipt
    data = path.read_bytes()
    if args.challenge_receipt:
        receipt = strict_json(data.decode('utf-8-sig'))
        results = receipt['results']
        if receipt.get('state') != 'EXECUTED' or receipt.get('rows_completed') != len(results):
            raise ValueError('Incomplete or unexecuted challenge receipt')
        if len(results) != 42:
            raise ValueError('Challenge audit must retain all 42 rows')
        rows = [{'id': r['input_sha256'], 'input': r['input'],
                 'stratum': 'NOVEL_ATTACK' if r['probe_class'] == 'STEERING' else 'LEXICON_FREE',
                 'target': {k:r['target'][k] for k in ('label','state')},
                 'raw_output': r['raw_output'], 'probabilities': None} for r in results]
    else:
        rows = [strict_json(line) for line in data.decode('utf-8-sig').splitlines() if line.strip()]
    thresholds_bytes = args.thresholds.read_bytes()
    report = evaluate_records(rows, strict_json(thresholds_bytes.decode('utf-8-sig')))
    report['created_utc'] = datetime.now(timezone.utc).isoformat()
    report['input_bindings'] = {
        'prediction_file_sha256': hashlib.sha256(data).hexdigest(),
        'thresholds_file_sha256': hashlib.sha256(thresholds_bytes).hexdigest(),
        'evaluator_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'metric_source_sha256': hashlib.sha256((ROOT/'src/szl_triage/qualification.py').read_bytes()).hexdigest(),
        'candidate_execution_binding': 'NOT_ESTABLISHED_BY_OFFLINE_AUDIT',
    }
    with args.output.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write('\n')
    print(json.dumps({'metric_status':report['metric_status'], 'promotion_status':report['promotion_status'],
                      'criteria':report['criteria']}))
    return 0 if report['metric_status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())

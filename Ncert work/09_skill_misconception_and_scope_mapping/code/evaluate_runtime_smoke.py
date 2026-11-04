"""Run a local-only publisher-data calibration smoke; it does not estimate accuracy."""
import hashlib
import json
from collections import Counter

from diagnose_eedi import EediDiagnostic, PHASE
from pipeline import read_jsonl, run_record, sha256


def select(rows, source, limit):
    selected, seen = [], set()
    for row in sorted(rows, key=lambda r: hashlib.sha256(r['example_id'].encode()).hexdigest()):
        if not row['source_dataset'].startswith(source) or row['split'] != 'calibration':
            continue
        if source == 'map-' and (row['correctness'] != 'selected_answer_incorrect' or not row['student_working']):
            continue
        group = row['problem_group_id'] if source == 'eedi-' else (row['problem_group_id'], row['gold_misconception_text'])
        if group in seen:
            continue
        seen.add(group); selected.append(row)
        if len(selected) == limit:
            break
    if len(selected) != limit:
        raise ValueError('Insufficient calibration examples for declared smoke')
    return selected


def main():
    path = PHASE / 'outputs/diagnostic_examples.jsonl'
    catalogue_manifest = PHASE / 'outputs/eedi_catalogue_manifest.json'
    with run_record('09_skill_misconception_and_scope_mapping', [path, catalogue_manifest]) as run:
        examples = read_jsonl(path)
        cases = select(examples, 'eedi-', 6) + select(examples, 'map-', 8)
        protocol = dict(split='calibration only', selection='Stable example-ID hash; one Eedi question and one MAP question/label pair',
                        cases=[r['example_id'] for r in cases], source_sha256=sha256(path),
                        note='Remote model disabled; no MAP-to-Eedi ID equivalence assumed; no student data in public metrics')
        protocol_path = PHASE / 'logs' / (run['run_id'] + '-runtime-smoke-protocol.json')
        protocol_path.write_text(json.dumps(protocol, indent=2) + '\n', encoding='utf-8')
        diagnostic = EediDiagnostic()
        counters = {'eedi_no_working': Counter(), 'map_with_working': Counter()}
        for index, case in enumerate(cases, 1):
            kind = 'eedi_no_working' if case['source_dataset'].startswith('eedi-') else 'map_with_working'
            result = diagnostic.diagnose(case['question'], case['student_answer'], case['student_working'] or '',
                                         answer_is_incorrect=True)
            if result.get('confirmed') or result.get('persistent'):
                raise ValueError('Unverified misconception was confirmed')
            counters[kind][result['status']] += 1
            if result.get('reason'):
                counters[kind]['reason:' + result['reason']] += 1
            print(f'{index}/{len(cases)} {kind}: {result["status"]}', flush=True)
        metrics = dict(run_id=run['run_id'], protocol_sha256=sha256(protocol_path),
                       eedi_no_working=dict(counters['eedi_no_working']), map_with_working=dict(counters['map_with_working']),
                       cases=len(cases), map_label_accuracy=None, wrong_confident_diagnosis_rate=None,
                       limitations=['Local retrieval/guard smoke; remote model not called', 'Calibration smoke, not held-out accuracy', 'Eedi distractors are not student responses',
                                    'MAP and Eedi use different label namespaces; no exact label bridge',
                                    'All model selections remain unconfirmed candidates'])
        output = PHASE / 'outputs/eedi_runtime_smoke_metrics.json'
        output.write_text(json.dumps(metrics, indent=2) + '\n', encoding='utf-8')
        run['outputs'].extend([protocol_path, output]); run['counts'] = metrics
        print(json.dumps(metrics), flush=True)


if __name__ == '__main__':
    main()

"""Original Eedi catalogue labels for bounded, working-corroborated candidates."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / '00_setup_and_scope/code'))
from pipeline import ROOT, local_path, read_csv, read_jsonl, sha256
from error_rules import corroborated_errors
from load_eedi_catalogue import catalogue

PHASE = ROOT / '09_skill_misconception_and_scope_mapping'


class EediDiagnostic:
    def __init__(self):
        manifest = json.loads((PHASE / 'outputs/eedi_catalogue_manifest.json').read_text(encoding='utf-8'))
        for relative, digest in manifest['input_sha256'].items():
            if sha256(local_path(relative)) != digest:
                raise ValueError('Pinned Eedi source changed')
        source = local_path(next(p for p in manifest['input_sha256'] if p.endswith('data/misconception-map.csv')))
        constructs = local_path(next(p for p in manifest['input_sha256'] if p.endswith('data/construct-map.csv')))
        self.rows = catalogue(read_csv(constructs), read_csv(source))
        saved = read_jsonl(PHASE / 'outputs/misconceptions.jsonl')
        if saved != self.rows or len(saved) != manifest['misconception_count']:
            raise ValueError('Eedi catalogue identity/order differs from pinned source')
        self.by_id = {r['misconception_id']: r for r in self.rows}

    def diagnose(self, question, answer, working='', *, answer_is_incorrect):
        if any(not isinstance(v, str) for v in (question, answer, working)) or not question.strip() or not answer.strip():
            raise ValueError('Question, answer and working must be text; question and answer are required')
        if len(question) > 8000 or len(answer) > 128 or len(working) > 8000:
            raise ValueError('Input exceeds safe size')
        if answer_is_incorrect is not True:
            return {'status': 'not_assessed', 'misconception_id': None, 'persistent': False}
        result = {'status': 'need_working', 'misconception_id': None, 'candidates': [],
                  'confirmed': False, 'persistent': False, 'catalogue': 'eedi-2ae0839debf73c0c'}
        if not working.strip():
            result['prompt'] = 'Please show the calculation or reasoning you used.'
            return result
        supported = corroborated_errors(question, answer, working)
        if len(supported) == 1:
            row = self.by_id.get(supported[0]['misconception_id'])
            if row is None:
                result.update(status='needs_review', reason='Rule ID is absent from the pinned catalogue')
                return result
            result['candidates'] = [{'misconception_id': row['misconception_id'], 'text': row['text']}]
            result.update(status='working_supported_candidate', misconception_id=supported[0]['misconception_id'],
                          evidence=supported[0]['evidence'], method=supported[0]['method'])
        else:
            result.update(status='insufficient_evidence', reason='No unique checked wrong method in explicit working',
                          prompt='Show the calculation you used, for example 50 * 20 = 1000.')
        result['remote_selector_enabled'] = False
        return result


def main():
    data = json.load(sys.stdin)
    result = EediDiagnostic().diagnose(data['question'], data['answer'], data.get('working', ''),
                                      answer_is_incorrect=data.get('answer_is_incorrect'))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()

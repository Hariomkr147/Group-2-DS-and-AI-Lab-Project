"""Exercise the running local app with synthetic Hariom attempts; no competition data."""
import json
import time
import urllib.request
import urllib.error
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = 'http://127.0.0.1:8765'
http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
events = []
replies = []


def call(path, body=None):
    request = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(),
                                     headers={'Content-Type': 'application/json'})
    try:
        with http.open(request, timeout=180) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = json.load(error)
        (HERE/'logs/live_checks_current.json').write_text(json.dumps(dict(passed=False,http_status=error.code,error=detail),indent=2))
        raise SystemExit('Live check stopped: ' + str(detail.get('message',detail.get('detail','HTTP '+str(error.code))))) from None


def message(sid, text, working='', intent='message'):
    body = dict(text=text, working=working, intent=intent, request_id=uuid.uuid4().hex)
    started = time.monotonic()
    result = call(f'/api/sessions/{sid}/messages', body)
    assert call(f'/api/sessions/{sid}/messages', body) == result
    diagnostic = result.get('misconception') or {}
    if result['action'] == 'EXPLAIN':
        assert 'From NCERT:' in result['reply'] and result['citations']
    if intent in {'explain','hint','practice'}:
        assert not diagnostic
    if diagnostic.get('misconception_id'):
        assert diagnostic['misconception_id'] in {c['misconception_id'] for c in diagnostic['candidates']}
    assert diagnostic.get('confirmed') is not True and diagnostic.get('persistent') is not True
    event = dict(action=result['action'], concept=result['session']['current_concept']['id'],
                 model=result.get('model_status'), diagnostic=diagnostic.get('status'),
                 diagnostic_model=diagnostic.get('model_origin'), candidates=len(diagnostic.get('candidates', [])),
                 hint_level=result.get('hint_level'), seconds=round(time.monotonic()-started, 2))
    if result.get('model_status') not in (None, 'controller'):
        assert result['model_status'] == 'fine_tuned_qwen'
    events.append(event)
    replies.append(dict(action=result['action'],reply=result['reply'],citations=result.get('citations', [])))
    print(json.dumps(event), flush=True)
    return result['session']


if __name__ == '__main__':
    status = call('/api/status')
    manifest=json.loads((Path(__file__).resolve().parent.parent/'Ncert work/07_concepts_questions_and_chunks/outputs/content_manifest.json').read_text())
    assert status['kt_loaded'] and status['kt'].startswith('AKT') and status['rag_chunks'] == manifest['accepted_chunks'] and status['eedi_entries'] == 8117
    state = call('/api/sessions', dict(target_concept_id='percentages', learner_id='Hariom'))
    sid = state['session_id']
    assert state['active_question'] is None
    state = message(sid, 'Explain concept', intent='explain')
    assert state['active_question'] is not None
    for level in (1, 2, 3):
        state = message(sid, 'I would like a hint.', intent='hint')
        assert events[-1]['hint_level'] == level and events[-1]['candidates'] == 0
    assert len({r['reply'] for r in replies if r['action'] == 'HINT'}) == 3
    assert call(f'/api/sessions/{sid}/progress')['total_attempts'] == 0
    state = message(sid, 'Tell me a joke')
    assert call(f'/api/sessions/{sid}/progress')['total_attempts'] == 0
    state = message(sid, '0.75%', '3 / 4 = 0.75', intent='answer')
    if not state['is_backtracking']:
        state = message(sid, '0', intent='answer')
    assert state['is_backtracking']
    assert state['current_concept']['id'] == 'fraction_multiplication'
    progress = call(f'/api/sessions/{sid}/progress')
    assert sum(c['origin'] == 'akt_prediction' for c in progress['concept_readiness']) == 3
    questions = {q['id']: q for values in json.loads((HERE/'data/private_questions.json').read_text()).values() for q in values}
    state = message(sid, questions[state['active_question']['id']]['key'], intent='answer')
    assert state['current_concept']['id'] == 'percentages' and not state['is_backtracking']
    state = message(sid, questions[state['active_question']['id']]['key'], intent='answer')
    assert state['state'] == 'ADVANCE' and state['active_question'] is not None
    while state['active_question']:
        state = message(sid, questions[state['active_question']['id']]['key'], intent='answer')
    assert state['state'] == 'DONE' and state['active_question'] is None
    before = call(f'/api/sessions/{sid}/progress')['total_attempts']
    state = message(sid, '0')
    assert state['state'] == 'DONE' and state['active_question'] is None
    assert call(f'/api/sessions/{sid}/progress')['total_attempts'] == before
    restarted = message(sid,'Try a question',intent='practice')
    assert restarted['active_question'] is not None
    assert restarted['practice_progress']['round'] == 2
    assert call(f'/api/sessions/{sid}/progress')['total_attempts'] == before
    science = call('/api/concepts')
    science_id = next(c['id'] for c in science if c['subject'] == 'science')
    session = call('/api/sessions', dict(target_concept_id=science_id, learner_id='Hariom'))
    assert session['active_question'] is None
    result = call(f"/api/sessions/{session['session_id']}/messages",
                  dict(text='I would like a hint.', intent='hint', request_id=uuid.uuid4().hex))
    assert len(result['citations']) > 0
    assert call(f"/api/sessions/{session['session_id']}/progress")['total_attempts'] == 0
    report = dict(status=status, events=events, replies=replies, maths_attempts=before,
                  akt_readiness=progress['concept_readiness'], science_hint_model=result['model_status'],
                  science_citations=len(result['citations']), science_reply=result['reply'], passed=True)
    (HERE/'logs/live_checks.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (HERE/'logs/live_checks_current.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('LIVE CHECKS PASSED', flush=True)

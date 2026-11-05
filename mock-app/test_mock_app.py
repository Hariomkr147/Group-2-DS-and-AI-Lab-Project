import io
import json
import sqlite3
import threading
import unittest
import urllib.error
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from server import Engine, app, numeric, leaks
from llm import ResponseModel, ModelError, ModelUnavailable, endpoint_config


class MockAppChecks(unittest.TestCase):
    def test_endpoint_config_preserves_url_and_key_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);connection=root/'phase/connection.json';connection.parent.mkdir()
            (root/'.env').write_text('API_KEY=test-only-secret\n')
            connection.write_text(json.dumps({'base_url':'https://example.trycloudflare.com/'}))
            with patch('llm.CONNECTION',connection):
                self.assertEqual(endpoint_config(),('https://example.trycloudflare.com','test-only-secret'))
                for url in ('http://example.trycloudflare.com','https://example.trycloudflare.com/path',
                            'https://example.trycloudflare.com?key=value','https://example.trycloudflare.com.evil.test'):
                    connection.write_text(json.dumps({'base_url':url}))
                    endpoint_config.cache_clear()
                    with self.assertRaises(ValueError):endpoint_config()
                connection.write_text(json.dumps({'base_url':'https://example.trycloudflare.com'}))
                (root/'.env').write_text('API_KEY=one\nAPI_KEY=two\n')
                with self.assertRaises(ValueError):endpoint_config()

    def setUp(self):
        endpoint_config.cache_clear()
        self.addCleanup(endpoint_config.cache_clear)
        self.engine = Engine.__new__(Engine)
        self.engine.db = sqlite3.connect(':memory:', check_same_thread=False)
        self.engine.db.execute('CREATE TABLE sessions(id TEXT PRIMARY KEY,payload TEXT)')
        self.engine.db.execute('CREATE TABLE replies(session_id TEXT,request_id TEXT,payload TEXT,PRIMARY KEY(session_id,request_id))')
        self.engine.questions = json.loads((Path(__file__).parent/'data/private_questions.json').read_text())
        self.engine.concepts = {cid:dict(id=cid,title=cid,level=1) for cid in self.engine.questions}
        self.engine.parents = {cid:[] for cid in self.engine.questions}
        self.engine.parents['percentages'] = ['fractions']
        self.engine.evidence = lambda *args:[]
        self.engine.guidance = Mock(return_value=('One step at a time.','fine_tuned_qwen'))
        self.engine.kt = Mock(predict=Mock(return_value={}))
        self.engine.eedi = Mock()
        self.engine.eedi.diagnose.return_value = dict(status='needs_review',confirmed=False,persistent=False,
            candidates=[dict(misconception_id='14611',text='Missing a conversion step')])
        self.engine.llm = Mock(ask=Mock(return_value=('14611','fine_tuned_qwen')))

    def tearDown(self):
        self.engine.db.close()

    def start(self, cid='percentages'):
        sid = self.engine.create(cid,'Hariom')['session_id']
        self.engine.respond(sid,'Try a question',intent='practice')
        return sid

    def test_learning_first_and_private_key_not_public(self):
        session = self.engine.create('fractions','Hariom')
        self.assertIsNone(session['active_question'])
        result = self.engine.respond(session['session_id'],'Try a question',intent='practice')
        self.assertNotIn('key',result['session']['active_question'])
        self.assertNotIn('official_answer_text',json.dumps(result))
        self.engine.eedi.diagnose.assert_not_called()

    def test_backtracking_return_completion_and_request_deduplication(self):
        sid = self.start()
        self.engine.respond(sid,'0',intent='answer',request_id='one')
        self.engine.respond(sid,'0',intent='answer',request_id='one')
        self.assertEqual(len(self.engine.get(sid)['attempts']),1)
        two = self.engine.respond(sid,'0',intent='answer',request_id='two')
        self.assertEqual(two['action'],'BACKTRACK')
        self.assertEqual(two['session']['current_concept']['id'],'fractions')
        back = self.engine.respond(sid,self.engine.questions['fractions'][0]['key'],intent='answer',request_id='three')
        self.assertEqual(back['session']['current_concept']['id'],'percentages')
        following = self.engine.respond(sid,'My answer is 75%',request_id='four')
        self.assertEqual(following['action'],'ADVANCE')
        self.assertIsNotNone(following['session']['active_question'])
        pool = {q['id']:q for _,_,q in self.engine.practice_pool(self.engine.get(sid))}
        while following['session']['active_question']:
            qid = following['session']['active_question']['id']
            following = self.engine.respond(sid,pool[qid]['key'],intent='answer')
        done = following
        self.assertEqual(done['session']['state'],'DONE')
        self.assertIsNone(done['session']['active_question'])
        for text in ['0','hint']:
            self.assertEqual(self.engine.respond(sid,text)['action'],'DONE')
        attempts = len(self.engine.get(sid)['attempts'])
        self.assertEqual(attempts,2+len(pool))
        self.engine.eedi.diagnose.assert_not_called()
        explanation = self.engine.respond(sid,'Explain concept')
        self.assertEqual(explanation['action'],'EXPLAIN')
        self.assertIsNone(explanation['session']['active_question'])
        self.engine.respond(sid,'0',intent='answer')
        self.assertEqual(len(self.engine.get(sid)['attempts']),attempts)

    def test_one_correct_result_continues_and_exhausted_pool_can_be_repeated(self):
        sid = self.start()
        result = self.engine.respond(sid,'75',intent='answer')
        self.assertEqual(result['action'],'ADVANCE')
        self.assertNotEqual(result['session']['active_question']['id'],self.engine.questions['percentages'][0]['id'])
        pool = {q['id']:q for _,_,q in self.engine.practice_pool(self.engine.get(sid))}
        seen = {self.engine.questions['percentages'][0]['id']}
        while result['session']['active_question']:
            qid = result['session']['active_question']['id']
            self.assertNotIn(qid,seen);seen.add(qid)
            result = self.engine.respond(sid,pool[qid]['key'],intent='answer')
        before = len(self.engine.get(sid)['attempts'])
        restarted = self.engine.respond(sid,'Try a question',request_id='restart')
        self.assertEqual(restarted['action'],'ASK')
        self.assertIsNotNone(restarted['session']['active_question'])
        self.assertIn('review round',restarted['reply'])
        self.assertEqual(restarted['session']['practice_progress']['round'],2)
        self.assertEqual(len(self.engine.get(sid)['attempts']),before)
        self.assertEqual(self.engine.respond(sid,'Try a question',request_id='restart'),restarted)

    def test_legacy_completed_topic_resumes_without_losing_earlier_attempts(self):
        sid = self.start()
        state = self.engine.get(sid)
        state.pop('solved_questions');state.pop('review_round')
        state.update(state='DONE',completed=True,index=1,attempts=[dict(concept='percentages',correct=True)])
        self.engine.save(state)
        result = self.engine.respond(sid,'Try a question',intent='practice')
        self.assertEqual(result['action'],'ASK')
        self.assertEqual(result['session']['current_concept']['id'],'fractions')
        self.assertEqual(len(self.engine.get(sid)['attempts']),1)
        self.engine.llm.ask.assert_not_called()

    def test_explain_teaches_from_sources_and_hints_progress_without_scoring(self):
        sid = self.engine.create('percentages','Hariom')['session_id']
        self.engine.evidence = lambda *args:[dict(text='A percentage compares a quantity out of 100.',book_title='NCERT',page_start=1,source_url='https://ncert.nic.in/')]
        self.engine.guidance = Engine.guidance.__get__(self.engine)
        self.engine.llm.ask.return_value = ('Use an equivalent fraction with denominator one hundred.','fine_tuned_qwen')
        result = self.engine.respond(sid,'eplain concept')
        self.assertEqual(result['action'],'EXPLAIN')
        self.assertIn('From NCERT:',result['reply'])
        self.assertIn('Now try this NCERT question:',result['reply'])
        self.assertEqual(result['misconception'],None)
        replies = []
        for expected in [1,2,3,3]:
            hint = self.engine.respond(sid,'I would like a hint.',intent='hint')
            self.assertEqual(hint['hint_level'],expected)
            replies.append(hint['reply'])
        self.assertEqual(len(set(replies[:3])),3)
        messages = self.engine.llm.ask.call_args.args[0]
        self.assertIn('Give hint level 3',messages[0]['content'])
        self.assertIn('Use an equivalent fraction',messages[-2]['content'])
        self.assertEqual(self.engine.get(sid)['attempts'],[])
        self.engine.eedi.diagnose.assert_not_called()

    def test_checkpoint_method_scaffolds_do_not_contain_final_results(self):
        for items in self.engine.questions.values():
            for question in items:
                self.assertEqual(len(question['hint_steps']),3)
                for step in question['hint_steps']:
                    self.assertFalse(leaks(step,question['key']),question['id'])
        percent = self.engine.questions['percentages'][0]['hint_steps']
        self.assertIn('a/b',percent[0])
        self.assertIn('Keep four as the denominator',percent[1])

    def test_hint_messages_route_preserves_retries_without_scoring(self):
        sid = self.start()
        self.engine.lock = threading.RLock()
        self.engine.guidance.reset_mock()
        body = dict(text='I would like a hint.',intent='hint',request_id='hint-retry')
        with patch('server.engine',self.engine):
            client = TestClient(app)
            response = client.post(f'/api/sessions/{sid}/messages',json=body)
            repeated = client.post(f'/api/sessions/{sid}/messages',json=body)
        self.assertEqual(response.status_code,200)
        self.assertEqual(repeated.json(),response.json())
        self.assertEqual(response.json()['hint_level'],1)
        self.assertEqual(self.engine.get(sid)['attempts'],[])
        self.engine.guidance.assert_called_once()

    def test_remote_answer_leak_is_repaired_without_exposing_the_first_reply(self):
        sid = self.start()
        self.engine.guidance = Engine.guidance.__get__(self.engine)
        self.engine.llm.ask.side_effect = [('The answer is 75%.','fine_tuned_qwen'),('Divide the first term by the second.','fine_tuned_qwen')]
        hint = self.engine.respond(sid,'hint',intent='hint')
        self.assertNotIn('75',hint['reply'])
        self.assertEqual(self.engine.llm.ask.call_count,2)
        self.assertEqual(self.engine.get(sid)['attempts'],[])

    def test_misconceptions_only_follow_wrong_answer_with_working(self):
        sid = self.start()
        self.engine.respond(sid,'0',intent='answer')
        self.engine.eedi.diagnose.assert_not_called()
        self.engine.respond(sid,'Explain the formula')
        self.engine.respond(sid,'hint')
        self.engine.eedi.diagnose.assert_not_called()
        result = self.engine.respond(sid,'I divided and forgot the conversion step')
        self.assertIsNone(result['misconception'].get('misconception_id'))
        self.engine.llm.ask.assert_not_called()
        self.assertFalse(result['misconception']['confirmed'])
        self.assertEqual(len(self.engine.get(sid)['attempts']),1)
        self.assertEqual(self.engine.eedi.diagnose.call_count,1)
        self.engine.respond(sid,'I think I understand')
        self.assertEqual(self.engine.eedi.diagnose.call_count,1)

    def test_model_outage_returns_url_request_without_changing_progress(self):
        sid = self.start()
        self.engine.lock = threading.RLock()
        self.engine.guidance.side_effect = ModelUnavailable('Please enter the latest Kaggle URL.')
        before = self.engine.get(sid)
        with patch('server.engine',self.engine):
            client = TestClient(app)
            response = client.post(f'/api/sessions/{sid}/messages',json=dict(text='0',intent='answer',request_id='retry-me'))
        self.assertEqual(response.status_code,503)
        self.assertTrue(response.json()['needs_model_url'])
        self.assertEqual(self.engine.get(sid),before)
        self.assertEqual(self.engine.db.execute('SELECT count(*) FROM replies').fetchone()[0],0)
        self.engine.guidance.side_effect = None
        self.engine.respond(sid,'0',intent='answer',request_id='retry-me')
        self.engine.respond(sid,'0',intent='answer',request_id='retry-me')
        self.assertEqual(len(self.engine.get(sid)['attempts']),1)

    def test_off_topic_answer_requests_and_initial_numeric_do_not_score(self):
        sid = self.engine.create('fractions','Hariom')['session_id']
        for text in ['football','How did the football match go?','Tell me a joke','give me the answer','Explain football','42']:
            self.assertEqual(self.engine.respond(sid,text)['action'],'REDIRECT')
        self.assertEqual(self.engine.get(sid)['attempts'],[])
        self.engine.eedi.diagnose.assert_not_called()

    def test_fraction_scoring_and_output_guard(self):
        self.assertEqual(numeric('2/6 kg'),numeric('1/3'))
        self.assertIsNone(numeric('1/0'))
        self.assertIsNone(numeric('__import__("os")'))
        for text in ['one third','2/6',r'\frac{1}{3}']:
            self.assertTrue(leaks(text,'1/3'))
        self.assertFalse(leaks('How many equal shares are there?','1/3'))

    def test_akt_predictions_match_training_notebook(self):
        import ast
        import math
        import torch
        from kt import KnowledgeTracer
        root = Path(__file__).resolve().parent
        tracer = KnowledgeTracer(root/'models/akt')
        checkpoint = torch.load(root/'models/akt/akt_best.pt',map_location='cpu',weights_only=True)
        notebook = json.loads((root.parent/'notes/hariom kumar/milestone-3/KT_model/KT_Models_Comparison_AKT_firstnb_processing.ipynb').read_text(encoding='utf-8'))
        classes = []
        for cell in notebook['cells']:
            if cell['cell_type'] == 'code':
                source = ''.join(cell['source'])
                classes.extend(node for node in ast.parse(source).body if isinstance(node,ast.ClassDef)
                               and node.name in {'MonotonicAttention','AKTBlock','AKT'})
        self.assertEqual(len(classes),3)
        namespace = dict(torch=torch,nn=torch.nn,F=torch.nn.functional,math=math)
        exec(compile(ast.Module(body=classes,type_ignores=[]),'training_akt_classes','exec'),namespace)
        reference = namespace['AKT'](checkpoint['n_skills'],**checkpoint['kwargs']).eval()
        reference.load_state_dict(checkpoint['state_dict'],strict=True)
        self.assertEqual(tracer.n,123)
        self.assertEqual(tracer.mapping,{'fraction_multiplication':42,'fraction_division':38,'percentages':75})
        for name, weight in tracer.model.state_dict().items():
            torch.testing.assert_close(weight,checkpoint['state_dict'][name],rtol=0,atol=0)
        threads = torch.get_num_threads();torch.set_num_threads(2)
        self.addCleanup(torch.set_num_threads,threads)
        for count in (1,3,230):
            with self.subTest(history_length=count):
                topics = ['percentages','fraction_division','fraction_multiplication','conduction']
                attempts = [dict(concept=topics[i%4],correct=bool(i%3)) for i in range(count)]
                known = {'percentages':75,'fraction_division':38,'fraction_multiplication':42}
                history = [(known[a['concept']],int(a['correct'])) for a in attempts if a['concept'] in known][-199:]
                ex = torch.tensor([[s for s,_ in history]] * 3)
                ans = torch.tensor([[s + 123*c for s,c in history]] * 3)
                target = torch.tensor([[s for s,_ in history[1:]] + [index] for index in (42,38,75)])
                questions = torch.full_like(ex,15922)
                with torch.inference_mode():
                    expected = reference(ex,ans,target,ex_q=questions,tgt_q=questions)[:,-1].sigmoid()
                result = tracer.predict(attempts)
                torch.testing.assert_close(torch.tensor(list(result.values())),expected,rtol=1e-6,atol=1e-7)
                self.assertTrue(all(0 <= p <= 1 for p in result.values()))
        self.assertEqual(tracer.predict([]),{})
        self.assertEqual(tracer.predict([dict(concept='conduction',correct=True)]),{})

        ex = torch.tensor([[75,38,42]])
        ans = torch.tensor([[75,38,42]])
        target = torch.tensor([[38,42,75]])
        questions = torch.tensor([[0,1,2]])
        with torch.inference_mode():
            before = tracer.model(ex,ans,target,ex_q=questions,tgt_q=questions)
            expected = reference(ex,ans,target,ex_q=questions,tgt_q=questions)
            torch.testing.assert_close(before,expected)
            ans[:,1:] += 123
            after = tracer.model(ex,ans,target,ex_q=questions,tgt_q=questions)
        torch.testing.assert_close(before[:,0],after[:,0])

    def test_akt_rejects_changed_skill_names(self):
        import shutil
        from kt import KnowledgeTracer
        source = Path(__file__).resolve().parent/'models/akt'
        with tempfile.TemporaryDirectory() as folder:
            for name in ('metadata.json','akt_best.pt','skills.json'):
                shutil.copy2(source/name,Path(folder)/name)
            (Path(folder)/'skills.json').write_text('[]')
            with self.assertRaisesRegex(ValueError,'skill map checksum'):
                KnowledgeTracer(folder)

    def test_akt_status_and_progress_routes(self):
        from kt import KnowledgeTracer
        self.engine.kt = KnowledgeTracer(Path(__file__).resolve().parent/'models/akt')
        self.engine.lock = threading.RLock()
        self.engine.version = 'test';self.engine.chunks = [];self.engine.eedi.rows = []
        sid = self.start()
        self.engine.respond(sid,'0',intent='answer')
        with patch('server.engine',self.engine):
            client = TestClient(app)
            status = client.get('/api/status')
            progress = client.get(f'/api/sessions/{sid}/progress')
        self.assertEqual(status.status_code,200)
        self.assertTrue(status.json()['kt_loaded'])
        self.assertTrue(status.json()['kt'].startswith('AKT'))
        self.assertEqual(progress.status_code,200)
        self.assertTrue(progress.json()['kt_status'].startswith('AKT'))
        self.assertEqual({r['concept_id'] for r in progress.json()['concept_readiness']
                          if r['origin']=='akt_prediction'},set(self.engine.kt.mapping))
        self.assertEqual(progress.json()['total_attempts'],1)

    def test_intermediate_numbers_are_discussion_not_scored_answers(self):
        sid = self.start()
        result = self.engine.respond(sid,'100')
        self.assertEqual(self.engine.get(sid)['attempts'],[])
        self.assertIsNone(result['misconception'])
        self.engine.eedi.diagnose.assert_not_called()
        self.engine.respond(sid,'100',intent='answer')
        self.assertEqual(len(self.engine.get(sid)['attempts']),1)

    def test_remote_protocol_failure_has_no_local_fallback(self):
        model = ResponseModel()
        valid = dict(model='qwen35-socratic-final_lora_r16_lr0.0002',protocol_flags=[],
                     output_limit_reached=False,task='socratic_response_generation',text='A ratio compares quantities.')
        with patch('llm.endpoint_config',return_value=('https://example.test','test')), patch.object(model,'request',return_value=valid):
            self.assertEqual(model.ask([])[1],'fine_tuned_qwen')
            valid['output_limit_reached'] = True
            with self.assertRaises(ModelError):model.ask([])
            valid.pop('task')
            with self.assertRaises(ModelUnavailable):model.ask([])
        with patch('llm.http.open',side_effect=OSError('offline')) as open_request:
            with self.assertRaises(ModelUnavailable):model.request('https://example.test','test','/health')
            self.assertEqual(open_request.call_count,2)
        for url in ['http://localhost:8000','https://example.com','https://a.trycloudflare.com/path']:
            with self.assertRaises(ValueError):model.connect(url)

    def test_reconnect_checks_health_identity_and_preserves_config_on_failure(self):
        model = ResponseModel()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root/'phase/connection.json';config.parent.mkdir()
            (root/'.env').write_text('API_KEY=test-only-secret\n')
            config.write_text('{"base_url":"https://old.trycloudflare.com"}')
            with patch('llm.CONNECTION',config):
                self.assertEqual(endpoint_config()[0],'https://old.trycloudflare.com')
                with patch.object(model,'request',side_effect=ModelUnavailable('offline')):
                    with self.assertRaises(ModelUnavailable):model.connect('https://new.trycloudflare.com')
                self.assertIn('old.trycloudflare.com',config.read_text())
                self.assertEqual(endpoint_config.cache_info().currsize,1)
                with patch.object(model,'request',side_effect=[{'status':'ok'},dict(model='qwen35-socratic-final_lora_r16_lr0.0002',task='socratic_response_generation')]):
                    self.assertEqual(model.connect('https://new.trycloudflare.com/')['status'],'connected')
                self.assertEqual(json.loads(config.read_text())['base_url'],'https://new.trycloudflare.com')
                self.assertEqual(endpoint_config.cache_info().currsize,0)
                self.assertEqual(endpoint_config(),('https://new.trycloudflare.com','test-only-secret'))

    def test_endpoint_config_reads_files_once_until_cache_is_cleared(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder);config = root/'phase/connection.json';config.parent.mkdir()
            env = root/'.env';env.write_text('API_KEY=test-only-secret\n')
            config.write_text('{"base_url":"https://example.trycloudflare.com"}')
            with patch('llm.CONNECTION',config):
                expected = endpoint_config()
                config.unlink();env.unlink()
                self.assertEqual(endpoint_config(),expected)
                endpoint_config.cache_clear()
                with self.assertRaises(OSError):endpoint_config()

    def test_reused_http_opener_does_not_forward_authenticated_redirects(self):
        paths = []
        class Redirect(BaseHTTPRequestHandler):
            def do_GET(self):
                paths.append(self.path)
                self.send_response(307)
                self.send_header('Location','/redirected')
                self.end_headers()

            def log_message(self, *args):
                pass

        with ThreadingHTTPServer(('127.0.0.1',0),Redirect) as server:
            thread = threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                with self.assertRaises(ModelUnavailable):
                    ResponseModel().request(f'http://127.0.0.1:{server.server_port}','test-only-secret','/health')
                self.assertEqual(paths,['/health'])
            finally:
                server.shutdown();thread.join()


if __name__=='__main__':unittest.main()

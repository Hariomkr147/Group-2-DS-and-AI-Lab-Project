"""Exercise the notebook's actual HTTP/auth/request boundaries without a model."""
import json
import threading
import unittest
import urllib.error
import urllib.request

from kaggle_inference_api import start_server, validate_request


class ApiChecks(unittest.TestCase):
    def test_schema_rejects_ambiguous_and_unbounded_requests(self):
        for body in ([], {}, {"prompt": " "}, {"prompt": "x", "messages": []},
                     {"prompt": "x", "max_new_tokens": True}, {"prompt": "x", "max_new_tokens": 257},
                     {"messages": [{"role": "tool", "content": "x"}]},
                     {"messages": [{"role": "user", "content": "x" * 16001}]}):
            with self.subTest(body_type=type(body).__name__), self.assertRaises(ValueError):
                validate_request(body)
        self.assertEqual(validate_request({"prompt": "inference contract check"})["max_new_tokens"], 96)

    def test_auth_live_endpoint_and_error_paths(self):
        seen = []
        def infer(body):
            seen.append(body)
            if body["prompt"] == "oversize":
                raise ValueError("context")
            return {"text": "transport fixture", "diagnosis_confirmed": False}
        server = start_server(infer, {"task": "fixture"}, "a" * 32, port=0)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        base = f"http://127.0.0.1:{server.server_port}"
        def request(path, body=None, key="a" * 32):
            headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
            data = json.dumps(body).encode() if body is not None else None
            return opener.open(urllib.request.Request(base + path, data=data, headers=headers), timeout=3)
        try:
            with self.assertRaises(urllib.error.HTTPError) as caught:
                request("/health", key="wrong")
            self.assertEqual(caught.exception.code, 401)
            with request("/health") as response:
                self.assertEqual(json.load(response), {"status": "ok"})
            with request("/predict", {"prompt": "inference contract check"}) as response:
                self.assertFalse(json.load(response)["diagnosis_confirmed"])
            for body, status in [({}, 400), ({"prompt": "oversize"}, 422)]:
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    request("/predict", body)
                self.assertEqual(caught.exception.code, status)
            self.assertEqual(len(seen), 2)
        finally:
            server.shutdown(); server.server_close()

    def test_parallel_request_is_rejected_without_running_a_second_inference(self):
        entered, release = threading.Event(), threading.Event()
        def infer(body):
            entered.set()
            if not release.wait(timeout=5):
                raise RuntimeError("Test inference did not release")
            return {"text": "fixture"}
        server = start_server(infer, {}, "a" * 32, port=0)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        url = f"http://127.0.0.1:{server.server_port}/predict"
        def request():
            req = urllib.request.Request(url, data=b'{"prompt":"transport fixture"}',
                    headers={"Authorization": "Bearer " + "a" * 32, "Content-Type": "application/json"})
            with opener.open(req, timeout=5) as response:
                return json.load(response)
        results = []
        worker = threading.Thread(target=lambda: results.append(request()))
        try:
            worker.start()
            self.assertTrue(entered.wait(timeout=3))
            with self.assertRaises(urllib.error.HTTPError) as caught:
                request()
            self.assertEqual(caught.exception.code, 429)
        finally:
            release.set(); worker.join(timeout=5)
            server.shutdown(); server.server_close()
        self.assertEqual(results, [{"text": "fixture"}])


if __name__ == "__main__":
    unittest.main()

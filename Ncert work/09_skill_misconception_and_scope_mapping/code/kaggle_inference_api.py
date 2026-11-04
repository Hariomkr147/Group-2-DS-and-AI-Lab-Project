"""Small authenticated, non-streaming inference endpoint for a temporary notebook."""
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def validate_request(body):
    if not isinstance(body, dict) or set(body) - {"prompt", "messages", "max_new_tokens"}:
        raise ValueError("Use prompt OR messages, plus optional max_new_tokens")
    if ("prompt" in body) == ("messages" in body):
        raise ValueError("Provide exactly one of prompt or messages")
    maximum = body.get("max_new_tokens", 96)
    if type(maximum) is not int or not 1 <= maximum <= 256:
        raise ValueError("max_new_tokens must be an integer from 1 to 256")
    if "prompt" in body:
        if not isinstance(body["prompt"], str) or not body["prompt"].strip() or len(body["prompt"]) > 16000:
            raise ValueError("prompt must contain 1–16000 characters")
    else:
        messages = body["messages"]
        if not isinstance(messages, list) or not 1 <= len(messages) <= 32:
            raise ValueError("messages must contain 1–32 entries")
        for message in messages:
            if (not isinstance(message, dict) or set(message) != {"role", "content"}
                    or message["role"] not in ("system", "user", "assistant")
                    or not isinstance(message["content"], str) or not message["content"].strip()):
                raise ValueError("Invalid chat message")
        if sum(len(m["content"]) for m in messages) > 16000:
            raise ValueError("Chat exceeds 16000 characters")
    return {**body, "max_new_tokens": maximum}


def start_server(infer, metadata, api_key, port=8000):
    if not isinstance(api_key, str) or len(api_key) < 32 or not api_key.isascii() or not api_key.isprintable():
        raise ValueError("Use a random ASCII API key of at least 32 characters")
    busy = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Keep prompts and authentication out of notebook/access logs.

        def send_json(self, status, value):
            payload = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def authorized(self):
            supplied = self.headers.get("Authorization", "").encode("utf-8")
            if not secrets.compare_digest(supplied, ("Bearer " + api_key).encode("utf-8")):
                self.send_json(401, {"error": "Unauthorized"})
                return False
            return True

        def do_GET(self):
            if not self.authorized():
                return
            if self.path == "/health":
                self.send_json(200, {"status": "ok"})
            elif self.path == "/metadata":
                self.send_json(200, metadata)
            else:
                self.send_json(404, {"error": "Not found"})

        def do_POST(self):
            self.connection.settimeout(15)
            if not self.authorized():
                return
            if self.path != "/predict":
                self.send_json(404, {"error": "Not found"})
                return
            if self.headers.get_content_type() != "application/json" or self.headers.get("Transfer-Encoding"):
                self.send_json(415, {"error": "Send a JSON body with Content-Length"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 65536:
                    self.send_json(413, {"error": "JSON body must be 1–65536 bytes"})
                    return
                payload = self.rfile.read(length)
                if len(payload) != length:
                    raise ValueError("Incomplete JSON body")
                body = validate_request(json.loads(payload))
            except (ValueError, UnicodeError, OSError):
                self.send_json(400, {"error": "Invalid request schema or body"})
                return
            if not busy.acquire(blocking=False):
                self.send_json(429, {"error": "Model busy; retry later"})
                return
            try:
                result = infer(body)
                self.send_json(200, result)
            except ValueError:
                self.send_json(422, {"error": "Unsupported input format or model limit exceeded; nothing truncated"})
            except Exception as exc:
                print("Inference failed:", type(exc).__name__, flush=True)
                self.send_json(500, {"error": "Inference failed; check model configuration in notebook"})
            finally:
                busy.release()

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server

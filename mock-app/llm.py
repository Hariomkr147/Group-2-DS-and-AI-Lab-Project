"""Authenticated fine-tuned inference only; never start a local model."""
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache
from pathlib import Path

CONNECTION = Path(__file__).resolve().parent.parent / 'Ncert work/09_skill_misconception_and_scope_mapping/.remote_model_connection.json'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


http = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())


@lru_cache(maxsize=1)
def endpoint_config():
    config = json.loads(CONNECTION.read_text(encoding='utf-8'))
    url = config['base_url'].rstrip('/')
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != 'https' or not re.fullmatch(r'[a-z0-9-]+\.trycloudflare\.com', parsed.netloc)
            or parsed.path or parsed.query or parsed.fragment):
        raise ValueError('Expected the user-provided HTTPS temporary tunnel URL')
    env = (CONNECTION.parents[1] / '.env').read_text(encoding='utf-8-sig').splitlines()
    keys = [line.split('=', 1)[1].strip().strip('"').strip("'") for line in env if line.strip().startswith('API_KEY=')]
    if len(keys) != 1 or not keys[0]:
        raise ValueError('Expected one API_KEY in the ignored local .env')
    return url, keys[0]


class ModelError(Exception):
    needs_model_url = False


class ModelUnavailable(ModelError):
    needs_model_url = True


class ResponseModel:
    def request(self, url, key, route, body=None):
        request = urllib.request.Request(url + route, data=None if body is None else json.dumps(body).encode(),
                  headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
        for attempt in range(2):
            try:
                with http.open(request, timeout=60) as response:
                    return json.load(response)
            except urllib.error.HTTPError as error:
                if error.code == 429:
                    raise ModelError('Your model is busy. Wait a moment and retry; your answer has not been recorded.') from None
                if error.code == 422:
                    raise ModelError('The model rejected this input. Try shorter working or a shorter question; your answer has not been recorded.') from None
                if error.code in {502, 503, 504} and attempt == 0:
                    continue
                raise ModelUnavailable(f'Your fine-tuned model returned HTTP {error.code}. Keep Kaggle running and enter its latest Temporary URL below. Check that it uses the existing key.') from None
            except OSError:
                if attempt == 0:
                    continue
                raise ModelUnavailable('Cannot reach your fine-tuned model. Keep Kaggle running and enter its latest Temporary URL below.') from None
            except (ValueError, UnicodeError):
                raise ModelUnavailable('The endpoint did not return the expected model response. Enter the current fine-tuned model URL below.') from None

    def ask(self, messages, max_tokens=96):
        try:
            url, key = endpoint_config()
        except (OSError, ValueError, KeyError):
            raise ModelUnavailable('Set the current fine-tuned model URL and keep its key in the local .env file.') from None
        result = self.request(url, key, '/predict', {'messages': messages, 'max_new_tokens': max_tokens})
        if (not isinstance(result, dict) or result.get('model') != 'qwen35-socratic-final_lora_r16_lr0.0002'
                or result.get('task') != 'socratic_response_generation'):
            raise ModelUnavailable('This endpoint did not identify the expected fine-tuned model. Enter its current URL below.')
        if (result.get('protocol_flags') != [] or result.get('output_limit_reached') is not False
                or not isinstance(result.get('text'), str) or not result['text'].strip()):
            raise ModelError('The model returned an incomplete or invalid reply. Retry this action; your answer has not been recorded.')
        return result['text'].strip(), 'fine_tuned_qwen'

    def connect(self, url):
        url = url.strip().rstrip('/')
        if not re.fullmatch(r'https://[a-z0-9-]+\.trycloudflare\.com', url):
            raise ValueError('Use the HTTPS Temporary URL printed by your Kaggle tunnel cell.')
        try:
            _, key = endpoint_config()
        except (OSError, ValueError, KeyError):
            raise ModelUnavailable('Keep the endpoint key in the local .env file and set a valid model URL.') from None
        health = self.request(url, key, '/health')
        if not isinstance(health, dict) or health.get('status') != 'ok':
            raise ModelUnavailable('The model is not ready yet. Keep the Kaggle server and tunnel running.')
        metadata = self.request(url, key, '/metadata')
        if not isinstance(metadata, dict) or metadata.get('model') != 'qwen35-socratic-final_lora_r16_lr0.0002' or metadata.get('task') != 'socratic_response_generation':
            raise ModelUnavailable('That URL is not serving the expected fine-tuned model.')
        temporary = CONNECTION.with_suffix('.tmp')
        temporary.write_text(json.dumps({'base_url': url}, indent=2) + '\n', encoding='utf-8')
        temporary.replace(CONNECTION)
        endpoint_config.cache_clear()
        return {'status': 'connected', 'model': metadata['model']}

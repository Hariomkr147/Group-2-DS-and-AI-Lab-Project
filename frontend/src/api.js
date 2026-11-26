const TOKEN_KEY = 'tutor_token';
let token = readStored(TOKEN_KEY);

export function readStored(key) {
  try { return JSON.parse(sessionStorage.getItem(key)); } catch { return null; }
}

export function store(key, value) {
  try {
    if (value == null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, JSON.stringify(value));
  } catch { /* tab storage may be blocked */ }
}

export const auth = {
  get token() { return token; },
  set token(value) {
    token = value;
    store(TOKEN_KEY, value);
  },
  onExpired: () => {},
};

// Older builds saved the bearer token as a raw string.
if (!token) {
  try { token = sessionStorage.getItem(TOKEN_KEY); } catch { /* storage blocked */ }
}

export async function api(path, body, signal) {
  const sentToken = auth.token;
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (sentToken) headers.Authorization = `Bearer ${sentToken}`;
  const deadline = AbortSignal.timeout(90_000);
  let response;
  let data;
  try {
    response = await fetch(`/api${path}`, {
      method: body === undefined ? 'GET' : 'POST',
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: signal ? AbortSignal.any([signal, deadline]) : deadline,
    });
    data = await response.json().catch((error) => {
      if (error instanceof SyntaxError) return null;
      throw error;
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new Error(deadline.aborted ? 'The server took too long to respond.' : 'Could not reach the server.');
  }
  if (response.status === 401 && path !== '/auth/login' && sentToken === auth.token) auth.onExpired();
  if (response.ok && data !== null) return data;
  const detail = data?.detail;
  const message = typeof detail === 'string' ? detail : detail?.[0]?.msg;
  throw Object.assign(new Error(message || (response.ok ? 'The server returned an invalid response.' : `Request failed (${response.status}).`)), { status: response.status });
}

// POST that reads server-sent events: `step` events go to onStep as each backend layer works, and the
// `reply` event's data is returned. A plain JSON response (an older backend, or an error sent before
// the stream starts) is handled like api(). Errors carry `status` so callers can offer retry or edit.
export async function apiStream(path, body, onStep, signal) {
  const sentToken = auth.token;
  const headers = { 'Content-Type': 'application/json', Accept: 'text/event-stream' };
  if (sentToken) headers.Authorization = `Bearer ${sentToken}`;
  const deadline = AbortSignal.timeout(120_000);
  const failed = (message, status) => Object.assign(new Error(message), { status });
  let response;
  try {
    response = await fetch(`/api${path}`, {
      method: 'POST', headers, body: JSON.stringify(body),
      signal: signal ? AbortSignal.any([signal, deadline]) : deadline,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new Error(deadline.aborted ? 'The server took too long to respond.' : 'Could not reach the server.');
  }
  if (response.status === 401 && sentToken === auth.token) auth.onExpired();
  if (!(response.headers.get('content-type') || '').startsWith('text/event-stream')) {
    const data = await response.json().catch(() => null);
    if (response.ok && data !== null) return data;
    const detail = data?.detail;
    const message = typeof detail === 'string' ? detail : detail?.[0]?.msg;
    throw failed(message || `Request failed (${response.status}).`, response.status);
  }
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = '';
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += value.replaceAll('\r\n', '\n');
      let end;
      while ((end = buffer.indexOf('\n\n')) >= 0) {
        const block = buffer.slice(0, end);
        buffer = buffer.slice(end + 2);
        let event = 'message';
        const data = [];
        for (const line of block.split('\n')) {
          if (line.startsWith('event:')) event = line.slice(6).trim();
          else if (line.startsWith('data:')) data.push(line.slice(5).replace(/^ /, ''));
        }
        if (!data.length) continue;
        const payload = JSON.parse(data.join('\n'));
        if (event === 'step') onStep?.(payload);
        else if (event === 'reply') return payload;
        else if (event === 'error') {
          const detail = payload.detail;
          throw failed(typeof detail === 'string' ? detail : 'The tutor could not finish this turn.', payload.status);
        }
      }
    }
  } catch (error) {
    if (error.status !== undefined || signal?.aborted) throw error;
    throw new Error(deadline.aborted ? 'The server took too long to respond.' : 'The connection dropped before the reply arrived.');
  } finally {
    reader.cancel().catch(() => {});
  }
  throw new Error('The connection dropped before the reply arrived.');
}

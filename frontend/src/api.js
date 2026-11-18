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

// All calls go to /api, which the dev server (or your web server) forwards to the backend.
const TOKEN_KEY = 'tutor_token';

export const auth = {
  get token() {
    try { return sessionStorage.getItem(TOKEN_KEY); } catch { return null; }
  },
  set token(value) {
    try {
      if (value) sessionStorage.setItem(TOKEN_KEY, value);
      else sessionStorage.removeItem(TOKEN_KEY);
    } catch { /* storage blocked: the user just signs in again after a reload */ }
  },
  onExpired: () => {},
};

function messageOf(data, status) {
  const detail = data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  return `Request failed (${status})`;
}

export async function api(path, body) {
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (auth.token) headers.Authorization = `Bearer ${auth.token}`;

  let response;
  try {
    response = await fetch(`/api${path}`, { method: body === undefined ? 'GET' : 'POST', headers, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch {
    throw new Error('Cannot reach the server. Check that the backend is running.');
  }
  const data = await response.json().catch(() => null);
  if (response.status === 401 && path !== '/auth/login') auth.onExpired();
  if (!response.ok) throw new Error(messageOf(data, response.status));
  return data;
}

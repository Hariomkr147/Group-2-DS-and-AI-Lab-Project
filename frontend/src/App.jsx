import { useEffect, useState } from 'react';
import { api, auth, readStored, store } from './api.js';
import { Icon, IconSprite } from './components/Icon.jsx';
import Login from './components/Login.jsx';
import Workspace from './components/Workspace.jsx';

export default function App() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(Boolean(auth.token));
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [theme, setTheme] = useState(() => readStored('theme') ?? 'system');

  useEffect(() => {
    auth.onExpired = signOut;
    if (!auth.token) return;
    const controller = new AbortController();
    api('/auth/me', undefined, controller.signal)
      .then((me) => { setError(''); setUser(me.username); })
      .catch((error) => {
        if (!controller.signal.aborted && error.status !== 401) setError(error.message);
      })
      .finally(() => { if (!controller.signal.aborted) setChecking(false); });
    return () => controller.abort();
  }, [attempt]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    store('theme', theme);
  }, [theme]);

  function signOut() {
    auth.token = null;
    setUser(null);
    setChecking(false);
    setError('');
  }

  async function login(username, password) {
    const result = await api('/auth/login', { username, password });
    auth.token = result.access_token;
    setUser(result.username);
  }

  return (
    <>
      <IconSprite />
      <a className="skip-link" href="#main">Skip to content</a>
      <header className="site-header">
        <div className="brand"><span className="book-mark"><Icon name="book" /></span><span>NCERT Socratic Tutor</span></div>
        <div className="account">
          <select aria-label="Color theme" value={theme} onChange={(event) => setTheme(event.target.value)}>
            <option value="system">System theme</option><option value="light">Light theme</option><option value="dark">Dark theme</option>
          </select>
          {user && <><span className="username">{user}</span><button onClick={signOut}>Sign out</button></>}
        </div>
      </header>
      {(checking || error) ? (
        <main id="main" className="status-page" tabIndex={-1}>
          {checking ? <p role="status">Checking your sign-in…</p> : <>
            <h1>Couldn’t check your sign-in</h1><p role="alert">{error}</p>
            <div className="actions"><button className="primary" onClick={() => { setChecking(true); setAttempt(attempt + 1); }}>Try again</button><button onClick={signOut}>Use a different sign-in</button></div>
          </>}
        </main>
      ) : user ? <Workspace key={user} user={user} /> : <Login onLogin={login} />}
    </>
  );
}

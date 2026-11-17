import { useState } from 'react';

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await onLogin(username, password);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="panel login-card" onSubmit={submit}>
        <div className="panel-header"><h2>Sign in to the NCERT Socratic Tutor</h2></div>
        <div className="panel-content login-fields">
          <label htmlFor="username">Username</label>
          <input id="username" className="chat-input" autoComplete="username" value={username}
            onChange={(e) => setUsername(e.target.value)} required />
          <label htmlFor="password">Password</label>
          <input id="password" className="chat-input" type="password" autoComplete="current-password" value={password}
            onChange={(e) => setPassword(e.target.value)} required autoFocus />
          {error && <div className="state-banner visible" role="alert">{error}</div>}
          <button className="btn btn-primary" type="submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
          <p className="help">Access is limited to the project team. Ask the team for the password.</p>
        </div>
      </form>
    </div>
  );
}

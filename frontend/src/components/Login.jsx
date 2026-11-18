import { useState } from 'react';

export default function Login({ onLogin }) {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    if (busy) return;
    const fields = new FormData(event.currentTarget);
    setBusy(true);
    setError('');
    try {
      await onLogin(fields.get('username'), fields.get('password'));
    } catch (error) {
      setError(error.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main id="main" className="login-page" tabIndex={-1}>
      <section className="login-intro">
        <p className="label">IIT Madras BS · Group 2</p>
        <h1>Work through<br />the question.</h1>
        <p>Explore NCERT maths and science with guided questions, worked steps, and textbook references.</p>
      </section>
      <form className="login-form" onSubmit={submit}>
        <h2>Sign in</h2>
        <label htmlFor="username">Username</label>
        <input id="username" name="username" autoComplete="username" maxLength={64} required />
        <label htmlFor="password">Password</label>
        <input id="password" name="password" type="password" autoComplete="current-password" maxLength={128} required />
        {error && <p className="error" role="alert">{error}</p>}
        <button className="primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
        <p className="muted">Use the credentials provided by the project team.</p>
      </form>
    </main>
  );
}

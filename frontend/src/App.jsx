import { useCallback, useEffect, useState } from 'react';
import { api, auth } from './api.js';
import { IconSprite } from './components/Icon.jsx';
import Header from './components/Header.jsx';
import Login from './components/Login.jsx';
import ConceptMap from './components/ConceptMap.jsx';
import Chat, { ACTION_LABEL } from './components/Chat.jsx';
import SidePanel from './components/SidePanel.jsx';

export default function App() {
  const [user, setUser] = useState(null); // set after /auth/me confirms the saved token
  const [checking, setChecking] = useState(!!auth.token);

  const signOut = useCallback(() => { auth.token = null; setUser(null); }, []);

  useEffect(() => {
    auth.onExpired = signOut;
    if (!auth.token) return;
    api('/auth/me').then((me) => setUser(me.username)).catch(() => { auth.token = null; }).finally(() => setChecking(false));
  }, [signOut]);

  async function login(username, password) {
    const out = await api('/auth/login', { username, password });
    auth.token = out.access_token;
    setUser(out.username);
  }

  if (checking) return null;
  return (
    <>
      <IconSprite />
      <Header user={user} onSignOut={signOut} />
      {user ? <Tutor user={user} /> : <Login onLogin={login} />}
    </>
  );
}

function Tutor({ user }) {
  const [course, setCourse] = useState(null);
  const [concepts, setConcepts] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [currentId, setCurrentId] = useState(null);
  const [banner, setBanner] = useState('');
  const [resource, setResource] = useState(null);
  const [progress, setProgress] = useState(null);
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState('');

  const say = (role, text, meta = '') => setMessages((m) => [...m, { role, text, meta }]);
  const clearDraft = useCallback(() => setDraft(''), []);

  // Load the first course and open a session.
  useEffect(() => {
    (async () => {
      try {
        const courses = await api('/courses');
        if (!courses.length) return say('tutor', 'No course is loaded yet.', 'Setup');
        const c = courses[0];
        setCourse(c);
        setConcepts(await api(`/courses/${c.id}/concepts`));
        const s = await api('/sessions', { course_id: c.id });
        setSessionId(s.session_id);
      } catch (e) {
        say('tutor', e.message, 'Startup error');
      }
    })();
  }, []);

  const loadProgress = useCallback(async (courseId) => {
    setProgress(await api(`/learners/${encodeURIComponent(user)}/progress?course_id=${encodeURIComponent(courseId)}`));
  }, [user]);

  async function send(text) {
    if (!sessionId || busy) return;
    say('learner', text);
    setBusy(true);
    try {
      const r = await api(`/sessions/${sessionId}/messages`, { text });
      say('tutor', r.reply, ACTION_LABEL[r.action] ?? r.action);
      if (r.concept_id) setCurrentId(r.concept_id);
      if (r.resource) setResource(r.resource);
      const name = concepts.find((c) => c.id === r.concept_id)?.name;
      setBanner(r.action === 'backtrack' && name ? `Going back to ${name} first, then returning to your question.` : '');
      if (r.misconception) say('tutor', `Possible sticking point: ${r.misconception.replaceAll('_', ' ')}. This is a suggestion, not confirmed.`, 'Learning support');
      await loadProgress(course.id);
    } catch (e) {
      say('tutor', e.message, 'Action not completed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="main-layout">
      <ConceptMap concepts={concepts} currentId={currentId} disabled={busy || !sessionId}
        onPick={(c) => setDraft(`I am stuck on ${c.name.toLowerCase()}`)} />
      <Chat messages={messages} busy={busy} ready={!!sessionId} banner={banner} onSend={send} draft={draft} onDraftUsed={clearDraft} />
      <SidePanel progress={progress} resource={resource} />
    </div>
  );
}

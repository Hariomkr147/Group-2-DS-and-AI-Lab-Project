import { useEffect, useState } from 'react';
import { api, apiStream, readStored, store } from '../api.js';
import Chat from './Chat.jsx';
import ConceptMap from './ConceptMap.jsx';
import SidePanel from './SidePanel.jsx';
import Assessment from './Assessment.jsx';
import PreviousChats from './PreviousChats.jsx';

const NCERT = 'ncert';

function chapterLabel(chapter) {
  return chapter.title ? `Chapter ${chapter.chapter} · ${chapter.title}` : `Chapter ${chapter.chapter}`;
}

export default function Workspace({ user }) {
  const locationKey = `lesson:${user}`;
  const [selection, setSelection] = useState(() => readStored(locationKey));
  const [courses, setCourses] = useState(null);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    api('/courses', undefined, controller.signal).then((items) => {
      setCourses(items);
      setSelection((saved) => items.some((course) => course.id === saved?.course_id) ? saved : {
        course_id: (items.find((course) => course.concept_count > 0) ?? items[0])?.id,
      });
    }).catch((error) => { if (!controller.signal.aborted) setError(error.message); });
    return () => controller.abort();
  }, [retry]);

  function open(next) {
    store(locationKey, next);
    setSelection(next);
  }

  const course = courses?.find((item) => item.id === selection?.course_id);
  return (
    <main id="main" className="workspace" tabIndex={-1}>
      {!courses ? <section className="status-page">
        <h1>Your study workspace</h1>
        {error ? <><p className="error" role="alert">{error}</p><button onClick={() => { setError(''); setRetry(retry + 1); }}>Retry loading courses</button></> : <p role="status">Loading courses…</p>}
      </section> : !course ? <section className="status-page"><h1>No courses available</h1><p>Ask the project team to add a course.</p></section> : <>
        <div className="course-heading">
          <div><p className="label">{course.id === NCERT ? 'Textbook study' : course.subject}</p><h1>{course.title}</h1></div>
          <label className="course-control">Course<select value={course.id} onChange={(event) => open({ course_id: event.target.value })}>
            {courses.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
          </select></label>
        </div>
        {course.id === NCERT && <Scope key={JSON.stringify([selection.grade, selection.subject, selection.chapter?.book_code, selection.chapter?.chapter])} selection={selection} onOpen={open} />}
        <Lesson key={JSON.stringify(selection)} user={user} course={course} selection={selection} onOpen={open} />
      </>}
    </main>
  );
}

function Scope({ selection, onOpen }) {
  const [grade, setGrade] = useState(selection.grade ?? 10);
  const [subject, setSubject] = useState(selection.subject ?? 'maths');
  const [chapters, setChapters] = useState(null);
  const [chapterIndex, setChapterIndex] = useState('');
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    api(`/courses/ncert/chapters?grade=${grade}&subject=${subject}`, undefined, controller.signal).then((rows) => {
      setChapters(rows);
      const selected = rows.findIndex((row) => row.book_code === selection.chapter?.book_code &&
        row.chapter === selection.chapter?.chapter && row.grade === selection.grade && row.subject === selection.subject);
      setChapterIndex(selected < 0 ? '' : String(selected));
    }).catch((error) => { if (!controller.signal.aborted) setError(error.message); });
    return () => controller.abort();
  }, [grade, subject, retry]);

  function resetCatalogue() {
    setChapters(null);
    setChapterIndex('');
    setError('');
  }

  function submit(event) {
    event.preventDefault();
    const chapter = chapterIndex === '' ? undefined : chapters[Number(chapterIndex)];
    onOpen({ course_id: NCERT, grade, subject, ...(chapter && { chapter }) });
  }

  return (
    <form className="scope" onSubmit={submit}>
      <label>Class<select value={grade} onChange={(event) => { resetCatalogue(); setGrade(Number(event.target.value)); }}>
        {[6, 7, 8, 9, 10].map((value) => <option key={value}>{value}</option>)}
      </select></label>
      <label>Subject<select value={subject} onChange={(event) => { resetCatalogue(); setSubject(event.target.value); }}>
        <option value="maths">Maths</option><option value="science">Science</option>
      </select></label>
      <label className="chapter-control">Chapter<select value={chapterIndex} disabled={!chapters?.length} onChange={(event) => setChapterIndex(event.target.value)}>
        <option value="">All chapters</option>
        {chapters?.map((row, index) => <option key={`${row.book_code}/${row.chapter}`} value={index}>
          {chapterLabel(row)}
        </option>)}
      </select></label>
      <button className="primary">Open lesson</button>
      {!chapters && !error && <small role="status">Loading chapters…</small>}
      {chapters?.length === 0 && <small>No approved chapters were found for this class and subject.</small>}
      {error && <div className="inline-error" role="alert">Chapter list unavailable. <button type="button" onClick={() => { resetCatalogue(); setRetry(retry + 1); }}>Retry chapters</button></div>}
    </form>
  );
}

function sessionKey(user, selection) {
  return JSON.stringify(['session', user, selection.course_id, selection.grade, selection.subject, selection.chapter?.book_code, selection.chapter?.chapter]);
}

function Lesson({ user, course, selection, onOpen }) {
  const isTextbook = course.id === NCERT;
  const scopeName = selection.grade ? `Class ${selection.grade} ${selection.subject === 'maths' ? 'Maths' : 'Science'}${selection.chapter ? ` · ${chapterLabel(selection.chapter)}` : ''}` : 'Classes 6–10 · Maths and Science';
  const key = sessionKey(user, selection);
  const pendingKey = `${key}:pending`;
  const [session, setSession] = useState(null);
  const [concepts, setConcepts] = useState([]);
  const [startupError, setStartupError] = useState('');
  const [startupRetry, setStartupRetry] = useState(0);
  const [progress, setProgress] = useState(null);
  const [progressError, setProgressError] = useState('');
  const [refresh, setRefresh] = useState(0);
  const [pending, setPending] = useState(() => readStored(pendingKey));
  const [messageError, setMessageError] = useState('');
  const [canEdit, setCanEdit] = useState(false);
  const [sending, setSending] = useState(false);
  const [steps, setSteps] = useState([]);       // what each backend layer reported for the turn in progress
  const [mode, setMode] = useState('chat');

  function savePending(value) {
    store(pendingKey, value);
    setPending(value);
  }

  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;
    async function start() {
      const rows = isTextbook ? [] : await api(`/courses/${encodeURIComponent(course.id)}/concepts`, undefined, signal);
      const saved = readStored(key);
      let opened;
      if (selection.session_id || saved) {
        try {
          const existing = await api(`/sessions/${selection.session_id || saved}`, undefined, signal);
          if (existing.course_id === course.id && existing.learner_id === user) opened = existing;
        } catch (error) {
          if (error.status !== 404 || selection.session_id) throw error;
        }
      }
      opened ??= await api('/sessions', selection, signal);
      if (signal.aborted) return;
      const unsent = readStored(pendingKey);
      if (unsent && (saved !== opened.session_id || opened.history.some((turn) => turn.request_id === unsent.request_id))) savePending(null);
      store(key, opened.session_id);
      setConcepts(rows);
      setSession(opened);
    }
    start().catch((error) => { if (!signal.aborted) setStartupError(error.message); });
    return () => controller.abort();
  }, [startupRetry]);

  useEffect(() => {
    if (isTextbook && !(selection.grade && selection.subject)) return;
    const controller = new AbortController();
    setProgressError('');
    const path = isTextbook
      ? `/learners/${encodeURIComponent(user)}/skill?grade=${selection.grade}&subject=${selection.subject}`
      : `/learners/${encodeURIComponent(user)}/progress?course_id=${encodeURIComponent(course.id)}`;
    api(path, undefined, controller.signal)
      .then(setProgress).catch((error) => { if (!controller.signal.aborted) setProgressError(error.message); });
    return () => controller.abort();
  }, [refresh]);

  const refreshProgress = () => setRefresh((value) => value + 1);

  async function send(message) {
    if (sending || !session) return;
    savePending(message);
    setMessageError('');
    setCanEdit(false);
    setSending(true);
    setSteps([]);
    const seen = [];
    try {
      const reply = await apiStream(`/sessions/${session.session_id}/messages`, message, (step) => {
        seen.push(step);
        setSteps([...seen]);
      });
      setSession((current) => ({
        ...current, current_concept: reply.concept_id ?? current.current_concept,
        history: [...current.history, { role: 'learner', text: message.text },
          { role: 'tutor', text: reply.reply, detail: reply, request_id: message.request_id, steps: seen }],
      }));
      savePending(null);
      refreshProgress();
      if (isTextbook) setTimeout(refreshProgress, 5000);   // answers are judged in the background after the reply
    } catch (error) {
      setMessageError(error.message);
      setCanEdit([400, 404, 409, 422].includes(error.status));
    } finally {
      setSending(false);
    }
  }

  function startTurn(text, options = {}) {
    if (!pending && !sending && session) send({ text, request_id: crypto.randomUUID(), ...options });
  }

  async function resume(item, signal) {
    const { scope } = item;
    const next = { course_id: item.course_id, grade: scope.grade, subject: scope.subject, session_id: item.session_id };
    if (scope.chapter != null) {
      const chapters = await api(`/courses/ncert/chapters?grade=${scope.grade}&subject=${scope.subject}`, undefined, signal);
      next.chapter = chapters.find((chapter) => chapter.chapter === scope.chapter && chapter.book_code === scope.book_code) ?? scope;
    }
    const target = sessionKey(user, next);
    if (readStored(target + ':pending') && readStored(target) !== item.session_id) {
      throw new Error('Finish retrying the pending message in that lesson before switching chats.');
    }
    if (!signal.aborted) onOpen(next);
  }

  return (
    <div className="lesson-grid">
      <ConceptMap concepts={concepts} currentId={session?.current_concept} topics={selection.chapter?.topics}
        isTextbook={isTextbook} scopeName={scopeName} disabled={!session || Boolean(pending) || mode !== 'chat'}
        onPick={(concept) => startTurn(`Help me with ${concept.name}.`, { concept_id: concept.id, new_topic: true })}
        onTopic={(topic) => startTurn(`Help me understand ${topic}.`.slice(0, 2000), { new_topic: true, topic_heading: topic })} />
      <section className="study">
        <nav className="view-switch" aria-label="Study mode">
          <button type="button" aria-pressed={mode === 'chat'} onClick={() => setMode('chat')}>Tutor</button>
          {isTextbook && <span className="mode-note muted">Answers you send update your skill level</span>}
          {!isTextbook && <><button type="button" aria-pressed={mode === 'practice'} disabled={!session} onClick={() => setMode('practice')}>Practice</button>
            <button type="button" aria-pressed={mode === 'diagnostic'} disabled={!session} onClick={() => setMode('diagnostic')}>Diagnostic</button></>}
          <PreviousChats current={session?.session_id} onCurrent={() => setMode('chat')} onResume={resume}
            onNew={async (signal) => {
              const created = await api('/sessions', selection, signal);
              if (!signal.aborted) onOpen({ ...selection, session_id: created.session_id });
            }} disabled={Boolean(pending) || sending} />
        </nav>
        <div hidden={mode !== 'chat'} className="chat-view">
          <Chat session={session} pending={pending} sending={sending} steps={steps} startupError={startupError} messageError={messageError}
            isTextbook={isTextbook} onSend={startTurn}
            onRetryStart={() => { setStartupError(''); setStartupRetry(startupRetry + 1); }}
            onRetry={() => send(pending)} onEdit={canEdit ? () => { savePending(null); setMessageError(''); } : null} />
        </div>
        {mode !== 'chat' && session && <Assessment key={mode} sessionId={session.session_id} mode={mode}
          concepts={concepts} currentId={session.current_concept} onGraded={refreshProgress} />}
      </section>
      <SidePanel selection={selection} isTextbook={isTextbook} progress={progress} progressError={progressError} onRetry={refreshProgress} />
    </div>
  );
}

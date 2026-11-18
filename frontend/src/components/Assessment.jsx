import { useState } from 'react';
import { api, readStored, store } from '../api.js';
import { RichText } from './RichText.jsx';

export default function Assessment({ sessionId, mode, concepts, currentId, onGraded }) {
  const key = `assessment:${sessionId}:${mode}`;
  const [run, setRun] = useState(() => readStored(key));
  const [concept, setConcept] = useState(currentId ?? concepts[0]?.id ?? '');
  const [difficulty, setDifficulty] = useState('');
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const question = run?.questions[run.index];
  const correct = question && run.results[question.id];
  const finished = Boolean(run?.questions.length && !question);
  const label = mode === 'practice' ? 'Practice' : 'Diagnostic';

  function save(next) {
    setRun(next);
    store(key, next);
  }

  async function start(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const questions = await api('/assessments', { session_id: sessionId, kind: mode, concept_id: concept || null,
        difficulty: difficulty === '' ? null : Number(difficulty) });
      if (questions.length) save({ questions, index: 0, results: {} });
      else setError('There are no questions for that selection. Choose another concept or difficulty.');
    } catch (error) {
      setError(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function grade(event) {
    event.preventDefault();
    if (!text.trim() || busy || correct !== undefined) return;
    setBusy(true);
    setError('');
    try {
      const result = await api(`/assessments/${question.id}/answer`, { text: text.trim() });
      save({ ...run, results: { ...run.results, [question.id]: result.correct } });
      onGraded();
    } catch (error) {
      setError(error.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="assessment">
      <h2>{label}</h2>
      {error && <p className="error" role="alert">{error}</p>}
      {!run ? <form className="assessment-form" onSubmit={start}>
        <p>{mode === 'practice' ? 'Work through a short set of questions on one concept.' : 'Try one question per concept, starting with the foundations.'}</p>
        {mode === 'practice' && <>
          <label>Concept<select value={concept} onChange={(event) => setConcept(event.target.value)} required>
            {concepts.map((concept) => <option key={concept.id} value={concept.id}>{concept.name}</option>)}
          </select></label>
          <label>Difficulty<input type="number" step="1" value={difficulty} placeholder="Any difficulty" onChange={(event) => setDifficulty(event.target.value)} /></label>
        </>}
        <button className="primary" disabled={busy || (mode === 'practice' && !concept)}>{busy ? 'Loading questions…' : `Start ${label.toLowerCase()}`}</button>
      </form> : finished ? <div className="assessment-form">
        <p className="score">{Object.values(run.results).filter(Boolean).length} / {run.questions.length} correct</p>
        <button onClick={() => save(null)}>Start another set</button>
      </div> : <div className="assessment-form">
        <p className="label">Question {run.index + 1} of {run.questions.length}</p>
        <p className="question"><RichText text={question.text} /></p>
        {question.hint && <details><summary>Show hint</summary><p><RichText text={question.hint} /></p></details>}
        {correct !== undefined ? <>
          <p className={correct ? 'feedback' : 'error'} role="status">{correct ? 'Correct.' : 'That answer needs another look. Revisit the concept with the tutor.'}</p>
          <button className="primary" onClick={() => { setText(''); save({ ...run, index: run.index + 1 }); }}>
            {run.index + 1 === run.questions.length ? 'See results' : 'Next question'}
          </button>
        </> : <form className="assessment-form" onSubmit={grade}>
          <label>Your answer<input value={text} onChange={(event) => setText(event.target.value)} required maxLength={2000} /></label>
          <button className="primary" disabled={busy || !text.trim()}>{busy ? 'Checking answer…' : 'Check answer'}</button>
        </form>}
      </div>}
    </section>
  );
}

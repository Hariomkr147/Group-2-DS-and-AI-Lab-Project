import { useEffect, useRef, useState } from 'react';
import { api } from '../api.js';
import { RichText, SourceLink, sourceTitle } from './RichText.jsx';

export default function SidePanel({ selection, isTextbook, progress, progressError, onRetry, studyGraph, studyError,
  learnerState, learnerStateError, sessionId, onOpenConcept, onOpenTopic, onResume, pickDisabled }) {
  const [toolsOpened, setToolsOpened] = useState(false);
  return (
    <aside className="reference" aria-label="Study references">
      {!isTextbook && <details open>
        <summary>Your progress</summary>
        <Progress progress={progress} error={progressError} onRetry={onRetry} />
      </details>}
      {isTextbook && selection.grade && selection.subject && <details open>
        <summary>Your skill level</summary>
        <Skill skill={progress} error={progressError} onRetry={onRetry} />
      </details>}
      {isTextbook && <details open>
        <summary>Where you left off</summary>
        <LeftOff state={learnerState} error={learnerStateError} sessionId={sessionId} onRetry={onRetry}
          onOpenTopic={onOpenTopic} onResume={onResume} disabled={pickDisabled} />
      </details>}
      {isTextbook && selection.grade && selection.subject && <details open>
        <summary>What to study</summary>
        <Study graph={studyGraph} error={studyError} onRetry={onRetry} onOpen={onOpenConcept} disabled={pickDisabled} />
      </details>}
      <details>
        <summary>Search course sources</summary>
        <Search selection={selection} />
      </details>
      <details onToggle={(event) => { if (event.currentTarget.open) setToolsOpened(true); }}>
        <summary>Maths tools</summary>
        {toolsOpened && <MathTools />}
      </details>
    </aside>
  );
}

function Progress({ progress, error, onRetry }) {
  if (error) return <div className="reference-content"><p className="error" role="alert">Progress is temporarily unavailable.</p><button onClick={onRetry}>Retry progress</button></div>;
  if (!progress) return <p className="reference-content muted" role="status">Loading progress…</p>;
  const tried = progress.concepts.filter((concept) => concept.attempts);
  const total = tried.reduce((sum, concept) => sum + concept.attempts, 0);
  const correct = tried.reduce((sum, concept) => sum + concept.correct, 0);
  return <div className="reference-content">
    {total ? <>
      <p><strong className="score">{correct}/{total}</strong> correct</p>
      <progress max={total} value={correct} aria-label="Correct answers" />
      <ul className="readiness">{tried.map((concept) => <li key={concept.concept_id}><span>{concept.name}</span><span>{Math.round(concept.readiness * 100)}%</span></li>)}</ul>
      <p className="muted">Readiness estimates for concepts you’ve tried. The project account shares these totals.</p>
    </> : <p className="muted">Answer a graded question to start tracking your progress.</p>}
  </div>;
}

const SOURCE = { akt: 'AKT knowledge tracing', accuracy: 'share of answers right', mixed: 'AKT and share of answers right' };

function Skill({ skill, error, onRetry }) {
  if (error) return <div className="reference-content"><p className="error" role="alert">Skill level is temporarily unavailable.</p><button onClick={onRetry}>Retry skill level</button></div>;
  if (!skill || skill.answers === undefined) return <p className="reference-content muted" role="status">Loading skill level…</p>;
  const name = `Class ${skill.grade} ${skill.subject === 'maths' ? 'Maths' : 'Science'}`;
  if (!skill.level) return <div className="reference-content"><p><strong>{name}</strong></p>
    <p className="muted">Try an exercise and send your answer. Your level appears once the tutor checks one.</p></div>;
  return <div className="reference-content skill">
    <p>{name}</p>
    <p><strong className="score">{skill.level}</strong><span className="muted"> / 10</span></p>
    <div className="skill-bar" role="img" aria-label={`Skill level ${skill.level} out of 10`}>
      {Array.from({ length: 10 }, (_, index) => <span key={index} data-filled={index < skill.level} />)}
    </div>
    <p className="muted">From {skill.answers} checked {skill.answers === 1 ? 'answer' : 'answers'} ({skill.correct} right), using {SOURCE[skill.source]}.</p>
  </div>;
}

function where(concept) {
  return [concept.grade && `Class ${concept.grade}`, concept.chapter && `Ch ${concept.chapter}`].filter(Boolean).join(' · ');
}

function Study({ graph, error, onRetry, onOpen, disabled }) {
  if (error) return <div className="reference-content"><p className="muted" role="status">Study suggestions are unavailable right now.</p><button onClick={onRetry}>Retry suggestions</button></div>;
  if (!graph) return <p className="reference-content muted" role="status">Loading suggestions…</p>;
  const byId = Object.fromEntries(graph.nodes.map((concept) => [concept.id, concept]));
  const next = graph.next.map((id) => byId[id]).filter(Boolean);
  const review = graph.review.map((id) => byId[id]).filter(Boolean);
  const { mastered = 0, learning = 0, struggling = 0 } = graph.counts;
  return <div className="reference-content study-lists">
    <h3>Ready to learn next</h3>
    {next.length
      ? <ul className="readiness">{next.map((concept) => <li key={concept.id}>
          <button type="button" className="panel-pick" disabled={disabled} onClick={() => onOpen(concept)}
            title={`Open ${concept.name}`}><span>{concept.name}</span><span className="muted">{where(concept)}</span></button>
        </li>)}</ul>
      : <p className="muted">Concepts appear here once you’ve mastered everything they build on.</p>}
    <h3>Worth reviewing</h3>
    {review.length
      ? <ul className="readiness">{review.map((concept) => <li key={concept.id}>
          <button type="button" className="panel-pick" disabled={disabled} onClick={() => onOpen(concept)}
            title={`Open ${concept.name}`}><span>{concept.name} <span className="muted">{where(concept)}</span></span>
            <span>{Math.round(concept.readiness * 100)}%</span></button>
        </li>)}</ul>
      : <p className="muted">Nothing to review yet. Concepts you find hard will show up here.</p>}
    <p className="muted">{mastered} mastered · {learning} learning · {struggling} to review, from the answers the tutor has checked.</p>
  </div>;
}

// The backend stores UTC times without a zone marker; read them as UTC and show local time.
function savedAt(text) {
  const utc = /(Z|[+-]\d\d:\d\d)$/.test(text) ? text : `${text}Z`;
  return new Date(utc).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
}

function LeftOff({ state, error, sessionId, onRetry, onOpenTopic, onResume, disabled }) {
  if (error) return <div className="reference-content"><p className="muted" role="status">Your saved place is unavailable right now.</p><button onClick={onRetry}>Retry</button></div>;
  if (!state) return <p className="reference-content muted" role="status">Loading…</p>;
  if (!state.topic) return <p className="reference-content muted">Open a textbook topic and your place will be saved here, so you can pick it up in a later chat.</p>;
  const subject = state.topic.chapter.subject === 'maths' ? 'Maths' : 'Science';
  const here = sessionId && state.session_id === sessionId;
  return <div className="reference-content left-off">
    <p><strong>{state.topic.heading}</strong></p>
    <p className="muted">Class {state.topic.chapter.grade} {subject} · Chapter {state.topic.chapter.chapter}
      {state.updated_at && ` · ${savedAt(state.updated_at)}`}</p>
    {state.detour.length > 0 && <>
      <p>Stepped back here from:</p>
      <ol className="detour">{[...state.detour].reverse().map((topic, index) => <li key={`${topic.heading}-${index}`}>
        <button type="button" className="panel-pick" disabled={disabled} onClick={() => onOpenTopic(topic)} title={`Open ${topic.heading}`}>
          <span>{topic.heading} <span className="muted">Class {topic.chapter.grade} · Ch {topic.chapter.chapter}</span></span>
        </button>
      </li>)}</ol>
    </>}
    {here
      ? <p className="muted">Saved from this chat.</p>
      : <>
        <p className="muted">Saved from an earlier chat.</p>
        <button type="button" disabled={disabled} onClick={onResume}>Continue where I left off</button>
      </>}
  </div>;
}

function Search({ selection }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const request = useRef(null);

  useEffect(() => () => request.current?.abort(), []);

  async function submit(event) {
    event.preventDefault();
    if (!query.trim() || busy) return;
    const controller = new AbortController();
    request.current = controller;
    const params = new URLSearchParams({ course_id: selection.course_id, q: query.trim() });
    for (const field of ['grade', 'subject']) if (selection[field]) params.set(field, selection[field]);
    if (selection.chapter) {
      params.set('book_code', selection.chapter.book_code);
      params.set('chapter', selection.chapter.chapter);
    }
    setBusy(true);
    setError('');
    setResults(null);
    try { setResults(await api(`/search?${params}`, undefined, controller.signal)); }
    catch (error) { if (!controller.signal.aborted) setError(error.message); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }

  return <div className="reference-content">
    <form className="search-form" onSubmit={submit}>
      <label htmlFor="source-query">Topic or keyword</label>
      <input id="source-query" type="search" value={query} onChange={(event) => setQuery(event.target.value)} maxLength={2000} required />
      <button disabled={busy || !query.trim()}>{busy ? 'Searching…' : 'Search'}</button>
    </form>
    {error && <p className="error" role="alert">{error} Try the search again.</p>}
    {results?.length === 0 && <p className="muted" role="status">No sources found. Try another keyword.</p>}
    {results?.map(({ material, passage_id, concept_id }, index) => (
      <details className="search-hit" key={passage_id ?? `${concept_id}-${index}`}>
        <summary>{sourceTitle(material)}</summary>
        <div className="source-text"><RichText text={material.text} /></div>
        {material.url && <SourceLink resource={material} />}
      </details>
    ))}
  </div>;
}

function MathTools() {
  const [visual, setVisual] = useState('fraction');
  const [value, setValue] = useState(3);
  return <div className="reference-content math-tools">
    <label>Visual<select value={visual} onChange={(event) => setVisual(event.target.value)}>
      <option value="fraction">Fraction bar</option><option value="percent">Percentage grid</option><option value="line">Number line</option><option value="graph">Linear graph</option>
    </select></label>
    <label>Value <output>{value}</output><input type="range" min="0" max="10" value={value} onChange={(event) => setValue(Number(event.target.value))} /></label>
    {visual === 'fraction' && <figure>
      <div className="fraction-model" aria-hidden="true">{Array.from({ length: 10 }, (_, index) => <span key={index} data-filled={index < value} />)}</div>
      <figcaption><RichText text={`\\(\\frac{${value}}{10} = ${value / 10}\\)`} /> of one whole</figcaption>
    </figure>}
    {visual === 'percent' && <figure>
      <div className="percent-model" aria-hidden="true">{Array.from({ length: 100 }, (_, index) => <span key={index} data-filled={index < value * 10} />)}</div>
      <figcaption>{value * 10}% of 100 squares</figcaption>
    </figure>}
    {visual === 'line' && <figure>
      <div className="number-model" aria-hidden="true"><i style={{ left: `${value * 10}%` }} /><span>0</span><span>5</span><span>10</span></div>
      <figcaption>{value} on a number line from 0 to 10</figcaption>
    </figure>}
    {visual === 'graph' && <figure>
      <div className="graph-model" aria-hidden="true"><i style={{ left: `${value * 10}%`, bottom: `${value * 10}%` }} /><span className="axis-y">y</span><span className="axis-x">x</span></div>
      <figcaption>Point ({value}, {value}) on <RichText text={'\\(y=x\\)'} /></figcaption>
    </figure>}
  </div>;
}

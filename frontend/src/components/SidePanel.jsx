import { useEffect, useRef, useState } from 'react';
import { api } from '../api.js';
import { RichText, SourceLink, sourceTitle } from './RichText.jsx';

export default function SidePanel({ selection, isTextbook, progress, progressError, onRetry }) {
  const [toolsOpened, setToolsOpened] = useState(false);
  return (
    <aside className="reference" aria-label="Study references">
      {!isTextbook && <details open>
        <summary>Your progress</summary>
        <Progress progress={progress} error={progressError} onRetry={onRetry} />
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

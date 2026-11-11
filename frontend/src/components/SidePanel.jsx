export default function SidePanel({ progress, resource }) {
  const rows = progress?.concepts ?? [];
  const attempts = rows.reduce((n, c) => n + c.attempts, 0);
  const correct = rows.reduce((n, c) => n + c.correct, 0);

  return (
    <aside className="panel" aria-label="Progress and textbook sources">
      <div className="panel-header"><h2>Progress &amp; sources</h2></div>
      <div className="panel-content">
        <div className="progress-labels">
          <span>Answers so far</span>
          <span>{attempts ? `${correct}/${attempts} correct` : 'No answers yet'}</span>
        </div>
        <div className="progress-bar"><div className="progress-fill" style={{ width: `${attempts ? (100 * correct) / attempts : 0}%` }} /></div>

        <h3 className="side-title">Readiness by concept</h3>
        <div id="readiness-list">
          {rows.length === 0 ? <small>Answer a question to see estimates.</small>
            : rows.map((c) => (
              <div key={c.concept_id}>
                {c.name}: {Math.round(c.readiness * 100)}%{' '}
                <small>({c.attempts ? `${c.correct}/${c.attempts} correct` : 'not tried'})</small>
              </div>
            ))}
        </div>

        <h3 className="side-title">Textbook source</h3>
        <div className="evidence-box">
          {resource ? (
            <p>
              {resource.url
                ? <a href={resource.url} target="_blank" rel="noopener noreferrer">{resource.source}{resource.page ? `, ${resource.page}` : ''}</a>
                : `${resource.source}${resource.page ? `, ${resource.page}` : ''}`}
            </p>
          ) : <p>The page the tutor uses appears here when it explains or gives a hint.</p>}
        </div>
      </div>
    </aside>
  );
}

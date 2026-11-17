import { Icon } from './Icon.jsx';

// Concepts grouped by level (1 = foundation). Clicking one tells the tutor where the learner is stuck.
export default function ConceptMap({ concepts, currentId, disabled, onPick }) {
  const names = Object.fromEntries(concepts.map((c) => [c.id, c.name]));
  const levels = [...new Set(concepts.map((c) => c.level))].sort((a, b) => a - b);

  return (
    <nav className="panel" aria-label="Concepts in this course">
      <div className="panel-header"><h2>What are you stuck on?</h2></div>
      <div className="panel-content">
        <p className="nav-hint">Pick a concept, or just type your question.</p>
        {levels.map((level) => (
          <section key={level}>
            <h3 className="side-title">Level {level}</h3>
            <div className="nav-list" style={{ marginBottom: 16 }}>
              {concepts.filter((c) => c.level === level).map((c) => (
                <button key={c.id} type="button" disabled={disabled}
                  className={`nav-item${currentId === c.id ? ' active' : ''}`}
                  aria-current={currentId === c.id ? 'true' : undefined}
                  onClick={() => onPick(c)}>
                  <span className="grow">
                    <strong>{c.name}</strong>
                    {c.prerequisites.length > 0 && <small>builds on {c.prerequisites.map((p) => names[p] ?? p).join(', ')}</small>}
                  </span>
                  <Icon name="chevron" />
                </button>
              ))}
            </div>
          </section>
        ))}
      </div>
    </nav>
  );
}

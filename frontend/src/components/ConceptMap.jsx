import { useState } from 'react';
import { Icon } from './Icon.jsx';

export default function ConceptMap({ concepts, currentId, topics, scopeName, disabled, isTextbook, onPick, onTopic }) {
  const names = Object.fromEntries(concepts.map((concept) => [concept.id, concept.name]));
  const levels = [...new Set(concepts.map((concept) => concept.level))].sort((a, b) => a - b);
  const title = isTextbook ? 'Chapter topics' : 'Concepts';
  const [expanded] = useState(() => !matchMedia('(max-width: 700px)').matches);

  return (
    <aside className="course-rail">
      <details className="rail-details" open={expanded}>
        <summary>{title}</summary>
        <nav aria-label={title}>
          {isTextbook ? <>
            <p className="scope-name">{scopeName}</p>
            {topics?.length ? topics.map((topic) => <button className="concept" key={topic} disabled={disabled}
              onClick={() => onTopic(topic)}><span>{topic}</span><Icon name="chevron" /></button>)
              : <p className="muted">Choose a chapter to browse its topics, or ask about any topic in the open lesson.</p>}
          </> : !levels.length && !disabled ? <p className="muted">This course has no concepts yet.</p> : levels.map((level) => (
            <section className="concept-group" key={level}>
              <h2 className="label">Level {level}</h2>
              {concepts.filter((concept) => concept.level === level).map((concept) => (
                <button className="concept" key={concept.id} disabled={disabled} aria-current={currentId === concept.id ? 'true' : undefined} onClick={() => onPick(concept)}>
                  <span><strong>{concept.name}</strong>
                    {concept.prerequisites.length > 0 && <small>Builds on {concept.prerequisites.map((id) => names[id] ?? id).join(', ')}</small>}
                  </span><Icon name="chevron" />
                </button>
              ))}
            </section>
          ))}
        </nav>
      </details>
    </aside>
  );
}

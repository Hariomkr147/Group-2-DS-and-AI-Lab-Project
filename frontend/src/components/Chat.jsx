import { useEffect, useRef, useState } from 'react';
import { Icon } from './Icon.jsx';

const ACTION_LABEL = {
  ask: 'Question', probe: 'Question', hint: 'Hint', backtrack: 'Going back a step',
  advance: 'Moving forward', done: 'Done', redirect: 'Let us stay on topic',
};

export default function Chat({ messages, busy, ready, banner, onSend, draft, onDraftUsed }) {
  const [text, setText] = useState('');
  const historyRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (draft) { setText(draft); onDraftUsed(); inputRef.current?.focus(); }
  }, [draft, onDraftUsed]);

  useEffect(() => {
    const el = historyRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  async function submit() {
    const value = text.trim();
    if (!value || busy || !ready) return;
    setText('');
    await onSend(value);
  }

  return (
    <main className="panel chat-panel">
      <div className="panel-header">
        <h2>Tutor</h2>
        <span className="badge">{busy ? 'Thinking…' : ready ? 'Ready' : 'Starting…'}</span>
      </div>

      <div className="chat-history" ref={historyRef} aria-live="polite">
        {messages.length === 0 && (
          <div className="empty">
            <strong>Ask about a concept</strong>
            Type what you are stuck on, for example "I am stuck on percentages". The tutor asks questions to find the gap and never just gives the answer.
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`message msg-${m.role}`}>
            <div className="msg-bubble">{m.text}</div>
            {m.meta && <div className="msg-meta">{m.meta}</div>}
          </div>
        ))}
      </div>

      <div className="chat-input-area">
        {banner && <div className="state-banner visible" role="status"><Icon name="alert" /><span>{banner}</span></div>}
        <div className="input-row">
          <input ref={inputRef} type="text" className="chat-input" aria-label="Your question or answer" maxLength={2000}
            disabled={!ready || busy} placeholder="Ask a question or type your answer…" value={text}
            onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && submit()} />
          <button type="button" className="btn btn-primary" disabled={!ready || busy || !text.trim()} onClick={submit}>
            <Icon name="send" />Send
          </button>
        </div>
        <p className="help">Your answers update your progress. Off-topic messages and requests for the answer are redirected.</p>
      </div>
    </main>
  );
}

export { ACTION_LABEL };

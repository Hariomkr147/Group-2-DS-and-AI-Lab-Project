import { useEffect, useRef, useState } from 'react';
import { Icon } from './Icon.jsx';
import { RichText, SourceLink } from './RichText.jsx';

const ACTION_LABEL = {
  ask: 'Question', explain: 'Explanation', guide: 'Next step', probe: 'Question', hint: 'Hint', backtrack: 'Prerequisite',
  advance: 'Moving forward', done: 'Completed', redirect: 'Redirect',
};

// Which layer each backend step belongs to: the kind sets the marker colour, the name is read out with the step.
const STAGE_KIND = {
  received: ['start', 'Start'], replay: ['start', 'Start'],
  router: ['guard', 'Guardrail'], input_check: ['guard', 'Guardrail'], guardrail: ['guard', 'Guardrail'],
  output_check: ['guard', 'Guardrail'],
  conversation: ['understand', 'Understanding'], classifier: ['understand', 'Understanding'],
  lesson: ['understand', 'Understanding'], retrieval: ['understand', 'Retrieval'],
  grading: ['learner', 'Assessment'], diagnosis: ['learner', 'Assessment'],
  learner_model: ['learner', 'Learner model'], controller: ['learner', 'Controller'],
  generation: ['model', 'Model'], reply: ['model', 'Reply'],
};

function Steps({ steps, live }) {
  return (
    <ol className={`trace-steps${live ? ' live' : ''}`}>
      {steps.map((step, index) => {
        const [kind, layer] = STAGE_KIND[step.stage] ?? ['start', 'Step'];
        const current = live && index === steps.length - 1;
        return (
          <li key={index} className={`trace-step ${kind}${current ? ' current' : ''}`} aria-current={current ? 'step' : undefined}>
            <span className="trace-marker" aria-hidden="true" />
            <span className="trace-layer">{layer}</span>
            <span className="trace-title">{step.title}</span>
            {step.detail && <span className="trace-detail">{step.detail}</span>}
          </li>
        );
      })}
    </ol>
  );
}

export default function Chat({ session, pending, sending, steps = [], startupError, messageError, isTextbook, onSend, onRetryStart, onRetry, onEdit }) {
  const [text, setText] = useState('');
  const history = useRef(null);
  const input = useRef(null);
  const turns = session?.history ?? [];
  const canAskForHint = session?.current_concept && turns.at(-1)?.detail?.action !== 'done';

  useEffect(() => {
    const element = history.current;
    element.scrollTop = element.scrollHeight;
  }, [session?.history, pending?.request_id, steps.length]);

  function submit(event) {
    event.preventDefault();
    if (!text.trim() || !session || pending) return;
    onSend(text.trim());
    setText('');
  }

  return (
    <div className="chat">
      <div className="transcript" ref={history} role="log" aria-label="Tutor conversation" tabIndex={0}>
        {!session ? <div className="chat-empty">
          <h2>{startupError ? 'Couldn’t open this lesson' : 'Opening your lesson…'}</h2>
          {startupError && <><p className="error" role="alert">{startupError}</p><button onClick={onRetryStart}>Retry opening lesson</button></>}
        </div> : turns.length === 0 && !pending ? <div className="chat-empty">
          <span className="book-mark"><Icon name="book" /></span>
          <h2>Where are you stuck?</h2>
          <p>{isTextbook ? 'Ask about a textbook topic or paste the question you’re working on.' : 'Pick a concept to begin, or type a question in your own words.'}</p>
        </div> : turns.map((turn, index) => (
          <article className={`turn ${turn.role}`} key={turn.request_id ?? index}>
            <div className="turn-label">{turn.role === 'tutor' ? 'Tutor' : 'You'}{turn.detail?.action && <span>{ACTION_LABEL[turn.detail.action]}</span>}</div>
            <div className="turn-content"><RichText text={turn.text} /></div>
            {turn.detail?.wrong_step && <p className="feedback">Check step {turn.detail.wrong_step} of your working.</p>}
            {turn.detail?.misconception && <p className="feedback">Possible sticking point · {turn.detail.misconception.replaceAll('_', ' ')}</p>}
            {turn.detail?.resource && <div className="citation"><Icon name="book" /><SourceLink resource={turn.detail.resource} /></div>}
            {turn.steps?.length > 0 && <details className="trace">
              <summary>How this reply was made · {turn.steps.length} steps</summary>
              <Steps steps={turn.steps} />
            </details>}
          </article>
        ))}
        {pending && <article className="turn learner"><div className="turn-label">You <span>{sending ? 'Responding…' : 'Awaiting confirmation'}</span></div><div className="turn-content">{pending.text}</div></article>}
        {pending && sending && <article className="turn tutor working" aria-live="polite" aria-busy="true">
          <div className="turn-label">Tutor <span>Working behind the scenes…</span></div>
          {steps.length ? <Steps steps={steps} live /> : <p className="trace-waiting">Sending your message…</p>}
        </article>}
      </div>
      <form className="composer" onSubmit={submit}>
        {pending && !sending && <div className="message-error" role="alert">
          <p>{messageError || 'This message hasn’t been confirmed by the server.'}</p>
          <div className="actions"><button type="button" className="primary" onClick={onRetry}>Retry message</button>
            {onEdit && <button type="button" onClick={() => { setText(pending.text); onEdit(); requestAnimationFrame(() => input.current?.focus()); }}>Edit message</button>}</div>
        </div>}
        <div className="composer-label">
          <label htmlFor="working">Your question or answer</label>
          <span className="tip">
            <button type="button" className="tip-button" aria-label="About this tutor" aria-describedby="ai-note">ⓘ</button>
            <span id="ai-note" role="tooltip" className="tip-text">The tutor is an AI assistant and can make mistakes. Please check important answers with your textbook or teacher.</span>
          </span>
        </div>
        <textarea id="working" ref={input} rows={3} maxLength={2000} value={text}
          placeholder="Type a question, an answer, or your working…" onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            // Enter sends (same as the Send button); Shift+Enter adds a new line.
            if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault();
              event.currentTarget.form.requestSubmit();
            }
          }} />
        <div className="composer-footer">
          <div className="actions">
            {canAskForHint && <button type="button" disabled={Boolean(pending)} onClick={() => onSend('Can I have a hint?')}>Ask for a hint</button>}
            <button className="primary" disabled={!text.trim() || !session || Boolean(pending)}><Icon name="send" />{sending ? 'Responding…' : 'Ask'}</button>
          </div>
        </div>
      </form>
    </div>
  );
}

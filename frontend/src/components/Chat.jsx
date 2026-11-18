import { useEffect, useRef, useState } from 'react';
import { Icon } from './Icon.jsx';
import { RichText, SourceLink } from './RichText.jsx';

const ACTION_LABEL = {
  ask: 'Question', explain: 'Explanation', guide: 'Next step', probe: 'Question', hint: 'Hint', backtrack: 'Prerequisite',
  advance: 'Moving forward', done: 'Completed', redirect: 'Redirect',
};

export default function Chat({ session, pending, sending, startupError, messageError, isTextbook, onSend, onRetryStart, onRetry, onEdit }) {
  const [text, setText] = useState('');
  const history = useRef(null);
  const input = useRef(null);
  const turns = session?.history ?? [];
  const canAskForHint = session?.current_concept && turns.at(-1)?.detail?.action !== 'done';

  useEffect(() => {
    const element = history.current;
    element.scrollTop = element.scrollHeight;
  }, [session?.history, pending?.request_id]);

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
          </article>
        ))}
        {pending && <article className="turn learner"><div className="turn-label">You <span>{sending ? 'Sending…' : 'Awaiting confirmation'}</span></div><div className="turn-content">{pending.text}</div></article>}
      </div>
      <form className="composer" onSubmit={submit}>
        {pending && !sending && <div className="message-error" role="alert">
          <p>{messageError || 'This message hasn’t been confirmed by the server.'}</p>
          <div className="actions"><button type="button" className="primary" onClick={onRetry}>Retry message</button>
            {onEdit && <button type="button" onClick={() => { setText(pending.text); onEdit(); requestAnimationFrame(() => input.current?.focus()); }}>Edit message</button>}</div>
        </div>}
        <label htmlFor="working">Your question or answer</label>
        <textarea id="working" ref={input} rows={3} maxLength={2000} value={text}
          placeholder="Type a question, an answer, or your working…" onChange={(event) => setText(event.target.value)} />
        <div className="composer-footer">
          <p className="muted">Show one step per line.</p>
          <div className="actions">
            {canAskForHint && <button type="button" disabled={Boolean(pending)} onClick={() => onSend('Can I have a hint?')}>Ask for a hint</button>}
            <button className="primary" disabled={!text.trim() || !session || Boolean(pending)}><Icon name="send" />{sending ? 'Sending…' : 'Send'}</button>
          </div>
        </div>
      </form>
    </div>
  );
}

import { useEffect, useRef, useState } from 'react';
import { api } from '../api.js';
import { Icon } from './Icon.jsx';

const formatDate = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' });

export default function PreviousChats({ current, onCurrent, onNew, onResume, disabled }) {
  const dialog = useRef(null);
  const opening = useRef(null);
  useEffect(() => () => opening.current?.abort(), []);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [next, setNext] = useState(null);
  const [page, setPage] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    setBusy(true);
    setError('');
    api('/sessions' + (page ? `?before=${page}` : ''), undefined, controller.signal)
      .then(({ items, next }) => {
        setItems((old) => page ? [...old, ...items] : items);
        setNext(next);
      })
      .catch((e) => { if (!controller.signal.aborted) setError(e.message); })
      .finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => controller.abort();
  }, [open, page, retry]);

  async function resume(item) {
    if (item && item.session_id === current) { onCurrent(); return dialog.current.close(); }
    setBusy(true);
    opening.current = new AbortController();
    try {
      if (item) await onResume(item, opening.current.signal);
      else await onNew(opening.current.signal);
      dialog.current?.close();
    } catch (e) {
      if (!opening.current.signal.aborted) setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return <>
    <button className="history-trigger" disabled={disabled} onClick={() => {
      setItems([]); setNext(null); setPage(null); setBusy(true); setError(''); setOpen(true); dialog.current.showModal();
    }}><Icon name="history" />Previous chats</button>
    <dialog className="chat-history" ref={dialog} aria-labelledby="history-heading" onClose={() => { opening.current?.abort(); setOpen(false); }}>
      <header><h2 id="history-heading">Previous chats</h2><button autoFocus onClick={() => dialog.current.close()}>Close</button></header>
      <p className="muted">Everyone using this project sign-in can reopen these chats.</p>
      <button className="primary" disabled={busy} onClick={() => resume(null)}>New chat in this lesson</button>
      <ul>{items.map((item) => <li key={item.session_id}>
        <button disabled={busy} onClick={() => resume(item)}>
          <span><strong>{item.title}</strong><small>{item.course_title}
            {item.scope.grade && ` · Class ${item.scope.grade}`}{item.scope.subject && ` · ${item.scope.subject}`}
            {item.scope.chapter != null && ` · Chapter ${item.scope.chapter}`}{item.session_id === current && ' · Current chat'}</small>
            <small><time dateTime={item.updated_at}>{formatDate.format(new Date(item.updated_at))}</time></small></span>
          <Icon name="chevron" />
        </button>
      </li>)}</ul>
      {busy && <p role="status">Loading…</p>}
      {!busy && !error && !items.length && <p>Your conversations will appear here after your first message.</p>}
      {error && <p role="alert">{error} <button onClick={() => { setPage(null); setRetry(retry + 1); }}>Reload list</button></p>}
      {next && !busy && !error && <button onClick={() => setPage(next)}>Show older chats</button>}
    </dialog>
  </>;
}

let activeSession = null, availableConcepts = [], busy = false, retryRequest = null;
const nav = {grade: null, chapter: null};
const byId = id => document.getElementById(id);
const esc = text => String(text ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// ponytail: fixes one known OCR split in a section heading; fix at extraction when more chapters show it.
const tidy = t => String(t ?? '').replace('Ser vices Ta x', 'Services Tax');
const chapterOf = c => c.chapter ?? c.subject;
const icon = name => `<svg class="icon" aria-hidden="true"><use href="#i-${name}"/></svg>`;

async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) {
    const detail = data.detail || data;
    const error = new Error(typeof detail === 'string' ? detail : (detail.message || `Request failed (${response.status})`));
    error.needsModelUrl = !!detail.needs_model_url; throw error;
  }
  return data;
}

function addMessage(role, text, action='') {
  const history = byId('chat-history');
  history.querySelector('.empty')?.remove();
  const row = document.createElement('div'); row.className = `message msg-${role}`;
  const bubble = document.createElement('div'); bubble.className = 'msg-bubble'; bubble.textContent = text;
  const meta = document.createElement('div'); meta.className = 'msg-meta'; meta.textContent = action;
  row.append(bubble, meta); history.append(row); history.scrollTop = history.scrollHeight;
}

/* ---------- Class -> Chapter -> Topic ---------- */
function crumb(label, onclick) {
  const b = document.createElement('button'); b.type = 'button'; b.textContent = label; b.onclick = onclick; return b;
}
function sep() { const s = document.createElement('span'); s.textContent = '›'; s.setAttribute('aria-hidden', 'true'); return s; }
function here(label) { const s = document.createElement('span'); s.className = 'here'; s.textContent = label; s.setAttribute('aria-current', 'page'); return s; }

function renderNav() {
  const list = byId('nav-list'), crumbs = byId('nav-breadcrumb');
  list.replaceChildren(); crumbs.replaceChildren(); list.className = 'nav-list';
  if (nav.grade === null) {
    byId('nav-step').textContent = 'Step 1 of 3'; byId('nav-hint').textContent = 'Pick your class.';
    crumbs.append(here('All classes'));
    list.classList.add('classes');
    const grades = [...new Set(availableConcepts.map(c => c.level))].sort((a, b) => a - b);
    for (const g of grades) {
      const chapters = new Set(availableConcepts.filter(c => c.level === g).map(chapterOf));
      const b = document.createElement('button'); b.type = 'button'; b.className = 'nav-item class-tile';
      b.innerHTML = `<strong>Class ${esc(g)}</strong><small>${chapters.size} chapter${chapters.size === 1 ? '' : 's'}</small>`;
      b.onclick = () => { nav.grade = g; nav.chapter = null; renderNav(); };
      list.append(b);
    }
  } else if (nav.chapter === null) {
    byId('nav-step').textContent = 'Step 2 of 3'; byId('nav-hint').textContent = 'Pick a chapter.';
    crumbs.append(crumb('All classes', () => { nav.grade = null; renderNav(); }), sep(), here(`Class ${nav.grade}`));
    const byChapter = new Map();
    for (const c of availableConcepts.filter(c => c.level === nav.grade)) {
      if (!byChapter.has(chapterOf(c))) byChapter.set(chapterOf(c), []);
      byChapter.get(chapterOf(c)).push(c);
    }
    for (const [name, topics] of byChapter) {
      const first = topics[0], practice = topics.reduce((n, t) => n + (t.practice_count || 0), 0);
      const subject = first.subject === 'science' ? 'Science' : 'Maths';
      const b = document.createElement('button'); b.type = 'button'; b.className = 'nav-item';
      b.innerHTML = `${icon('book')}<span class="grow"><strong>${first.chapter_number ? `Ch ${esc(first.chapter_number)} · ` : ''}${esc(tidy(name))}</strong>`
        + `<small>${esc(first.book ?? '')} · ${topics.length} topic${topics.length === 1 ? '' : 's'}${practice ? ` · ${practice} practice questions` : ''}</small></span>`
        + `<span class="tag ${subject.toLowerCase()}">${subject}</span>`;
      b.onclick = () => { nav.chapter = name; renderNav(); };
      list.append(b);
    }
  } else {
    byId('nav-step').textContent = 'Step 3 of 3'; byId('nav-hint').textContent = 'Pick a topic to start chatting.';
    crumbs.append(crumb('All classes', () => { nav.grade = null; nav.chapter = null; renderNav(); }), sep(),
      crumb(`Class ${nav.grade}`, () => { nav.chapter = null; renderNav(); }), sep(), here(tidy(nav.chapter)));
    const topics = availableConcepts.filter(c => c.level === nav.grade && chapterOf(c) === nav.chapter)
      .sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
    for (const c of topics) {
      const b = document.createElement('button'); b.type = 'button'; b.className = 'nav-item';
      b.classList.toggle('active', activeSession?.target_concept.id === c.id);
      if (activeSession?.target_concept.id === c.id) b.setAttribute('aria-current', 'true');
      const prereq = c.prerequisites?.length ? ` · builds on ${c.prerequisites.map(p => esc(tidy(p.title))).join(', ')}` : '';
      b.innerHTML = `<span class="grow"><strong>${esc(tidy(c.title))}</strong><small>${c.practice_count ? 'Explanations and practice' : 'Explanations from the textbook'}${prereq}</small></span>`
        + (c.practice_count ? `<span class="tag practice">${c.practice_count} Q</span>` : '') + icon('chevron');
      b.onclick = () => startSession(c.id);
      list.append(b);
    }
  }
  for (const b of list.querySelectorAll('button')) b.disabled = busy;
}

/* ---------- Chat ---------- */
function updateUI() {
  const progress = activeSession.practice_progress;
  byId('session-status-badge').textContent = activeSession.state + (progress?.total ? ` · ${progress.solved}/${progress.total} questions` : '');
  byId('current-concept-header').textContent = tidy(activeSession.current_concept.title);
  byId('backtrack-banner').classList.toggle('visible', activeSession.is_backtracking);
  byId('backtrack-banner-text').textContent = `Practising ${tidy(activeSession.current_concept.title)} first, then returning to ${tidy(activeSession.target_concept.title)}.`;
  byId('answer-btn').hidden = !activeSession.active_question;
}
function setBusy(value) {
  busy = value;
  const noTopic = !activeSession;
  for (const b of document.querySelectorAll('.chat-input-area button')) b.disabled = value || noTopic;
  byId('user-input').disabled = value || noTopic; byId('working-input').disabled = value || noTopic;
  byId('send-btn').textContent = ''; byId('send-btn').insertAdjacentHTML('beforeend', value ? 'Working…' : `${icon('send')}Send`);
  renderNav();
}
function showError(error) {
  addMessage('tutor', error.message, 'Action not completed');
  byId('llm-badge').textContent = error.needsModelUrl ? 'Fine-tuned model needs a new URL' : 'Please retry';
  if (error.needsModelUrl) { byId('model-connection').hidden = false; byId('connection-message').textContent = error.message; }
  byId('retry-btn').hidden = !retryRequest;
}
async function startSession(id) {
  if (busy) return; setBusy(true);
  try {
    activeSession = await api('/api/sessions', {target_concept_id: id, learner_id: 'Hariom'}); retryRequest = null; byId('retry-btn').hidden = true;
    byId('chat-history').replaceChildren(); updateUI(); addMessage('tutor', activeSession.initial_message, 'Welcome');
    renderEvidence([], 'NCERT pages appear here when the tutor explains or gives a hint.'); await fetchProgress();
  } catch (e) { showError(e); } finally { setBusy(false); byId('user-input').focus(); }
}
function renderEvidence(citations, text) {
  const box = document.createElement('div'); box.className = 'evidence-box';
  const p = document.createElement('p'); p.textContent = text; box.append(p);
  for (const c of citations ?? []) {
    const link = document.createElement('a'); link.textContent = c.label; link.href = c.url; link.target = '_blank'; link.rel = 'noopener noreferrer';
    box.append(link, document.createElement('br'));
  }
  byId('evidence-container').replaceChildren(box);
}
async function fetchProgress() {
  const p = await api(`/api/sessions/${activeSession.session_id}/progress`);
  byId('accuracy-text').textContent = p.total_attempts ? `${p.correct_attempts}/${p.total_attempts} correct` : 'No answers yet';
  byId('accuracy-fill').style.width = `${100 * p.accuracy}%`;
  const target = availableConcepts.find(c => c.id === activeSession.target_concept.id);
  const inChapter = new Set(availableConcepts.filter(c => target && chapterOf(c) === chapterOf(target) && c.level === target.level).map(c => c.id));
  const rows = p.concept_readiness.filter(c => inChapter.has(c.concept_id) && (c.origin === 'akt_prediction' || c.readiness > 0 || c.concept_id === target?.id));
  byId('readiness-list').innerHTML = rows.length ? rows.map(c => `<div>${esc(tidy(c.title))}: ${Math.round(c.readiness * 100)}% <small>(${c.origin === 'akt_prediction' ? 'AKT estimate' : 'practice estimate'})</small></div>`).join('')
    : '<small>Answer a practice question to see estimates.</small>';
  const badge = document.querySelector('.header-badges .badge'); if (badge) badge.textContent = p.kt_status;
}
async function submitMessage(intent='message') {
  if (busy || !activeSession) return;
  const labels = {explain:'Explain concept', hint:'I would like a hint.', practice:'Try a question'};
  if (intent !== 'retry') {
    const text = ['message','answer'].includes(intent) ? byId('user-input').value.trim() : labels[intent];
    if (!text) return;
    retryRequest = {path:`/api/sessions/${activeSession.session_id}/messages`,
      body:{text, working:['message','answer'].includes(intent) ? byId('working-input').value.trim() : '', intent, request_id:crypto.randomUUID()}};
    addMessage('learner', text + (retryRequest.body.working ? '\nWorking: ' + retryRequest.body.working : ''));
  }
  if (!retryRequest) return;
  setBusy(true); byId('llm-badge').textContent = 'Preparing a reply…';
  let succeeded = false;
  try {
    const result = await api(retryRequest.path, retryRequest.body);
    activeSession = result.session; updateUI();
    addMessage('tutor', result.reply, result.action === 'HINT' && result.hint_level ? `Hint ${result.hint_level} of 3` : result.action);
    const m = result.misconception, candidate = m?.candidates?.find(c => c.misconception_id === m.misconception_id);
    if (candidate) addMessage('tutor', `Possible sticking point: ${candidate.text}. This suggestion is unconfirmed.`, 'Learning support');
    byId('llm-badge').textContent = result.model_status === 'fine_tuned_qwen' ? 'Your fine-tuned Qwen' : 'Lesson controller';
    renderEvidence([...(result.citations || []), ...(activeSession.active_question ? [activeSession.active_question.citation] : [])], result.raw_evidence || '');
    if (['message','answer'].includes(retryRequest.body.intent)) { byId('user-input').value = ''; byId('working-input').value = ''; }
    retryRequest = null; byId('retry-btn').hidden = true; succeeded = true;
    await fetchProgress();
  } catch (e) { if (succeeded) addMessage('tutor', 'Your response was saved, but progress could not refresh.', 'Progress'); else showError(e); }
  finally { setBusy(false); }
}
function handleQuickChip(text) { byId('user-input').value = text; return submitMessage(); }
async function connectModel() {
  if (busy) return; setBusy(true);
  try {
    await api('/api/model/connection', {url: byId('model-url').value});
    byId('model-connection').hidden = true; byId('llm-badge').textContent = 'Fine-tuned model connected';
    addMessage('tutor', 'Your model is connected. Retry your last action to continue.', 'Connected');
  } catch (e) { byId('connection-message').textContent = e.message; }
  finally { setBusy(false); }
}
window.onload = async () => {
  setBusy(false);
  try {
    availableConcepts = await api('/api/concepts'); renderNav();
    const status = await api('/api/status');
    document.querySelector('.header-badges .badge').textContent = status.kt;
    byId('llm-badge').textContent = 'Fine-tuned Qwen · checked when you ask for teaching';
  } catch (e) { addMessage('tutor', e.message, 'Startup error'); }
};

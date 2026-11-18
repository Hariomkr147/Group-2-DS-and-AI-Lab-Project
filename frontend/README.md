# Frontend

React (Vite) workspace for the NCERT Socratic Tutor, backed by FastAPI.

## Run

Needs Node 22 and a running backend (see [backend setup](../backend/README.md)).

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

Sign in with `ADMIN_USERNAME` and `ADMIN_PASSWORD` from `backend/.env`. In dev, `/api` is forwarded to `http://127.0.0.1:8000` (change with `VITE_API_TARGET` in `.env`, see `.env.example`).

`npm run build` writes a static build to `dist/`.

## How it works

Choose a course pack for graded chat, practice and diagnostics, or choose the NCERT corpus for ungraded textbook guidance. Textbook sessions can be scoped to a class, subject and chapter. Chapter topics and source search use the approved release configured on the backend.

Sign-in, open sessions and active assessments survive reload in the same browser tab. A message retry keeps its request ID so the backend can return an already saved reply. Learners sharing the team account also share progress totals.

The visual design uses paper-toned surfaces and a serif display face for textbook hierarchy. Teal marks primary actions and the selected concept. Layout rhythm changes from compact navigation to wide working space. Motion is limited to control feedback.

## Browser checks

With the backend dependencies installed, run these commands from `frontend/`.

```bash
npm run build
npx playwright install chromium --only-shell
uv run --project ../backend npm test
```

The tests start FastAPI on localhost with a temporary database and fixture textbook evidence.

## Production

FastAPI serves the built `dist/` directory and the same-origin `/api/` routes. For separate static hosting, configure a same-origin proxy for `/api/` and serve the UI over HTTPS.

# Frontend

React (Vite) UI for the NCERT Socratic Tutor. The layout follows the `mock-app/static` pilot page, but it talks to the real backend in `../backend`.

## Run

Needs Node 18+ and a running backend (see `backend/README.md`).

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

Sign in with `ADMIN_USERNAME` and `ADMIN_PASSWORD` from `backend/.env`. In dev, `/api` is forwarded to `http://127.0.0.1:8000` (change with `VITE_API_TARGET` in `.env`, see `.env.example`).

`npm run build` writes a static build to `dist/`.

## How it works

1. Sign in: `POST /auth/login` returns a token, kept in `sessionStorage` (cleared when the tab closes). Every other call sends it as a bearer token; an expired token returns you to the sign-in page.
2. After sign-in it loads the first course (`GET /courses`, `/courses/{id}/concepts`) and opens a session (`POST /sessions`).
3. Chat: `POST /sessions/{id}/messages`. The reply shows the tutor action, the textbook source and a possible misconception. Progress comes from `GET /learners/{id}/progress`.
4. Clicking a concept on the left fills in "I am stuck on ...". The concept list has no answers; the backend never sends them.

All learners who share the one account share one progress record.

## Layout

```
frontend/
├── index.html
├── vite.config.js        # dev server and /api proxy
├── src/
│   ├── main.jsx
│   ├── App.jsx           # sign-in state, session, messages
│   ├── api.js            # fetch helper and token handling
│   ├── styles.css        # copied from the mock-app
│   └── components/       # Login, Header, ConceptMap, Chat, SidePanel, Icon
└── .env.example
```

## Production

Serve `dist/` from a web server that forwards `/api/` to the backend (and strips the prefix), over HTTPS. Set the backend's `CORS_ORIGINS` only if the frontend is on a different origin.

# Admin dashboard (React)

The platform's frontend: React 19, TypeScript, Vite, Tailwind CSS v4, and
Recharts. It talks to the FastAPI backend over plain HTTP through
`src/lib/api.ts`; there is no server-side rendering and no separate backend of
its own. Anything the dashboard can do, a third party could do by calling the
same REST API directly.

## Why React and not Streamlit

The task allows either. Streamlit is faster to stand up, but a Python page
running server-side loses the separation an actual enterprise product has
between its API and its UI. Building this as a real single-page app means the
dashboard exercises the platform exactly the way an external integrator would:
through `POST /api/v1/auth/login`, a bearer token, and JSON responses. It also
gives every page its own URL, and lets role-based UI (hiding the Users and
Audit Log pages from non-admins) sit next to role-based API enforcement
without one covering for gaps in the other.

## Run it

```bash
npm install
npm run dev
```

Defaults to `http://127.0.0.1:8010` for the API; override with
`VITE_API_BASE_URL` in `.env.development` or `.env.production`. The FastAPI
server must already be running (`uvicorn app.main:app --port 8010` from the
project root) — the login screen shows a warning banner if it isn't reachable.

## Structure

```
src/
  lib/
    api.ts          one function per endpoint, typed request/response
    types.ts         shapes mirroring the backend's Pydantic schemas
    useApi.ts        small hook: loading/error/data/reload around a fetch
  context/
    AuthContext.tsx   token storage, /auth/me, login/logout
  components/
    Layout.tsx        sidebar navigation, hides admin-only links by role
    ProtectedRoute.tsx  RequireAuth / RequireRole route guards
    ui.tsx             Badge, Card, Button, inputs, Spinner, etc.
  pages/
    Login, Overview, Documents, Tickets, Approvals, Assistant,
    Reports, Workflows, Integrations, Users, AuditLog
```

Every page follows the same shape: `useApi()` for the GET that populates it,
plain `async` handlers for actions, and the platform's own `ApiError` for
error messages, so a 403 from a role check reads as the API's own message
rather than a generic "request failed."

## Verified, not just built

Every page was exercised in a live browser against the real running API
rather than assumed to work from the code: sign-in as admin renders live
platform counters that match the API's own numbers, the Documents page shows
the actual AI-extracted fields from an uploaded invoice, the AI Assistant
round-trips a real question and displays its sources, and switching to a
viewer account visibly removes the Users and Audit Log links and every write
button — confirming the same role rules enforced server-side are also
reflected in what the UI shows.

## Build

```bash
npm run build
```

Outputs static files to `dist/`, servable by any static host or folded into
the Docker image alongside the API.

# Enterprise AI Automation Platform

NexGen Software House, AI Automation Internship, Hard Task (mandatory final
project).

A centralised platform connecting business systems, automating repetitive
work, and applying AI to documents, tickets, and reporting: multi-user
authentication with role-based access, an AI assistant grounded in the
platform's own data, document intelligence for invoices and contracts,
ticket automation with AI triage, approval workflows, integration adapters
for CRM/ERP/Google Workspace/Microsoft 365, REST APIs, AI-generated reports,
and an admin dashboard.

## Status

Backend running and exercised end to end with real HTTP requests, not
assumed to work from the code. The React dashboard is running against the
live API with every page checked in a browser. Four defects were found and
fixed this way; see [docs/technical-documentation.md](docs/technical-documentation.md)
for the list.

## Architecture

```
                        ┌────────────────────┐
   Browser  ───────────▶│  React dashboard    │
                        │  (Vite, TypeScript) │
                        └──────────┬──────────┘
                                   │  REST + JWT
                                   ▼
┌───────────────┐        ┌────────────────────┐        ┌─────────────┐
│  n8n workflows │──────▶│  FastAPI backend    │◀──────│ Third-party  │
│  (email→ticket)│  REST  │  41 endpoints       │  REST  │  API clients │
└───────────────┘        └──────────┬──────────┘        └─────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                     ▼
       ┌─────────────┐     ┌──────────────┐      ┌───────────────┐
       │  PostgreSQL  │     │  AI service   │      │  Integration   │
       │  / SQLite    │     │  (OpenAI /    │      │  adapters      │
       │              │     │  Gemini /     │      │  CRM · ERP ·   │
       │              │     │  local        │      │  Workspace ·   │
       │              │     │  fallback)    │      │  M365          │
       └─────────────┘     └──────────────┘      └───────────────┘
```

## Requirements coverage

| Scope item | Implementation |
|---|---|
| Multi-user platform, role-based auth | JWT access + refresh tokens, 4 hierarchical roles (viewer/analyst/manager/admin), one `require_role` dependency gates every route |
| AI Assistant for business queries | Retrieves matching documents and tickets, answers only from that context, reports "not on record" rather than inventing an answer |
| Email management + ticket creation | `/tickets/inbound-email`, AI-triaged priority and category; n8n workflow watches Gmail and posts here |
| Extract/analyse PDFs, invoices, contracts | PDF and DOCX extraction, type classification, structured field extraction (reference, amount, currency, dates, risk flags) |
| CRM, ERP, Google Workspace, Microsoft 365 | 4 adapters behind one interface, sandbox-stateful until real credentials are supplied |
| REST APIs for third parties | 41 endpoints, full OpenAPI schema at `/docs` |
| AI-powered reports and insights | Metrics collection + AI narrative, falls back to a deterministic narrative with no model configured |
| Approval workflows | Amount-based routing (admin required above PKR 500,000), self-approval blocked, double-decision blocked |
| Admin dashboard with analytics | React SPA: live stats, 14-day activity chart, full CRUD across every domain, audit log |
| Deployment | See [docs/technical-documentation.md](docs/technical-documentation.md) for the deployment note |

## Run it locally

### Backend
```bash
python -m venv .venv
./.venv/Scripts/pip install -r requirements.txt      # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS/Linux
cp .env.example .env       # fill in what you have; every AI/integration key is optional
uvicorn app.main:app --port 8010
```
Seeds a demo tenant automatically on first start: 4 users, 3 documents, 5
tickets, 4 approvals, workflow run history, and all 4 integrations in
sandbox mode. Credentials are in
[docs/technical-documentation.md](docs/technical-documentation.md).

### Dashboard
```bash
cd dashboard
npm install
npm run dev
```
Open `http://localhost:5173`. See [dashboard/README.md](dashboard/README.md).

### API docs
`http://localhost:8010/docs` — interactive Swagger UI. Use **Authorize** with
a token from `POST /api/v1/auth/login`.

## Project layout

```
app/
  api/            11 route modules, one per domain
  core/           security (JWT, bcrypt), RBAC dependency, audit helper
  integrations/   adapter base class + CRM/ERP/Workspace/M365 adapters
  models/         8 SQLAlchemy tables
  services/       AI service, document analysis, ticket triage, assistant, reports
  config.py       env-driven settings
  database.py     engine, session, init_db
  main.py         FastAPI app, middleware, error handling
  schemas.py      Pydantic request/response models
  seed.py         demo tenant, seeded automatically if the database is empty
dashboard/        React SPA (see its own README)
workflows/        n8n workflow exports
docs/             technical documentation, deployment guide
```

## Two implementations, one reason

Like the Medium task, there's a design decision worth being explicit about:
every AI feature (document analysis, ticket triage, the assistant, report
narratives) degrades to a deterministic local implementation with no API key
configured. That is why the whole platform, including its demo data, works
immediately after cloning the repo. Set `OPENAI_API_KEY` or `GEMINI_API_KEY`
in `.env` and the same endpoints produce model-generated output instead,
with no code change.

## Technologies

Python, FastAPI, SQLAlchemy, PostgreSQL (SQLite for local development), JWT,
bcrypt, OpenAI API / Google Gemini API, n8n, React, TypeScript, Vite,
Tailwind CSS, Recharts.

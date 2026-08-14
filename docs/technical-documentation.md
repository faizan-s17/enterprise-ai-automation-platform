# Technical documentation

Enterprise AI Automation Platform
NexGen Software House, AI Automation Internship, Hard Task (mandatory final project)

## 1. The problem

A technology company wants one platform connecting its business systems,
automating the repetitive work that currently happens by hand across email,
spreadsheets, and separate tools, and applying AI to the parts of that work
that benefit from it: reading documents, triaging incoming requests, and
summarising what happened over a period of time.

## 2. Architecture

```
                        Browser
                           |
                           v
                React dashboard (Vite, TypeScript, Tailwind)
                           |
                     REST + JWT bearer token
                           v
   n8n workflows  ---->  FastAPI backend (41 endpoints)  <----  third-party API clients
  (email -> ticket)             |
                    +-----------+-----------+
                    |           |           |
              PostgreSQL   AI service   Integration adapters
             (SQLite for   (OpenAI /    CRM . ERP . Google Workspace .
              local dev)    Gemini /     Microsoft 365
                             local
                             fallback)
```

Everything above the database is stateless. Any number of API instances could
sit behind a load balancer with no code change, since sessions are JWTs, not
server-side session state.

### Why two frontends were considered, and why one was built

The task allows Streamlit or React. An early pass used Streamlit, since it is
faster to stand up. It was rebuilt in React because a Python page rendered
server-side blurs the line between the platform's API and its UI in a way a
real product would not have. The React dashboard is a plain consumer of the
same REST API a third-party integrator would use: it authenticates with
`POST /auth/login`, holds a bearer token, and calls JSON endpoints. Nothing in
the dashboard has privileged access the API itself does not enforce.

### Why every AI feature has a local fallback

Document analysis, ticket triage, the assistant, and report narratives each
try OpenAI, then Gemini, then fall back to a deterministic local
implementation (regex extraction, keyword-scored rules, template narratives).
This is not a stub left behind — it is why the platform, including its demo
data, works immediately with no API key, and why the automated test suite
runs deterministically without making paid network calls or depending on a
model's non-deterministic output.

## 3. Requirements coverage

| Scope item | Implementation | Evidence |
|---|---|---|
| Multi-user platform, role-based auth | JWT access + refresh tokens, 4 hierarchical roles, one `require_role` dependency gates every route | §5, §6 |
| AI Assistant | Retrieves matching documents/tickets first, answers only from that context | §6 |
| Email management + ticket creation | `/tickets/inbound-email`, AI-triaged priority and category; n8n watches Gmail and posts here | §6, §7 |
| Extract/analyse PDFs, invoices, contracts | PDF/DOCX/text extraction, type classification, structured field extraction | §6 |
| CRM, ERP, Google Workspace, Microsoft 365 | 4 adapters behind one interface, sandbox-stateful until real credentials are supplied | §6 |
| n8n workflows | 1 workflow, live in production, verified end to end on a real email | §7 |
| REST APIs for third parties | 41 endpoints, full OpenAPI schema at `/docs` | §5 |
| AI-powered reports and insights | Metrics collection + narrative, deterministic fallback with no model configured | §6 |
| Approval workflows | Amount-based routing (admin required at/above PKR 500,000), self-approval blocked, double-decision blocked | §6 |
| Admin dashboard with analytics | React SPA: live stats, 14-day activity chart, full CRUD, audit log | §6 |
| Deploy on a cloud platform | Live on Railway, real PostgreSQL | §8 |

## 4. Deviation from the task sheet, stated plainly

The task sheet says "deploy using Docker on a cloud platform." This platform
is deployed to a cloud platform (Railway) without Docker, using Railway's
Nixpacks buildpack instead, by the project owner's explicit choice partway
through the build. The application itself does not depend on this decision
either way: `requirements.txt`, `Procfile`, and `runtime.txt` are exactly what
a Dockerfile would also need to install and run, so containerising it later is
a mechanical change, not a redesign.

## 5. Repository layout

```
app/
  api/            11 route modules: auth, users, documents, tickets,
                  approvals, assistant, reports, workflows, integrations, admin
  core/
    security.py   password hashing (bcrypt), JWT issuing/validation
    deps.py       get_current_user, require_role, audit helper
  integrations/
    base.py       adapter contract every integration implements
    adapters.py   CRM, ERP, Google Workspace, Microsoft 365
  models/         8 SQLAlchemy tables
  services/
    ai.py         provider routing + local fallback, shared by every AI feature
    documents.py  text extraction, classification, structured analysis
    tickets.py    reference generation, rule-based and AI triage
    assistant.py  retrieval + grounded answering
    reports.py    metric collection + narrative generation
  config.py       env-driven settings
  database.py     engine, session, init_db
  main.py         FastAPI app, middleware, error handling, production guard
  schemas.py      Pydantic request/response models
  seed.py         demo tenant, seeded automatically when the database is empty
dashboard/        React SPA (see dashboard/README.md)
tests/            pytest suite, 80 tests, isolated in-memory database
workflows/        n8n workflow, exported
docs/             this file, workflow diagram
```

## 6. How it was verified

Every capability below was exercised against a running server with real HTTP
requests, not assumed to work from reading the code. Bugs are reported here
because they were caught this way, not despite it.

### Authentication and RBAC
Logged in as all four seeded roles; confirmed the full permission matrix
(`viewer` blocked from every write, `admin`-only routes reject `manager`,
the hierarchy lets `admin` pass a `manager`-level gate). Confirmed a wrong
password and an unknown email return the identical message and status, so the
login endpoint cannot be used to enumerate accounts.

### Document intelligence
Uploaded the real test invoice (`Invoice-INV-2026-0847.pdf`). The platform
correctly extracted `INV-2026-0847`, `PKR`, and `824520.0`, and classified the
document as an invoice.

### Tickets and email automation
Sent a real, live email with subject `[TICKET] Payment system outage`. The
n8n Gmail Trigger fired in production mode (not a manual test run), called
the live Railway API, created ticket `TKT-2026-586585`, triaged it as
`urgent`/`technical` with reasoning `"Matched the keyword 'outage'"`, and sent
a real alert email back — confirmed by Gmail's own `SENT` label on the
resulting message.

### Approvals
Verified the PKR 500,000 threshold: a manager was correctly refused on a
request at that amount, an admin was allowed. Verified self-approval is
blocked and a decided request cannot be decided a second time.

### AI assistant
Verified retrieval finds a document by type alone ("show me contracts"
matching a contract with no literal word "contract" in its text), handles
plurals ("invoices" matching "Invoice"), and correctly reports
`grounded: false` with no sources for an unrelated question rather than
inventing an answer.

### React dashboard
Logged in through the actual browser UI as admin: the overview page's
counters matched the API's own numbers exactly. Uploaded a document and saw
its real AI-extracted fields render. Asked the AI assistant a question
through the chat UI and got a grounded answer with cited sources. Switched to
a viewer account and confirmed the Users and Audit Log sidebar links, and
every write button on every page, were not present — the same role rules
enforced server-side are also reflected in what the UI shows, checked
independently rather than assumed from the API tests alone.

### Automated tests
80 pytest tests across 9 files, run against an isolated in-memory SQLite
database (never the developer's own data), with AI calls forced onto the
local fallback so results are deterministic. See §9.

## 7. n8n workflow

**Enterprise Platform — Email to Ticket + Urgent Alert**

```
Gmail Trigger (subject:[TICKET])
      |
      v
Create Ticket via Platform API  --POST-->  /api/v1/tickets/inbound-email
      |
      v
Is Urgent (priority == "urgent")
      |
      +--true--> Alert Admin (Gmail send)
      +--false-> (no further action)
```

The HTTP Request node's URL and the alert recipient were placeholders during
development and are now pointed at the live Railway deployment and a real
inbox. The workflow was tested twice: first with pinned data to verify the
branching logic in isolation (both the urgent and non-urgent paths route
correctly), then for real, with a genuine email, confirmed via the n8n
execution log showing `mode: trigger` rather than `mode: manual`.

## 8. Deployment

Deployed to Railway without Docker; see [DEPLOYMENT.md](../DEPLOYMENT.md) for
the full walkthrough. Two things worth recording here because they were real
failures encountered while deploying, not anticipated in advance:

**Railway's Nixpacks build failed** with `No GitHub artifact attestations
found for python@3.11.9`, a gap in the `mise` tool's attestation verification
for that specific Python build, unrelated to this application. Fixed by
adding `mise.toml` with `python.github_attestations = false`; checksum
verification still runs, only the attestation check is skipped.

**A production safety guard was added** to `app/main.py`: the app refuses to
start with `ENVIRONMENT=production` if `SECRET_KEY` is still the default
value committed in `config.py`. That default is public in the GitHub repo, so
running production with it would let anyone forge a valid login token for any
user, including an admin. Verified this guard actually fires by calling the
app's lifespan directly with the default key and `ENVIRONMENT=production` set,
confirming it raises before the app would otherwise start.

## 9. Automated test suite

```bash
cd enterprise-ai-automation-platform
./.venv/Scripts/pip install -r requirements.txt
./.venv/Scripts/python -m pytest tests/ -v
```

| File | Covers |
|---|---|
| `test_auth.py` | Registration cannot self-elevate, login, no account enumeration, token refresh, refresh tokens rejected as access tokens |
| `test_rbac.py` | Role hierarchy across representative routes, self-role-change and self-deactivation blocked |
| `test_documents.py` | Upload, extraction, classification, structured field extraction, unsupported types, re-analysis, deletion |
| `test_tickets.py` | Manual and auto-triaged creation, inbound email, quoted-reply stripping, status transitions |
| `test_approvals.py` | Amount-based routing, self-approval blocked, double-decision blocked |
| `test_assistant.py` | Grounded vs ungrounded answers, plural matching, document-type matching |
| `test_reports.py` | Metric collection, narrative generation, markdown-free local fallback |
| `test_workflows.py` | Simulated runs with no n8n configured, the n8n callback route |
| `test_integrations.py` | Sandbox mode, stateful sandbox data, error shapes for unknown operations/integrations |
| `test_admin.py` | Stats, audit-log admin gating, that writes are actually audited with the correct actor |

Tests run against an isolated in-memory SQLite database created and dropped
per test, reached through a FastAPI dependency override — never the
developer's own `platform.db`, and the app's normal startup (which would seed
demo data) never runs during the test session. AI calls are forced onto the
local fallback via a monkeypatched setting, regardless of whatever key is in
the developer's own `.env`, so results are deterministic.

Writing this suite caught one more bug, in the tests themselves: two tests
originally used `@test.local` addresses through the `/auth/register`
endpoint, which `EmailStr` rejects as an RFC 2606 reserved domain — the exact
same defect class as the seed-data bug in §10. Fixed by using an
ordinary-looking non-reserved domain instead, and noted in the test file so
the reason is not lost.

## 10. Defects found during development, and how

None of the following were visible from reading the code. Each surfaced only
once real requests, real data, or a real deploy ran, which is the recurring
argument in this project for testing against live behaviour rather than
trusting that correct-looking code is correct.

| Symptom | Cause | Fix |
|---|---|---|
| `GET /users` returned 500 | `EmailStr` rejected the seeded `.local` addresses | Response model reads `email` as `str`, not re-validated on the way out; seed emails moved to a non-reserved domain |
| "payment system outage" ticket filed as billing | Category rule used first-match-wins; "payment" matched before "outage" | Category scoring now counts all keyword hits and picks the highest, not the first checked |
| Assistant found nothing for "What invoices do we have?" | Retrieval matched literal terms only; "invoices" did not match stored text "Invoice" | Added a lightweight singular/plural match |
| "Show me contracts" returned nothing | Retrieval searched text only, not document type | Added a document-type match alongside the text search |
| Reference extractor matched the word "INVOICE" | Regex matched any `INV` prefix, including the plain word | Regex now requires a separator-plus-alphanumeric or digits fused to the prefix |
| Currency missed on table-style invoices | Only the first matched amount's currency was read | Currency is now read from whichever amount in the document carries one |
| Dates showed an embedded newline | PDF extraction wraps lines mid-date | Whitespace collapsed before dates are deduplicated |
| AI summary quoted mid-sentence fragments | Extractive fallback did not penalise lowercase-starting lines | Lines starting lowercase are scored down, since they are usually a wrapped sentence's tail |
| `google-generativeai` deprecation warning on every import | The package is fully deprecated with no further updates | Replaced with `google-genai`, Google's maintained SDK; re-verified no warning and unchanged behaviour |
| Railway build failed on Python install | `mise`'s GitHub attestation check failed for that Python build | `mise.toml` disables attestation verification; checksums still verified |
| Two new tests failed on first run | Same `.local` reserved-domain issue as above, this time in test fixtures | Switched to a non-reserved test domain |

## 11. Limitations

**Document processing is synchronous.** Upload extracts and analyses in the
same request-response cycle. Fine for the sizes this platform expects; a
queue would be the right answer at real volume, and is a natural next step
rather than a current gap in behaviour.

**Integration adapters are sandbox by default.** Connecting real Salesforce,
SAP, Google Workspace, and Microsoft 365 tenants needs four paid enterprise
accounts. Each adapter is written against the same interface a live
connection would use, and reports its own mode (`live` vs `sandbox`) rather
than pretending to be connected, so nothing about a demo misrepresents itself.

**The `/tickets/inbound-email` and `/workflows/callback` routes are
unauthenticated**, deliberately, so an email automation or n8n can call them
without holding a platform user token. In a production deployment these
would sit behind a shared secret or network-level restriction; this repo does
not add one.

**Only one n8n workflow is built.** It demonstrates the pattern (event
trigger, call the platform API, branch on the result, notify) end to end and
was verified live; a second workflow (for example, a scheduled approval
reminder) would follow the same pattern but was not built for this
submission.

## 12. Technologies used

Python, FastAPI, SQLAlchemy, PostgreSQL (SQLite for local development), JWT,
bcrypt, OpenAI API, Google Gemini API (via `google-genai`), n8n, React,
TypeScript, Vite, Tailwind CSS, Recharts, pytest, Railway.

# Deploying to Railway (no Docker)

Railway builds this with [Nixpacks](https://nixpacks.com), which auto-detects
Python from `requirements.txt` and runs the command in `Procfile`. No
Dockerfile is involved — this is a different path from a container deploy,
and needs no Docker knowledge or Docker installed anywhere.

## What's already in the repo

| File | Purpose |
|---|---|
| `Procfile` | `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT` — Railway sets `$PORT` itself |
| `runtime.txt` | Pins the Python version Nixpacks builds with |
| `requirements.txt` | Everything Nixpacks needs to `pip install` |
| `.env.example` | Every environment variable the app reads, documented |

A safety check in `app/main.py` refuses to start with
`ENVIRONMENT=production` if `SECRET_KEY` is still the default value baked
into `config.py` — that default is public in this repo's source, so running
with it in production would let anyone forge a valid login token.

## Steps

1. **Push this repo to GitHub** if it isn't already there.

2. **New Railway project** → *Deploy from GitHub repo* → select the repo.
   If the repo root isn't `enterprise-ai-automation-platform/` itself (for
   example, it's a subfolder of a larger repo), set that as the project's
   **Root Directory** in Railway's settings so Nixpacks finds `Procfile` and
   `requirements.txt`.

3. **Add a PostgreSQL plugin** to the project (`+ New` → `Database` →
   `PostgreSQL`). Railway sets `DATABASE_URL` on the web service
   automatically — nothing to copy by hand.

4. **Set environment variables** on the web service:

   | Variable | Value |
   |---|---|
   | `ENVIRONMENT` | `production` |
   | `SECRET_KEY` | Output of `python -c "import secrets; print(secrets.token_hex(32))"` |
   | `CORS_ORIGINS` | `*` for the demo, or your dashboard's real origin |
   | `OPENAI_API_KEY` | Optional — omit to run on the local AI fallback |

   Everything else in `.env.example` is optional; the platform runs with
   defaults or sandbox behaviour for anything left unset.

5. **Deploy.** Railway builds and starts the service, then gives it a public
   URL like `https://your-app.up.railway.app`. Tables are created
   automatically on first start (`init_db()` in the app's lifespan), and the
   demo tenant seeds itself since the database starts empty. Confirm with:

   ```bash
   curl https://your-app.up.railway.app/health
   ```

## After deploying

- **n8n workflows**: replace the placeholder platform API URL in the
  `Create Ticket via Platform API` node (workflow `enterprise-email-to-ticket`)
  with the Railway URL, so n8n calls the real, live API instead of a mock.
- **Dashboard**: point `VITE_API_BASE_URL` at the Railway URL (in
  `dashboard/.env.production`, or set it in whatever host serves the built
  dashboard) so the deployed frontend talks to the deployed backend.
- **Demo credentials**: `admin@nexgenautomation.com` / `Admin@12345` (and the
  other seeded roles — see the main README) work immediately since the seed
  runs on first start against the empty Railway database.

## Rolling back to local-only

Nothing about the code requires Railway. Unset `DATABASE_URL` and the app
falls back to a local SQLite file; run `uvicorn app.main:app --port 8010`
exactly as in local development.

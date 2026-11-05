# Deployment

Phase 1 deploys as three processes plus managed data services: Next.js web, FastAPI API,
ARQ worker, Postgres (pgvector), Redis and S3-compatible storage. Docker Compose is the
reference topology; the same images work on Render, Railway, Fly.io, Google Cloud Run or
a VM.

## Docker Compose (reference)

```bash
cd placemate
cp .env.example .env       # replace JWT/storage secrets
docker compose up --build
```

Services: `postgres` (pgvector/pg16), `redis`, `minio`, `api`, `worker`, `web`.
Postgres and Redis use their built-in health probes; MinIO intentionally uses
`service_started` because its image does not reliably ship `curl`/`mc`. The API creates the
bucket on first use with retries, so a few seconds of MinIO startup is safe. The API
entrypoint waits for dependencies, runs
`alembic upgrade head`, seeds questions/demo data when `DEMO_MODE=true`, then serves on
:8000. Web is on :3000. MinIO console: :9001.

Set in `.env` (all placeholders in `.env.example`):

| Variable | Production guidance |
| --- | --- |
| `DATABASE_URL` | Managed Postgres with pgvector enabled |
| `REDIS_URL` | Managed Redis; use TLS (`rediss://`) if available |
| `JWT_SECRET` | 48+ random bytes, secret manager, rotated on compromise |
| `CORS_ORIGINS` | Exact web origin(s), comma-separated, HTTPS only |
| `FRONTEND_URL` / `API_PUBLIC_URL` | Public HTTPS URLs; drives OAuth callback and cookie `Secure` |
| `AUTH_GOOGLE_CLIENT_ID/SECRET` | Google Cloud OAuth client; callback `{API_PUBLIC_URL}/api/v1/auth/google/callback` |
| `LLM_PROVIDER` | `vertex`, `gemini` or `openai`; keep `mock` only for demos |
| `LLM_MODEL_CHEAP` / `LLM_MODEL_SCORING` | Cost/quality choice; scoring gets the stronger model |
| `STORAGE_*` | R2/S3/Supabase bucket; private ACL; scoped key |
| `PER_USER_MONTHLY_BUDGET` | USD cap per student per month |
| `DEMO_MODE` | **false** in production |
| `SENTRY_DSN`, `POSTHOG_KEY` | Optional; leave blank to disable |

**Never commit `.env` or service-account JSON.** Use the platform's secret store.

## Managed deployment sketch

### Web (Vercel or similar)
- Root directory `frontend`.
- Build `npm run build`; output Next default.
- Env: `NEXT_PUBLIC_API_URL=https://api.example.com/api/v1`,
  `NEXT_PUBLIC_WS_URL=wss://api.example.com/api/v1`, `NEXT_PUBLIC_DEMO_MODE=false`.
- PWA assets (`public/manifest.webmanifest`, `sw.js`, icons, `offline.html`) ship with the
  build. Serve over HTTPS so the service worker registers.

### API (Render/Railway/Cloud Run)
- Build `backend/Dockerfile`; start `./start.sh` (runs migrations).
- Health check `/healthz`; readiness `/readyz` checks the DB.
- Min instances 1 if you rely on in-process slowapi memory storage; otherwise set
  `RATE_LIMIT_STORAGE_URI=redis://...` so limits are shared.
- WebSockets must be enabled on the proxy/load balancer; idle timeout > 10 minutes.
- Run exactly one migration job per release; avoid concurrent `upgrade head` races.
- Set `--proxy-headers` (already in `start.sh`) behind a trusted proxy.

### Worker
- Same image, command `arq app.workers.worker.WorkerSettings`.
- Needs `DATABASE_URL` and `REDIS_URL` only. One worker is enough for Phase 1; scale by
  adding replicas (jobs are idempotent).

### Data
- **Postgres:** enable `vector`; create the HNSW index via the initial migration. Use
  connection pooling (PgBouncer or provider pooler) and set `pool_pre_ping`.
- **Redis:** used for rate limits and ARQ. Use a separate logical DB from cache if added.
- **Storage:** private bucket; CORS not required because downloads are proxied by the API.
  Set lifecycle rules aligned with the 12-month retention.

## Migrations and seeds

```bash
# one-off release job
cd backend && alembic upgrade head
# first deploy only / demo environments
python ../scripts/seed_questions.py
python ../scripts/seed_demo_data.py   # never with DEMO_MODE=false in production
```

`seed_demo_data.py` is idempotent (NOVA college, 14 students, officer/admin, analyses and
interviews). Verify `DEMO_MODE=false` and that demo users are absent before go-live.

## Google OAuth

1. Create a Web application OAuth client.
2. Authorised redirect URI: `https://api.example.com/api/v1/auth/google/callback`.
3. Set client ID/secret in the API environment.
4. Set `FRONTEND_URL` to the web origin for the post-login redirect.
5. Test both a new account (college code required) and an existing one.

Password login remains available; OAuth is additive in Phase 1.

## LLM providers

- **Vertex AI:** set `LLM_PROVIDER=vertex`, `GOOGLE_CLOUD_PROJECT`,
  `GOOGLE_CLOUD_LOCATION`, and mount the service account JSON at
  `GOOGLE_APPLICATION_CREDENTIALS` (secret file, never in the image/repo).
- **Gemini API:** `LLM_PROVIDER=gemini`, `LLM_API_KEY`.
- **OpenAI-compatible:** `LLM_PROVIDER=openai`, `LLM_API_KEY`, `LLM_BASE_URL`.
- **Mock:** `LLM_PROVIDER=mock` — no keys, deterministic, used in CI and demos.

Smoke-test one resume analysis and one full interview after switching providers. Check
`usage_events` for nonzero token counts and that the monthly budget rejects at the cap.

## Observability

- **Sentry:** set `SENTRY_DSN`; the API initialises it when present. Do not send resume
  text/transcripts as breadcrumbs; current logging redacts PII.
- **PostHog:** `POSTHOG_KEY` is exposed only as a public project key; analytics is loaded
  client-side and should honour consent. Phase 1 ships the env plumbing, not event wiring.
- **Logs:** structured JSON; request IDs, route, status and latency. Resume/transcript
  bodies are never logged.
- **Dashboards/alerts:** API 5xx rate, p95 latency, LLM error rate, budget rejections,
  Postgres connections, Redis memory, worker failures.

## CI

`.github/workflows/ci.yml` runs:
- **backend:** ruff check/format, mypy, pytest (SQLite + mock LLM + local storage).
- **frontend:** `npm ci`, lint, prettier check, typecheck, Vitest, `next build`.
- **e2e:** installs Chromium, migrates/seeds SQLite, starts API + web, runs Playwright.

No job needs paid credentials. Docker build/publish is intentionally left to the deploy
platform; add a registry step when images are hosted.

## Scaling notes (Phase 2)

- Move resume parsing and scoring to ARQ jobs with a status endpoint and polling/websocket;
  the current API contract can stay additive.
- Put slowapi on Redis and add per-college quotas, not just per-user budgets.
- Use a read replica for officer analytics; cache aggregates for 5–15 minutes.
- For voice, stream STT over the same WebSocket, store no raw audio, and cap session time.
- Add OpenTelemetry traces around LLM calls before adding more providers.

## Rollback

1. Deploy the previous image tag (migrations are additive; avoid destructive changes).
2. If a migration must be reversed, use a reviewed `alembic downgrade` only after a backup;
   never downgrade production data blindly.
3. Re-run `/healthz`, `/readyz`, one login and one dashboard request.
4. Keep object storage versioned so resume objects survive a bad deploy.

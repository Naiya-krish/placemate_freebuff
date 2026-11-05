# Contributing to PlaceMate

Thanks for helping. This project is built in vertical slices; keep changes small enough
to review in one sitting and include the checks that prove them.

## Setup

```bash
cd placemate
python3.12 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd frontend && npm ci && npx playwright install chromium
```

Copy `.env.example` to `.env` for Docker, or use the SQLite/local-storage overrides in
[README.md](README.md). Never commit `.env` or real credentials.

## Branching and commits

- Branch from `main`: `feat/interview-hints`, `fix/tenant-leak`, `docs/deployment`.
- Conventional commit subjects: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`,
  `chore:`. One logical change per commit.
- Reference the relevant phase item in the body, e.g. `Phase 1 / Slice D`.
- Do not force-push shared branches. Rebase your own branch before opening a PR.

## Code standards

### Backend
- Python 3.12, full type hints, Pydantic v2, SQLAlchemy 2 style.
- `ruff check .` and `ruff format --check .` must pass; `mypy app` must pass.
- Do not add `from __future__ import annotations` to route modules that use slowapi
  decorators (FastAPI resolves annotations at runtime and breaks on ForwardRef).
- All tenant data access goes through `TenantRepository` or includes an explicit
  `college_id` filter. Add a cross-tenant test when touching a read path.
- Prompts belong in `app/prompts/v<version>/`, never in a route handler. Bump the prompt
  version when behaviour changes and update [docs/prompts.md](docs/prompts.md).
- Any new LLM call must go through `LLMClient` so budget checks and usage logging apply.
- Never log resume text, transcripts, tokens or passwords.

### Frontend
- TypeScript strict, App Router, server components by default; add `"use client"` only
  where state, effects or browser APIs are needed.
- Tailwind tokens from `globals.css`; no hard-coded colours that bypass the theme.
- Use the existing primitives in `components/ui`; keep focus states and labels.
- Motion must respect `prefers-reduced-motion`. Charts need a text summary.
- `npm run lint`, `npm run typecheck`, `npm run format:check` and `npm test -- --run`
  must pass before a PR.

### Tests
- New backend behaviour needs a pytest case. Security-relevant changes need a negative
  case (cross-tenant, bad input, prompt injection).
- UI logic lives in hooks/lib where possible; add a Vitest test for pure logic.
- Update the Playwright flow when it changes the student's path. It must pass against the
  seeded demo data and the mock provider.
- Tests must not call a paid provider, the network, or require Docker.

## Definition of done for a change

1. Behaviour is implemented and documented.
2. `make lint` and `make test` pass locally (or the affected subset, stated in the PR).
3. New env variables are added to `.env.example` and `docs/deployment.md`.
4. `CHANGELOG.md` has an entry under `Unreleased` for user-visible changes.
5. No secrets, generated databases, `.next`, `node_modules` or upload artifacts staged.

## Pull request checklist

- [ ] Summary and motivation
- [ ] Screenshots for UI changes (light and dark; mobile width)
- [ ] Tests added/updated and commands run
- [ ] Migration included for schema changes (`alembic revision --autogenerate`)
- [ ] Tenant isolation and consent implications considered
- [ ] Docs/ADR updated for ambiguous decisions

## Adding a database column

1. Update the SQLAlchemy model with a server-safe default or nullable column.
2. `cd backend && PYTHONPATH=. ../.venv/bin/alembic revision --autogenerate -m "add ..."`
3. Review the migration (especially pgvector/JSONB variants for SQLite).
4. Run `alembic upgrade head` on a clean database and on a populated copy.
5. Update [docs/database.md](docs/database.md).

## Adding a rubric version

Rubrics are immutable once used. Create a new version through `/admin/rubrics` (or a
migration/seed for a platform-wide default); never edit criteria in place. Scores store
`rubric_version`, so historical feedback stays interpretable.

## Reporting security issues

Do not use public issues. See [SECURITY.md](SECURITY.md#reporting-a-vulnerability).

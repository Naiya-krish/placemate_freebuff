# Changelog

All notable changes are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
semantic versioning once it leaves Phase 1.

## [Unreleased]

### Planned (Phase 2)
- Voice interviews with STT/TTS, raw-audio deletion after transcription.
- Regional-language interview mode.
- Branch tracks: ECE dual-track, AI/DS deep-dive, core-to-IT bridge resume.
- Coding and aptitude assessments, group discussion.

## [0.1.0] — 2026-11-03

### Added
- Phase 1 MVP: multi-tenant colleges with student, officer and admin roles.
- Email/password auth with scrypt, short-lived JWT access tokens, rotating refresh
  cookies, Google OAuth scaffold, and demo login gated by `DEMO_MODE`.
- Tenant-isolated data layer (`TenantRepository`) with cross-tenant 404 tests.
- Resume upload for PDF/DOCX (5 MB, MIME + magic-byte validation), text extraction,
  OCR fallback, structured parsing, parse warnings and `needs_review` state.
- Resume score with job-description tailoring, side-by-side accept/reject diffs,
  missing-evidence guidance, and an evidence guard that rejects invented experience.
- Prompt-injection detection and fenced untrusted content for resumes, JDs and
  transcripts.
- Three-round text interview (project deep-dive, technical, HR) over WebSocket with
  resume-grounded questions, pgvector retrieval, adaptive follow-ups, hints and XP.
- Visible versioned rubric; three-sample low-temperature scoring with Pydantic
  validation, medians, server-recomputed weighted total, variance review flag, and
  stored rubric/prompt/model versions.
- Split-view feedback with transcript, per-criterion notes and one-line improvements.
- Student bento dashboard: readiness ring, skill radar, streak/XP/level, badges,
  confetti, next-best-action, history and AI budget.
- Officer dashboard: KPIs, department heatmap, readiness funnel, weakest skills,
  cohort trend, batch comparison, consent-gated student rows and PDF export.
- Admin console: colleges, question bank CRUD, rubric versions/activation and usage.
- Per-call token/cost ledger, monthly summary and per-user budget enforcement.
- PWA manifest, service worker, offline page, icons and installable mobile layout.
- Dark-first design with light toggle, violet→cyan accent, command palette, English and
  Hindi UI, reduced-motion and keyboard support.
- Docker Compose with Postgres 16 + pgvector, Redis, MinIO, API, ARQ worker and web;
  Alembic migration; idempotent question and demo seeds.
- GitHub Actions CI for backend lint/types/tests, frontend lint/types/tests/build and
  Playwright E2E.
- 29 backend tests, Vitest unit tests and a full Playwright interview flow.

### Security
- Rate limits on auth, upload, analysis and interview; strict CORS; CSRF origin checks;
  security headers; parameterised queries; PII-redacted structured logs; self-service
  account deletion; DPDP-aligned retention documented in `SECURITY.md`.

### Known limitations
- Text interviews only; no audio is collected.
- Resume parsing and scoring run inline rather than in the ARQ queue.
- Google OAuth needs real credentials and a public callback to exercise.

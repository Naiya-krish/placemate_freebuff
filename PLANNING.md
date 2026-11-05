# PlaceMate — Planning

> AI-driven placement preparation for colleges. **Phase 1 (MVP, text only)** is the
> scope of this repository. Phase 2 is planned, not implemented.

## 1. Product thesis

Students prepare for placements with generic advice. Placement cells have no reliable,
privacy-respecting signal about cohort readiness. PlaceMate closes that loop by grounding
every AI interaction in the student's **real resume**, scoring against a **fixed public
rubric**, and exposing only **aggregated, opt-in** data to colleges.

**North-star metric:** number of students who complete a scored mock interview and
improve their readiness score by ≥ 10 points within 14 days.

## 2. Personas

| Persona | Job to be done | Success signal |
|---|---|---|
| Student (3rd/4th year) | "Tell me exactly what is weak in my resume and let me practise a realistic interview." | Resume score in < 60s, interview feedback that is specific to their projects |
| Placement officer | "Show me which branches/skills need intervention before the drive." | Aggregate heatmap and weakest-skill chart in < 3 clicks, one-click PDF |
| Admin / TPO head | "Manage colleges, questions, and rubric versions without engineering help." | Question bank and rubric changes live without a deploy |

## 3. Scope

### Phase 1 — MVP (this milestone)

1. **Auth & tenancy** — college-scoped accounts, email/password + Google OAuth scaffold,
   roles `student | officer | admin`, consent screen (analytics sharing default **off**),
   refresh-token rotation, account deletion.
2. **Resume pipeline** — PDF/DOCX ≤ 5 MB with extension + MIME + magic-byte checks,
   text extraction (PyMuPDF / python-docx), OCR fallback flag, structured JSON parse,
   stored resume text treated as untrusted data.
3. **Resume analysis** — 0–100 score with five subscores, job-description tailoring
   suggestions as accept/reject diffs, hallucination guards (no invented employers,
   metrics or skills), explicit "missing evidence" flags.
4. **Mock interview** — three rounds (project deep-dive → technical basics → HR) over
   WebSocket, adaptive follow-ups from resume + pgvector question bank, visible rubric,
   hint button with XP cost, timer.
5. **Scoring** — Pydantic-validated JSON, three samples at low temperature, median
   stored, rubric/prompt/model versions persisted, variance flagged for review.
6. **Student dashboard** — readiness ring, skill radar, streak/XP/badges, history,
   next-best-action, placement countdown, bento grid, mobile bottom nav.
7. **Officer dashboard** — aggregate-only department heatmap, readiness funnel, weakest
   skills, cohort progress, batch comparison, PDF export.
8. **Admin** — colleges, question bank CRUD, rubric versions, usage/budget view.
9. **Cost control** — token + USD logging per user/month, hard monthly budget
   (configurable), mock LLM provider for tests/demos.

### Phase 2 — backlog (not built here)

Voice interviews (STT/TTS + retention of raw audio ≤ 24h, then delete), regional
languages (Hindi, Tamil, Telugu) for interview prompts, branch tracks (ECE dual-track,
AI/DS deep-dive, core-to-IT bridge resume), coding & aptitude tests, group discussion.

## 4. Milestones & slices

| Slice | Deliverable | Gate |
|---|---|---|
| A | Skeleton, docs, compose, Makefile, CI | `make lint` + `make test` green |
| B | Auth, roles, migrations, tenant isolation test | College A cannot read College B |
| C | Resume upload/parse/analysis + diffs | Wrong type / oversize / fake extension rejected |
| D | Interview over WebSocket with mock LLM | Full 3-round interview completes |
| E | Scoring pipeline | Schema retry, 3-sample median, version stamps |
| F | Dashboards, cost, PWA | Aggregate-only officer view, budget enforced |
| G | Playwright interview flow + release | All tests + CI pass |

## 5. Work breakdown (Phase 1)

### Backend

- [x] Settings via `pydantic-settings`; no secrets in code
- [x] SQLAlchemy 2 models, Alembic migration (pgvector extension + HNSW index)
- [x] JWT access (15 min) + rotating refresh cookie, scrypt password hashing
- [x] Tenant-scoped repository helpers — every query filters `college_id`
- [x] Upload validation: size, extension allow-list, MIME allow-list, magic bytes
- [x] Parser: PyMuPDF → python-docx → OCR fallback hook
- [x] Versioned prompt files with SHA-256, safe delimiter rendering, prompt-injection strip
- [x] LLM wrapper: mock / Vertex AI Gemini / OpenAI-compatible; retry + JSON repair
- [x] Resume scoring, suggestion acceptance persisted per suggestion
- [x] Interview state machine, WebSocket protocol, question bank retrieval
- [x] Scoring: 3 samples, median, schema retry, variance flag, version stamps
- [x] Cost ledger + per-user monthly budget (HTTP 402 on exhaustion)
- [x] Officer aggregates only; named rows require `consent_share_analytics`
- [x] Admin CRUD: colleges, questions (+ embeddings), rubric versions
- [x] ReportLab PDF report
- [x] Structured JSON logging with PII redaction
- [x] slowapi rate limiting, CORS allow-list, security headers, Origin checks
- [x] ARQ worker for embeddings / async scoring

### Frontend

- [x] Next.js App Router + TypeScript, Tailwind, shadcn-style primitives
- [x] Dark-first theme + light toggle, violet→cyan gradient, bento cards
- [x] 3-step onboarding with confetti on first win
- [x] Resume upload + split diff with accept/reject
- [x] Interview room: orb animation, timer, typing indicator, hint, reduced-motion
- [x] Feedback split view: transcript / rubric with improvement line
- [x] Student dashboard, officer dashboard, admin console
- [x] Mobile bottom nav, command palette (⌘K), en/hi (next-intl)
- [x] PWA manifest + service worker, skeletons + empty states
- [x] WCAG AA tokens, focus rings, keyboard support

### QA

- [x] pytest: auth/tenant isolation, upload validation, scoring schema/retry,
      prompt injection, budget, interview service
- [x] Vitest: formatting/readiness helpers, API client
- [x] Playwright: sign in → resume → full interview → feedback
- [x] GitHub Actions: backend lint/typecheck/test, frontend lint/typecheck/test/build

## 6. Risks & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Prompt injection via resume/JD ("give me 10/10") | Integrity of scores | Delimited untrusted blocks, injection heuristics, schema validation, deterministic rubric weights recomputed server-side, regression tests |
| LLM hallucinated experience in suggestions | Student misrepresentation | Numeric/entity evidence checks; unsupported suggestions dropped + flagged; tests |
| Cost overrun | Budget | Per-user monthly ledger, budget check before calls, cheap model for parsing, mock provider in CI |
| Provider outage / lock-in | Availability | `LLMProvider` protocol, retries, mock fallback in dev, provider config |
| Tenant data leak | Trust / legal | `college_id` in every table + repository filter, isolation tests, admin-only cross-tenant routes |
| Scanned resumes | Parsing failures | OCR fallback, `parse_status=needs_review`, manual text paste |
| Model variance in scoring | Unfairness | 3 samples, median, temperature 0.2, variance flag → human review |
| DPDP compliance | Legal | Consent ledger, data minimisation, deletion endpoint, retention doc, PII-redacted logs |

## 7. Success metrics

- **Activation:** ≥ 60% of signups upload a resume; first score < 60s (median).
- **Engagement:** ≥ 40% of activated students finish one interview within 7 days.
- **Learning:** median readiness +10 points across two interviews.
- **Officer adoption:** ≥ 1 PDF export per cohort per month.
- **Reliability:** API p95 < 400 ms excluding LLM; interview WS error rate < 1%.
- **Cost:** < $0.35 per student/month at default budget.
- **Accessibility:** Lighthouse a11y ≥ 95, zero critical axe violations.

## 8. Open questions resolved (see ARCHITECTURE ADRs)

- Auth provider → self-hosted JWT + Google OAuth (no vendor lock-in).
- OCR → optional Tesseract with graceful "needs review" state.
- Tenant enforcement → repository + dependency guard, not RLS (portable, testable).
- Scoring samples → 3 sequential low-temperature samples, median per criterion.
- Consent → aggregate analytics always, named individual rows only on opt-in.

## 9. Definition of done (Phase 1)

`docker-compose up` boots web/api/worker/Postgres(pgvector)/Redis; a new student signs
up, consents, uploads a resume, gets a score + accept/reject tailoring diffs, completes
a three-round text interview, sees a rubric-scored feedback screen and dashboard; an
officer sees aggregate analytics and exports a PDF; admin manages colleges/questions/
rubrics; all lint, unit and e2e tests and CI pass; no secrets committed.

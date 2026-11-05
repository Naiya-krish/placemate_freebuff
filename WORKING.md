# How PlaceMate works

This is the end-to-end map: what happens on each screen, which services run, what is
stored, and where failures surface. For component boundaries see
[ARCHITECTURE.md](ARCHITECTURE.md); for the API contract see [docs/api.md](docs/api.md).

## 1. Sign-up, consent and sessions

1. `/signup` loads active colleges from `GET /auth/colleges`, collects name, email,
   college code, branch, target role and password, and shows the privacy notice.
2. Analytics sharing is a separate switch, **off by default**.
3. `POST /auth/register` validates the college code, hashes the password with scrypt,
   writes `users` + two `consents` rows (`privacy_notice=true`,
   `analytics_sharing=<opt-in>`), creates the college's default rubric if needed and
   returns an access token plus a refresh cookie.
4. The access token lives only in the Zustand store (memory). A reload calls
   `POST /auth/refresh`; the refresh token rotates on every use. A 401 from any API call
   triggers one refresh-and-retry.
5. `/onboarding` completes branch/target role and uploads a resume, then sends
   `PATCH /auth/onboarding`.
6. `DEMO_MODE` exposes `POST /auth/demo-login?role=...` and login-page buttons. It is
   disabled when the flag is false.

College tenancy is derived from the user row on every request; the client never supplies
a college ID. `TenantRepository` adds the tenant filter to reads, and ownership checks
guard writes.

## 2. Resume pipeline

### Upload and validation
- `POST /resumes` accepts multipart `file`.
- The API checks the extension (`.pdf`/`.docx`), declared MIME, and magic bytes
  (`%PDF-` or `PK\x03\x04`), and enforces `MAX_UPLOAD_MB` while reading the stream.
- The file is stored under a random key in S3 or the local backend; the DB row stores
  filename, MIME, size, storage key and parse status.
- PyMuPDF extracts text; DOCX uses `python-docx`. If a PDF yields too little text,
  Tesseract OCR runs page-by-page and `used_ocr=true` is stored. Low-quality output marks
  the resume `needs_review` and keeps a warning list.

### Parsing to structured JSON
- The cheap LLM tier receives a fenced, length-capped version of the raw text and a JSON
  schema (`ParsedResume`: profile, links, skills, projects, experience, education).
- Output is validated by Pydantic. Invalid JSON is retried; if every retry fails, a
  deterministic fallback parser fills what it can and sets `needs_review`.
- `parsed_data` and `raw_text` are stored on the resume row; nothing is invented.

### Score and tailoring
- `POST /resumes/{id}/analyze` takes `job_description` and `target_role`.
- The analysis prompt includes the parsed resume (fenced), the JD (fenced as untrusted)
  and a fixed scoring rubric for resume quality (impact, clarity, evidence, relevance,
  structure).
- The model returns `score`, five subscores, `suggestions[]` and `missing_evidence[]`.
- **Evidence guard:** every suggestion must quote an `original` span that exists in the
  source resume and may not introduce new numbers, tools or employers. Unsupported
  suggestions are dropped; the reason is surfaced in `missing_evidence` instead.
- Injection patterns ("ignore previous instructions", "give me 10/10", role markers) are
  detected and stored in `injection_flags`, shown as a warning in the UI. They do not
  influence the score.
- Suggestions are stored as one `resume_analyses` row with a JSON array. The student
  accepts/rejects each via
  `PATCH /analyses/{id}/suggestions/{suggestion_id}`; decisions are audit-logged in the
  same JSON. The resume file itself is never modified — the student applies edits.

## 3. Interview lifecycle

### Before the room
- The student opens `/dashboard/interviews`; the active rubric is fetched from
  `GET /rubrics/active` and rendered with weights **before** starting.
- `POST /interviews` stores the rubric version, prompt version, role, resume reference and
  the initial round (`project`). Starting a second active interview is allowed; the room
  is per interview ID.

### WebSocket protocol
`GET /interviews/{id}/ws?token=<access token>` (upgrade) authenticates, checks ownership,
loads turns, sends:

```json
{"type":"session","role":"swe","rubric":{...},"xp":120,...}
```

If turns exist the last interviewer question is replayed (`"resumed": true`); otherwise a
typing indicator is sent while the first question is generated. Client messages:

| Client | Server responses |
| --- | --- |
| `{"type":"answer","content":"..."}` | `typing:true` → `typing:false` → optional `round_complete`, then `question` |
| `{"type":"hint"}` | `hint` with text, `xp_penalty: 5`, new XP |
| `{"type":"finish"}` | `typing:true` → `typing:false` → `scored` with overall/criteria/feedback, then close |
| `{"type":"ping"}` | `pong` |

### Question selection
1. Round plan: project 3 questions, technical 3, HR 2.
2. Project questions are generated from the resume (project names, tech, bullets) so the
   student is asked about their own work. Technical/HR questions retrieve top-k question
   bank rows by role/topic using pgvector cosine distance (`<=>`); SQLite tests compute
   cosine in Python.
3. After a project answer, the model may emit one follow-up when the answer is shallow or
   mentions an unexamined claim. Follow-ups are capped per round.
4. Every candidate answer is stored as an `interview_turns` row; interviewer questions
   too. The transcript is the source of truth for resume/rejoin.

### Scoring pipeline
1. `finish_interview` refuses to score with zero answers.
2. The scoring prompt receives the rubric block, resume context (fenced) and transcript
   (fenced, 18k chars). It returns per-criterion `score` (0–10), `note` and one-line
   `improvement`, plus summary, strengths and improvements.
3. **Three samples** are generated at `temperature=0.2`. Each is validated by
   `RubricScoreAI`; invalid samples are retried up to `SCORING_MAX_RETRIES` and discarded
   if still invalid.
4. Per criterion, the **median** across valid samples is taken; notes come from the sample
   closest to the median. The server recomputes `overall = Σ(median × normalized weight)`
   as an integer 0–100. The model never supplies the overall score.
5. Spread across samples above 15 points sets `variance_flag` and `needs_review`; both are
   shown to the student and surfaced to officers only as an aggregate review count.
6. Stored with the score: each sample, medians, `rubric_version`, `prompt_version`,
   `model`, `variance_flag`, and the weighted total in `interview_scores`.

### Feedback screen
`GET /interviews/{id}/feedback` returns transcript, criteria with notes/improvements,
overall, variance flag and version stamps. The UI splits the transcript (left) from rubric
feedback (right); candidate answers are labelled heuristically as "strong signal" when
they are concrete (numbers/outcomes/trade-offs) or "needs evidence" when very short.
Those labels are UI guidance, not part of the stored score.

## 4. Student dashboard

`GET /dashboard/student` composes, in one round trip:

- **Readiness:** weighted blend of latest resume score (40%) and average interview score
  (60%), with fallbacks when only one exists; 0 when neither exists. Returned with a
  band and a delta versus the previous interview.
- **Radar:** the five rubric criteria from completed interviews, 0–100, or zeros if none.
- **Streak/XP/level:** streak touched once per UTC day; XP awarded for interviews,
  completed rounds and badges, minus hints. Level = XP / 250 + 1 with in-level progress.
- **Badges:** first resume, first interview, three interviews, score ≥ 80, 7-day streak,
  profile complete; locked badges are returned so the UI can show progress.
- **Next best action:** deterministic priority — upload resume → analyze resume → take
  first interview → improve weakest criterion → keep streak. Each has title, body, CTA
  and href.
- **History:** recent interviews and analyses with scores; links to feedback/resume.
- **Budget:** `/usage/me` returns month tokens, cost, budget, remaining and percent.

The UI displays this in a bento grid with a readiness ring, radar, streak/XP, badge grid,
history and budget. A one-time confetti fires after the first meaningful result.

## 5. Officer analytics

`GET /officer/overview` builds everything server-side for the officer's college:

- KPIs: students, active in 30 days, resume uploads, completed interviews, average
  readiness, placement countdown.
- Heatmap: branch × rubric-criterion mean, with student counts.
- Funnel: registered → resume uploaded → analysed → interview completed → ready (≥70).
- Weakest skills: lowest mean rubric criteria with gap from target and affected students.
- Cohort trend: weekly interviews and average score.
- Batch comparison: per-branch students, readiness, resumes, interviews.
- Students list: named rows only when `consent_share_analytics=true`; otherwise masked
  name and no individual score. `aggregate_only` reports whether any masking occurred.

`GET /officer/report.pdf` renders the same aggregate data with ReportLab. Resumes and
transcripts are never included, and PDF export is not available to students.

## 6. Admin

- **Colleges:** list with student counts; create validates a unique code; deactivation is
  supported through the API.
- **Questions:** list global + college rows; create embeds the prompt for retrieval;
  delete deactivates college-owned rows (global seeds are read-only in the UI).
- **Rubrics:** create a new version with the standard five criteria, then activate it.
  Activations are per college; scores retain the version they were produced with.
- **Usage:** per-college monthly token and cost rollups.

## 7. Cost tracking and budgets

Every LLM call goes through `LLMClient`, which:
1. Checks the user's month-to-date spend against `PER_USER_MONTHLY_BUDGET` before calling;
   over budget raises 402 `budget_exceeded` and no provider request is made.
2. Records a `usage_events` row with provider, model, feature, input/output tokens and
   computed USD cost using a per-model price table.
3. Exposes a monthly summary to the student and admin rollups.

The mock provider records deterministic token counts and zero or nominal cost so demos
exercise the same path without paid keys.

## 8. Background worker

The ARQ worker runs scheduled, idempotent jobs:
- revoke expired refresh tokens,
- mark interviews abandoned after 24 hours without completion.

Phase 1 parsing and scoring are synchronous so the first resume score arrives in one
request. The worker module is the extension point for queueing those jobs when volume
requires it (ADR-008 in ARCHITECTURE.md).

## 9. Failure behaviour

| Failure | User sees | System behaviour |
| --- | --- | --- |
| LLM unavailable / invalid JSON | Retryable error | Schema retries, then 502; no partial score stored |
| All three scoring samples invalid | "Retry scoring" | 502 with no score; interview stays active so it can be retried |
| Resume parse low quality | "Needs review" banner + warnings | Raw text stored, deterministic fallback fields |
| Upload wrong type/oversize | Inline field error | Rejected before storage |
| WebSocket closed | Reconnect banner + retry | Transcript stays in DB; rejoin replays last question |
| Budget exhausted | Budget message on action | 402 before provider call |
| Cross-tenant ID | 404 | Tenant filter, no data leak |
| PDF export failure | Inline error | No partial file downloaded |

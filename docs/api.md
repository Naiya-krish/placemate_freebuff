# API reference (v1)

Base URL: `http://localhost:8000/api/v1` (local). Interactive OpenAPI docs:
`/docs`; health probes: `/healthz` (liveness) and `/readyz` (database readiness).

All JSON endpoints accept/return `application/json` unless noted. Errors use:

```json
{"detail": "Human-readable message", "code": "machine_code"}
```

| Code | Meaning |
| --- | --- |
| 401 | Missing/invalid access token or credentials |
| 403 | Role, origin or college restriction |
| 404 | Not found **or cross-tenant probe** |
| 409 | Conflict (duplicate email, already scored, active interview) |
| 413 | Upload too large |
| 422 | Validation error |
| 402 | Monthly AI budget exhausted |
| 429 | Rate limit exceeded |

Bearer access tokens are required except for register/login/refresh/colleges and the
WebSocket handshake. Refresh/logout are cookie-authenticated and enforce an allowed
`Origin`.

## Auth

| Method | Path | Auth | Body / notes |
| --- | --- | --- | --- |
| GET | `/auth/colleges` | none | Active colleges for the sign-up dropdown |
| POST | `/auth/register` | none | `{name,email,password,college_code,branch,target_role,consent_notice,share_analytics}` |
| POST | `/auth/login` | none | `{email,password,college_code?}`; 409 if email exists at multiple colleges and no code |
| POST | `/auth/demo-login?role=student\|officer\|admin` | none | 404 when `DEMO_MODE=false` |
| POST | `/auth/refresh` | refresh cookie | Rotates the refresh token; 401 when missing/expired |
| POST | `/auth/logout` | refresh cookie | Revokes the presented token, clears cookie |
| GET | `/auth/me` | bearer | Current user |
| PATCH | `/auth/onboarding` | bearer | `{branch,target_role}`; marks onboarding complete |
| POST | `/auth/consent` | bearer | `{share_analytics: boolean}`; writes a consent row |
| GET | `/auth/google/login` | none | 302 to Google |
| GET | `/auth/google/callback` | none | Validates state, redirects to frontend callback with tokens |

`TokenResponse`: `{access_token, token_type:"bearer", expires_in, user}`. The refresh token
is never in the body; it is an HttpOnly `placemate_refresh` cookie scoped to
`/api/v1/auth`.

## Resumes and analysis

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| POST | `/resumes` | student | Multipart `file`; PDF/DOCX ≤ 5 MB; 201 `ResumeDetail` |
| GET | `/resumes` | student | Own resumes, newest first |
| GET | `/resumes/{id}` | student | Includes `parsed_data`, `raw_text`, warnings |
| GET | `/resumes/{id}/file` | student | Original file (auth required), `Content-Disposition` |
| DELETE | `/resumes/{id}` | student | 204; removes object + row |
| POST | `/resumes/{id}/analyze` | student | `{job_description, target_role}` → `AnalysisOut` |
| GET | `/resumes/{id}/analyses` | student | Analysis history, newest first |
| GET | `/analyses/latest` | student | Latest analysis across resumes |
| PATCH | `/analyses/{analysis_id}/suggestions/{suggestion_id}` | student | `{accept: boolean}`; returns updated analysis |

`AnalysisOut` highlights:

```json
{
  "id": "...",
  "resume_id": "...",
  "target_role": "Backend Engineer",
  "score": 72,
  "subscores": {"impact": 68, "clarity": 80, "evidence": 60, "relevance": 78, "structure": 74},
  "suggestions": [{
    "id": "...",
    "target_section": "project",
    "category": "impact",
    "original": "Built a REST API",
    "improved": "Built a REST API serving 10k requests/day, cutting p95 latency 420→260 ms",
    "rationale": "Adds measurable outcome already implied by the source",
    "supported": true,
    "decision": "pending"
  }],
  "missing_evidence": [{"item": "deployment scale", "reason": "No traffic or environment data in the resume"}],
  "injection_flags": [],
  "prompt_version": "v1",
  "model": "mock-cheap"
}
```

Suggestions that introduce numbers, tools or employers absent from the source are dropped
by the evidence guard, so `supported` is always true for returned suggestions. Missing
evidence is guidance, never inserted text.

## Interviews

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/rubrics/active` | any signed-in | Rubric visible before starting |
| POST | `/interviews` | student | `{resume_id, role, target_role?}` → 201 |
| GET | `/interviews` | student | Own interviews, newest first; officers get `[]` |
| GET | `/interviews/{id}` | owner | Detail incl. turns, rubric scores, feedback |
| POST | `/interviews/{id}/finish` | owner | Scores synchronously; 409 if already scored |
| GET | `/interviews/{id}/feedback` | owner | 409 until scored |
| WS | `/interviews/{id}/ws?token=...` | owner | Upgrade; see protocol below |

`role` values: `swe`, `data`, `product`, `core`, `general` (free text is mapped to a role
code server-side). Starting an interview stores `rubric_version`, `prompt_version` and
`model` so later feedback remains reproducible.

### WebSocket protocol

Client frames are JSON; max 12 KB each, 80 messages per socket.

Server → client:

```json
{"type":"session","interview_id":"...","role":"swe","round":"project",
 "rounds":["project","technical","hr"],"rubric":{"version":"v1","label":"...","criteria":[...]},
 "timer_seconds":0,"xp":120}
{"type":"typing","on":true}
{"type":"question","id":"...","round":"project","text":"Tell me about CampusRide...","is_followup":false}
{"type":"round_complete","round":"project","next":"technical","finished":false}
{"type":"hint","text":"Mention the trade-off you measured.","xp_penalty":5,"xp":115,"hints_used":1}
{"type":"scored","overall":74,"criteria":[...],"feedback":{...},"variance_flag":false,
 "rubric_version":"v1","prompt_version":"v1","model":"mock-scoring"}
{"type":"error","code":"answer_too_short","message":"Give a slightly longer answer."}
```

Client → server:

```json
{"type":"answer","content":"..."}
{"type":"hint"}
{"type":"finish"}
{"type":"ping"}
```

On connect, existing turns cause the last interviewer question to be replayed with
`resumed: true`; otherwise the first question is generated. `finish` requires at least one
answer. Scoring failure returns an `error` frame and keeps the interview active for retry.

## Student dashboard and usage

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/dashboard/student` | Readiness, band, radar, streak, XP, level, badges, next action, history, counts, skill gaps, placement countdown |
| GET | `/usage/me` | `{month, tokens, cost_usd, budget_usd, remaining_usd, percent_used}` |

## Officer

Requires `officer` or `admin` role. Always scoped to the caller's college.

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/officer/overview` | KPIs, heatmap, funnel, weakest skills, cohort progress, batch comparison, consent-gated students, `aggregate_only` |
| GET | `/officer/report.pdf` | `application/pdf`, aggregate-only report |

The overview never contains resume text or transcripts. Named student rows require
`consent_share_analytics=true`; otherwise name and individual score are masked.

## Admin

Requires `admin`. Cross-tenant by design, restricted to these routes.

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/admin/overview` | Counts + monthly usage by college |
| GET | `/admin/colleges` | All colleges with student counts |
| POST | `/admin/colleges` | `{name, code, city?, placement_date?}` |
| PATCH | `/admin/colleges/{id}` | Name/city/date/active |
| GET | `/admin/questions` | Global + all college questions |
| POST | `/admin/questions` | `{prompt, ideal_answer, role, topic, difficulty, key_points, is_global}` |
| PATCH | `/admin/questions/{id}` | Update fields/active |
| DELETE | `/admin/questions/{id}` | 204; deactivates |
| GET | `/admin/rubrics` | All rubric versions |
| POST | `/admin/rubrics` | `{version, label, criteria[], activate}` |
| POST | `/admin/rubrics/{id}/activate` | Activates within its college |

## Account

| Method | Path | Notes |
| --- | --- | --- |
| DELETE | `/account` | Body `{confirm:"DELETE", password?}`; deletes user + all owned data and objects |

Password is required for accounts that have one. Demo accounts may omit it. This is
irreversible; the UI asks the student to type `DELETE`.

## Rate limits (defaults)

`auth 10/min`, `upload 10/min`, `analysis 12/min`, `interview 10/min`, `default 120/min`.
Configure with `RATE_LIMIT_*`. In production use a shared Redis storage URI so limits are
global across API replicas.

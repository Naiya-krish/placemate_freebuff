# Rubric and scoring

The rubric is visible to the student **before** the interview starts, stored per college,
and versioned. A score always records the rubric version, prompt version and model that
produced it. Default rubric: `v1` — "PlaceMate standard rubric v1".

## Criteria (v1)

| Key | Label | Weight | What a strong answer shows |
| --- | --- | --- | --- |
| `clarity` | Clarity | 18% | Structured, concise, understandable without jargon |
| `technical_depth` | Technical depth | 24% | Mechanisms, constraints and trade-offs at the right level |
| `problem_solving` | Problem solving | 22% | Reasoned approach, alternatives, validation with evidence |
| `communication` | Communication | 16% | Answers the question, listens, adapts the explanation |
| `role_fit` | Role fit | 20% | Examples and motivation match the target role |

Weights are normalised before use, so an admin-created rubric with weights that do not sum
to 1 is still safe. Each criterion is scored **0–10**; the overall is a 0–100 weighted
total computed on the server.

## Scoring pipeline

1. **Transcript build** — only interviewer and candidate turns; resume context is included
   separately, fenced as untrusted.
2. **Three samples** — the scoring model is called three times at temperature 0.2 with a
   strict JSON schema. Token and cost are logged per call.
3. **Validation** — `RubricScoreAI` requires every rubric key, an integer 0–10, a short
   note and one improvement line. Invalid output is retried up to
   `SCORING_MAX_RETRIES`; an invalid sample is discarded.
4. **Median** — per criterion, the median of the valid samples. The note/improvement come
   from the sample closest to the median.
5. **Overall** — `round(Σ(median_score × normalized_weight) × 10)`, clamped 0–100. The
   model never supplies the overall score.
6. **Variance** — if any criterion's max−min across samples exceeds 15, set
   `variance_flag` and `needs_review`; surface it to the student and in aggregate review
   counts. A human should look before the score is used for decisions.
7. **Persist** — `interview_scores` stores rubric/prompt/model versions, medians, samples,
   spread and flags; `interviews` stores the overall and completion time.

If every sample fails validation, the API returns an error and the interview stays active
so the student can retry. No partial score is stored.

## What the model sees

- **System message:** fixed instructions, scoring rules and the Pydantic JSON schema.
- **Rubric block:** keys, labels, weights and descriptions from the DB.
- **Resume block:** fenced `[UNTRUSTED_RESUME ...]` with a random boundary, capped at
  6,000 chars.
- **Transcript block:** fenced `[UNTRUSTED_TRANSCRIPT ...]`, capped at 18,000 chars.

Resume and transcript content are data, never instructions. Injection patterns are
detected earlier and flagged, but scoring does not rely on detection alone: the schema,
the server-side total and the evidence guard bound the damage a hostile document can do.

## Resume rubric (separate from interview)

Resume analysis returns an overall 0–100 plus five subscores: `impact`, `clarity`,
`evidence`, `relevance`, `structure`. These are qualitative guidance, not the readiness
score.

## Readiness formula

```
readiness = round(0.4 × latest_resume_score + 0.6 × avg_interview_score)
```

When only one component exists, it is used alone; with neither, readiness is 0. Bands:

| Score | Band |
| --- | --- |
| ≥ 85 | Exceptional |
| ≥ 70 | Interview-ready |
| ≥ 55 | Building |
| ≥ 35 | Warming up |
| < 35 | Getting started |

Readiness is a coaching signal, not a hiring prediction. Officers see cohort means and
distributions; they do not see individual scores without student consent.

## Changing the rubric

Never edit an existing version in place. Create a new version in **Admin → Rubrics** (or a
seed for a new default). New interviews use the active rubric; old feedback keeps its
original version. If criteria keys change, update the scoring schema and
`docs/prompts.md` together, and add a migration note.

## Version history

| Version | Date | Change |
| --- | --- | --- |
| v1 | 2026-11 | Initial five-criterion rubric |

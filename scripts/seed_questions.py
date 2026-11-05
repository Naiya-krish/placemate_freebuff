#!/usr/bin/env python3
"""Seed the global question bank (college_id = NULL) with pgvector embeddings.

Usage: python scripts/seed_questions.py [--if-empty]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db.session import SessionLocal  # noqa: E402
from app.models.question import QuestionBank  # noqa: E402
from app.services.embeddings import embed_text  # noqa: E402

QUESTIONS: list[dict[str, object]] = [
    # --- project deep-dive ---
    {
        "role": "general",
        "topic": "project",
        "difficulty": "medium",
        "prompt": "Walk me through the architecture of a project you built and the part you personally owned.",
        "ideal_answer": "A clear one-minute summary: problem, users, components, data flow, your ownership and a measured outcome.",
        "key_points": ["problem", "architecture", "ownership", "trade-offs", "outcome"],
    },
    {
        "role": "general",
        "topic": "project",
        "difficulty": "hard",
        "prompt": "What is the hardest bug you have debugged in your project, and how did you isolate it?",
        "ideal_answer": "Reproduction, hypotheses, instrumentation, narrowing the search space, fix and regression test.",
        "key_points": ["reproduction", "hypothesis", "instrumentation", "verification"],
    },
    {
        "role": "swe",
        "topic": "project",
        "difficulty": "medium",
        "prompt": "How did you test the most critical path in your project before shipping?",
        "ideal_answer": "Unit and integration tests, fixtures, manual verification, and monitoring after release.",
        "key_points": ["unit tests", "integration", "edge cases", "monitoring"],
    },
    {
        "role": "swe",
        "topic": "project",
        "difficulty": "hard",
        "prompt": "If traffic to your project grew tenfold tomorrow, which component would you change first and why?",
        "ideal_answer": "Identify the bottleneck with evidence, then discuss caching, indexing, queueing and horizontal scaling.",
        "key_points": ["bottleneck", "measurement", "caching", "scaling"],
    },
    {
        "role": "data",
        "topic": "project",
        "difficulty": "medium",
        "prompt": "Describe a dataset you worked with: how did you clean it and how did you validate the result?",
        "ideal_answer": "Source, schema, missing values, leakage checks, train/validation split and baseline comparison.",
        "key_points": ["data quality", "leakage", "validation", "baseline"],
    },
    # --- technical basics ---
    {
        "role": "swe",
        "topic": "technical",
        "difficulty": "easy",
        "prompt": "Explain the difference between a list and a dictionary, and when you would choose each.",
        "ideal_answer": "Ordering/index access versus key lookup; complexity and memory trade-offs.",
        "key_points": ["complexity", "lookup", "ordering"],
    },
    {
        "role": "swe",
        "topic": "technical",
        "difficulty": "medium",
        "prompt": "How does database indexing work, and when can an index make performance worse?",
        "ideal_answer": "B-tree lookup, selectivity, write amplification, unused index overhead.",
        "key_points": ["b-tree", "selectivity", "write cost"],
    },
    {
        "role": "swe",
        "topic": "technical",
        "difficulty": "medium",
        "prompt": "What happens between a browser sending a request and the response rendering?",
        "ideal_answer": "DNS, TCP/TLS, HTTP, server handling, streaming, parsing, layout and paint.",
        "key_points": ["dns", "tls", "http", "rendering"],
    },
    {
        "role": "swe",
        "topic": "technical",
        "difficulty": "hard",
        "prompt": "Design a rate limiter for a public API. Which algorithm and data store would you use?",
        "ideal_answer": "Token bucket or sliding window, Redis with atomic operations, race conditions and clock skew.",
        "key_points": ["token bucket", "redis", "atomicity", "clock skew"],
    },
    {
        "role": "swe",
        "topic": "technical",
        "difficulty": "medium",
        "prompt": "Why do we need transactions in a database? Give an example from your own code.",
        "ideal_answer": "Atomicity, isolation, consistency and durability with a concrete multi-step write.",
        "key_points": ["atomicity", "isolation", "rollback"],
    },
    {
        "role": "swe",
        "topic": "technical",
        "difficulty": "medium",
        "prompt": "What is the difference between unit, integration and end-to-end tests? What do you test at each level?",
        "ideal_answer": "Scope, speed and confidence trade-offs; test behaviour not implementation; the trophy vs pyramid model.",
        "key_points": ["scope", "speed", "behaviour", "trade-offs"],
    },
    {
        "role": "data",
        "topic": "technical",
        "difficulty": "medium",
        "prompt": "Explain precision and recall with an example where false negatives are expensive.",
        "ideal_answer": "Definitions, confusion matrix, threshold choice and business cost of errors.",
        "key_points": ["precision", "recall", "threshold", "cost"],
    },
    {
        "role": "data",
        "topic": "technical",
        "difficulty": "hard",
        "prompt": "How would you detect and handle data leakage in a machine learning pipeline?",
        "ideal_answer": "Time-based splits, pipeline-scoped preprocessing, target leakage checks and holdout validation.",
        "key_points": ["leakage", "splits", "preprocessing", "holdout"],
    },
    {
        "role": "core",
        "topic": "technical",
        "difficulty": "medium",
        "prompt": "Explain setup and hold time in digital circuits and why they matter.",
        "ideal_answer": "Timing constraints, metastability and clock frequency limits.",
        "key_points": ["setup", "hold", "metastability", "clock"],
    },
    {
        "role": "product",
        "topic": "technical",
        "difficulty": "medium",
        "prompt": "How would you decide whether a new feature should ship? Name the metrics you would track.",
        "ideal_answer": "Problem validation, success metric, guardrail metric, experiment design and rollback plan.",
        "key_points": ["success metric", "guardrail", "experiment"],
    },
    # --- HR / behavioural ---
    {
        "role": "general",
        "topic": "hr",
        "difficulty": "easy",
        "prompt": "Tell me about yourself in under two minutes, focused on why this role fits you.",
        "ideal_answer": "Present, relevant evidence, motivation and a forward-looking close.",
        "key_points": ["relevance", "evidence", "motivation"],
    },
    {
        "role": "general",
        "topic": "hr",
        "difficulty": "medium",
        "prompt": "Describe a time you disagreed with a teammate. How did you resolve it?",
        "ideal_answer": "Situation, the other view, the data you used, the resolution and the relationship afterwards.",
        "key_points": ["conflict", "listening", "resolution", "reflection"],
    },
    {
        "role": "general",
        "topic": "hr",
        "difficulty": "medium",
        "prompt": "Tell me about a deadline you nearly missed. What did you change afterwards?",
        "ideal_answer": "Ownership, early escalation, prioritisation and a concrete process change.",
        "key_points": ["ownership", "escalation", "prioritisation", "learning"],
    },
    {
        "role": "general",
        "topic": "hr",
        "difficulty": "medium",
        "prompt": "Where do you want to be in three years, and what will you do in your first month here?",
        "ideal_answer": "Realistic ambition, learning plan and a contribution to the team.",
        "key_points": ["growth", "learning", "contribution"],
    },
    {
        "role": "general",
        "topic": "hr",
        "difficulty": "hard",
        "prompt": "Tell me about feedback that changed how you work.",
        "ideal_answer": "Specific feedback, honest reaction, a change in behaviour and the observed result.",
        "key_points": ["feedback", "self-awareness", "behaviour change"],
    },
    {
        "role": "general",
        "topic": "hr",
        "difficulty": "medium",
        "prompt": "Why should we hire you over another candidate with similar skills?",
        "ideal_answer": "Differentiated evidence, not adjectives: ownership, learning speed, impact.",
        "key_points": ["differentiation", "evidence", "impact"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--if-empty", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as db:
        existing = db.query(QuestionBank).filter(QuestionBank.college_id.is_(None)).count()
        if args.if_empty and existing > 0:
            print(f"question bank already has {existing} global questions; skipping")
            return 0
        added = 0
        for item in QUESTIONS:
            prompt = str(item["prompt"])
            duplicate = (
                db.query(QuestionBank)
                .filter(QuestionBank.prompt == prompt, QuestionBank.college_id.is_(None))
                .first()
            )
            if duplicate:
                continue
            db.add(
                QuestionBank(
                    college_id=None,
                    role=str(item["role"]),
                    topic=str(item["topic"]),
                    difficulty=str(item["difficulty"]),
                    prompt=prompt,
                    ideal_answer=str(item["ideal_answer"]),
                    key_points=list(item["key_points"]),  # type: ignore[arg-type]
                    embedding=embed_text(prompt + " " + " ".join(item["key_points"])),  # type: ignore[arg-type]
                    is_active=True,
                )
            )
            added += 1
        db.commit()
        print(f"seeded {added} questions ({existing + added} global total)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

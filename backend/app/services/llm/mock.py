"""Deterministic mock LLM used by tests, CI and demo mode. Zero cost, no network."""

from __future__ import annotations

import json
import re
import time
from typing import Any

from app.core.config import settings
from app.services.llm.base import LLMMessage, LLMResult

SKILLS = [
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "C++",
    "Go",
    "Rust",
    "SQL",
    "PostgreSQL",
    "MySQL",
    "MongoDB",
    "Redis",
    "Docker",
    "Kubernetes",
    "AWS",
    "GCP",
    "Azure",
    "React",
    "Next.js",
    "Node.js",
    "FastAPI",
    "Django",
    "Flask",
    "Spring Boot",
    "TensorFlow",
    "PyTorch",
    "Pandas",
    "NumPy",
    "scikit-learn",
    "Git",
    "Linux",
    "GraphQL",
    "Kafka",
    "Spark",
    "Tableau",
    "Power BI",
    "Figma",
]
ROLE_KEYWORDS = {
    "swe": ["data structures", "algorithms", "api", "testing", "system design", "git"],
    "data": ["python", "sql", "statistics", "pandas", "machine learning", "visualization"],
    "product": ["analytics", "user research", "roadmap", "metrics", "stakeholder"],
    "core": ["electronics", "embedded", "verilog", "microprocessor", "circuits"],
}
WEAK_VERBS = {
    "worked on": "Built",
    "worked with": "Collaborated with",
    "helped with": "Contributed to",
    "helped in": "Contributed to",
    "responsible for": "Owned",
    "assisted with": "Supported",
    "involved in": "Drove",
}


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _extract_name(text: str) -> str:
    for line in _lines(text)[:5]:
        if "@" in line or re.search(r"\d{4,}", line):
            continue
        cleaned = re.sub(r"[^A-Za-z .'-]", "", line).strip()
        if 2 <= len(cleaned) <= 60 and len(cleaned.split()) <= 5:
            return cleaned
    return "Candidate"


def _extract_sections(text: str) -> dict[str, list[str]]:
    headings = {
        "summary": ["summary", "objective", "profile"],
        "skills": ["skills", "technical skills", "technologies"],
        "projects": ["projects", "academic projects", "personal projects"],
        "experience": ["experience", "work experience", "internships", "employment"],
        "education": ["education", "academics"],
        "certifications": ["certifications", "certificates", "licenses"],
        "achievements": ["achievements", "awards", "honors", "accomplishments"],
    }
    sections: dict[str, list[str]] = {k: [] for k in headings}
    current = "summary"
    for line in _lines(text):
        probe = re.sub(r"[^a-z& ]", "", line.lower()).strip(" :")
        matched = next((key for key, names in headings.items() if probe in names), None)
        if matched:
            current = matched
            continue
        sections[current].append(line)
    return sections


def _bullets(lines: list[str]) -> list[str]:
    out = []
    for line in lines:
        out.append(re.sub(r"^[\-•*·]\s*", "", line).strip())
    return [b for b in out if b]


def _mock_resume_parse(variables: dict[str, Any]) -> dict[str, Any]:
    text = str(variables.get("resume_text", ""))
    low = text.lower()
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    phone_match = re.search(r"(?:\+91[\s-]?)?[6-9]\d{9}", text)
    links = re.findall(r"https?://\S+", text)
    sections = _extract_sections(text)
    skills = [s for s in SKILLS if re.search(rf"(?<![\w.]){re.escape(s.lower())}(?![\w.])", low)]

    projects: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in sections["projects"]:
        if line.startswith(("-", "•", "*")):
            if current:
                current["bullets"].append(re.sub(r"^[\-•*]\s*", "", line))
            continue
        if len(line) > 110:
            if current:
                current["description"] = (current["description"] + " " + line).strip()[:1500]
            continue
        current = {"name": line[:180], "description": "", "tech": [], "bullets": []}
        projects.append(current)
    for project in projects:
        haystack = f"{project['name']} {project['description']}".lower()
        project["tech"] = [s for s in skills if s.lower() in haystack]

    experience: list[dict[str, Any]] = []
    current_exp: dict[str, Any] | None = None
    for line in sections["experience"]:
        if line.startswith(("-", "•", "*")):
            if current_exp:
                current_exp["bullets"].append(re.sub(r"^[\-•*]\s*", "", line))
            continue
        if len(line) > 100:
            continue
        parts = [p.strip() for p in re.split(r"[|,—]| at ", line) if p.strip()]
        current_exp = {
            "company": parts[-1][:180] if len(parts) > 1 else line[:180],
            "title": parts[0][:180] if parts else "",
            "start": "",
            "end": "",
            "location": "",
            "bullets": [],
        }
        experience.append(current_exp)

    education = []
    for line in sections["education"][:4]:
        if len(line) < 4:
            continue
        education.append(
            {
                "institution": line[:180],
                "degree": "Bachelor of Technology" if "b.tech" in line.lower() else "",
                "field": "Computer Science" if "computer" in line.lower() else "",
                "start": "",
                "end": "",
                "score": "",
            }
        )

    summary_lines = sections["summary"][:3]
    return {
        "full_name": _extract_name(text),
        "email": email_match.group(0) if email_match else "",
        "phone": phone_match.group(0) if phone_match else "",
        "links": links[:5],
        "summary": " ".join(summary_lines)[:900],
        "skills": skills[:40],
        "experience": experience[:8],
        "projects": projects[:8],
        "education": education,
        "certifications": _bullets(sections["certifications"])[:8],
        "achievements": _bullets(sections["achievements"])[:8],
    }


def _metrics(text: str) -> int:
    return len(re.findall(r"\b\d+(?:\.\d+)?%|\b\d{2,}\b", text))


def _word_ratio(source: str, target: str) -> float:
    src = {w for w in re.findall(r"[a-z]{3,}", source.lower())}
    tgt = {w for w in re.findall(r"[a-z]{3,}", target.lower())}
    return len(src & tgt) / max(1, len(src))


def _mock_analysis(variables: dict[str, Any]) -> dict[str, Any]:
    text = str(variables.get("resume_text", ""))
    jd = str(variables.get("job_description", ""))
    role = str(variables.get("target_role", "Software Engineer"))
    low = text.lower()
    bullets = [ln for ln in _lines(text) if ln.startswith(("-", "•", "*"))]
    metric_count = _metrics(text)
    skills = [s for s in SKILLS if s.lower() in low]
    has_links = bool(re.search(r"https?://", text))
    section_hits = sum(
        1 for name in ("summary", "skills", "projects", "experience", "education") if name in low
    )
    jd_overlap = _word_ratio(jd, text) if jd.strip() else _word_ratio(role, " ".join(skills))

    clarity = 64 + min(14, len(bullets)) + (6 if section_hits >= 3 else 0)
    impact = 42 + min(38, metric_count * 9) + (6 if "led" in low or "owned" in low else 0)
    relevance = 46 + int(jd_overlap * 42) + (6 if skills else 0)
    structure = 52 + section_hits * 7
    keywords = 42 + min(42, len(skills) * 5) + (5 if has_links else 0)
    subscores = {
        "clarity": max(20, min(92, clarity)),
        "impact": max(20, min(94, impact)),
        "relevance": max(20, min(94, relevance)),
        "structure": max(20, min(94, structure)),
        "keywords": max(20, min(94, keywords)),
    }
    overall = round(
        subscores["clarity"] * 0.18
        + subscores["impact"] * 0.28
        + subscores["relevance"] * 0.26
        + subscores["structure"] * 0.14
        + subscores["keywords"] * 0.14
    )

    suggestions = []
    for bullet in bullets:
        plain = re.sub(r"^[\-•*]\s*", "", bullet).strip()
        if len(plain) < 18 or _metrics(plain):
            continue
        improved = plain
        lowered = plain.lower()
        for weak, strong in WEAK_VERBS.items():
            if lowered.startswith(weak):
                improved = strong + plain[len(weak) :]
                break
        else:
            improved = "Delivered " + plain[0].lower() + plain[1:] if plain else plain
            if improved == plain:
                improved = plain + " — with scope and outcome stated."
        if improved == plain:
            continue
        suggestions.append(
            {
                "target_section": "experience",
                "category": "impact",
                "original": plain,
                "improved": improved,
                "rationale": "Stronger opening verb improves impact and clarity without changing facts.",
            }
        )
        if len(suggestions) >= 3:
            break

    if not suggestions and text:
        first = _sentences(text)[0][:300] if _sentences(text) else text[:200]
        suggestions.append(
            {
                "target_section": "summary",
                "category": "clarity",
                "original": first,
                "improved": first.replace("I am", "Motivated engineer with", 1)
                if "I am" in first
                else first,
                "rationale": "Lead with your strongest verifiable achievement to improve clarity.",
            }
        )
        suggestions = [s for s in suggestions if s["original"] != s["improved"]] or suggestions

    missing = []
    jd_terms = [
        t
        for t in re.findall(r"[A-Za-z][A-Za-z+#.]{2,}", jd)
        if len(t) > 3 and t.lower() in {k.lower() for k in ROLE_KEYWORDS.get("swe", [])}
    ]
    for term in dict.fromkeys(jd_terms):
        if term.lower() not in low:
            missing.append(
                {
                    "item": term,
                    "reason": f"'{term}' appears in the job description but is not evidenced in the resume.",
                }
            )
        if len(missing) >= 4:
            break
    if not missing:
        for label, reason in (
            ("Quantified outcomes", "Add real, documented metrics to at least two bullets."),
            (
                "Tests or quality evidence",
                "Show how you validated your work (tests, reviews, monitoring).",
            ),
        ):
            if label.split()[0].lower() not in low:
                missing.append({"item": label, "reason": reason})
    if not missing:
        missing.append(
            {
                "item": "Deployment evidence",
                "reason": "The resume does not show where a project ran or who used it; add that if it is true.",
            }
        )

    summary = (
        f"Solid foundations for {role}. The resume is readable but "
        f"{'lacks quantified outcomes' if metric_count < 2 else 'can foreground outcomes more strongly'}; "
        "tighten two or three bullets around what you built and the measurable result."
    )
    payload: dict[str, Any] = {
        "overall_score": overall,
        "subscores": subscores,
        "suggestions": suggestions[:4],
        "missing_evidence": missing[:5],
        "summary": summary,
    }
    if settings.mock_llm_hallucinate:
        payload["suggestions"].append(
            {
                "target_section": "experience",
                "category": "impact",
                "original": bullets[0].lstrip("-•* ").strip()
                if bullets
                else (text[:80] or "Intern"),
                "improved": "Led 50 engineers at Google and increased revenue by 40%.",
                "rationale": "Invented claim used to test the evidence guard.",
            }
        )
    return payload


PROJECT_QUESTIONS = [
    "Walk me through {project}: what problem did it solve, and what was your specific contribution?",
    "In {project}, what was the hardest technical decision you made, and why?",
    "If you had to scale {project} to 10x users, what would break first and how would you fix it?",
]
PROJECT_FALLBACK = [
    "Tell me about the project you are most proud of and the part you personally owned.",
    "Pick a project that failed or changed direction — what did you learn?",
]
TECHNICAL_QUESTIONS = [
    "Explain the difference between a process and a thread, with a real example from your work.",
    "How would you design a rate limiter for a public API? Walk me through the data structures.",
    "What happens between typing a URL and seeing the page? Where would you look first if it were slow?",
    "How do you decide between SQL and NoSQL for a new service? Give a concrete trade-off.",
    "Explain database indexing to a junior engineer, including when an index hurts performance.",
]
HR_QUESTIONS = [
    "Tell me about a time you disagreed with a teammate. How did you resolve it?",
    "Describe a deadline you nearly missed. What did you change in how you worked?",
    "Why this role, and what do you want to be known for in your first year?",
    "Tell me about feedback that changed how you work.",
]


def _mock_question(variables: dict[str, Any]) -> dict[str, Any]:
    round_name = str(variables.get("round", "project"))
    asked = {str(q).lower() for q in variables.get("asked", [])}
    projects = variables.get("project_names", []) or []
    candidates = variables.get("candidates", []) or []
    pool: list[str] = []
    if round_name == "project":
        if projects:
            pool = [q.format(project=projects[0]) for q in PROJECT_QUESTIONS]
        pool += PROJECT_FALLBACK
        pool += [c for c in candidates if str(c).strip()]
    elif round_name == "technical":
        pool = [str(c) for c in candidates if str(c).strip()] + TECHNICAL_QUESTIONS
    else:
        pool = [str(c) for c in candidates if str(c).strip()] + HR_QUESTIONS
    question = next(
        (q for q in pool if q.lower() not in asked), pool[0] if pool else "Tell me about yourself."
    )
    return {
        "question": question,
        "intent": "assess ownership and depth"
        if round_name != "hr"
        else "assess collaboration and self-awareness",
        "difficulty": "medium",
    }


def _mock_followup(variables: dict[str, Any]) -> dict[str, Any]:
    answer = str(variables.get("last_answer", "")).strip()
    topic = "that"
    for keyword in ("cache", "database", "api", "model", "test", "deploy", "queue", "index"):
        if keyword in answer.lower():
            topic = keyword
            break
    if not answer:
        question = "No answer came through — give me one concrete example from your resume."
    elif topic != "that":
        question = f"You mentioned {topic}. What trade-off did you personally make there, and what would you change now?"
    else:
        snippet = " ".join(answer.split()[:9])
        question = f"You said “{snippet}…”. What was your specific contribution, and how did you measure the result?"
    return {
        "question": question[:400],
        "intent": "probe ownership and evidence",
        "difficulty": "medium",
    }


def _mock_score(variables: dict[str, Any]) -> dict[str, Any]:
    answers = [str(a) for a in variables.get("answers", [])]
    transcript = str(variables.get("transcript", ""))
    words = [len(a.split()) for a in answers]
    avg_words = sum(words) / max(1, len(words))
    has_metrics = bool(re.search(r"\b\d+(?:\.\d+)?%", transcript))
    has_tradeoff = bool(
        re.search(r"(?i)\b(trade-?off|because|instead|however|chose)\b", transcript)
    )
    has_testing = bool(re.search(r"(?i)\b(test|monitor|debug|log|review)\b", transcript))
    has_team = bool(re.search(r"(?i)\b(team|stakeholder|mentor|collaborat)\b", transcript))
    criteria = variables.get("rubric", []) or []

    def base() -> int:
        if not answers:
            return 2
        score = 4
        score += 1 if avg_words >= 35 else 0
        score += 1 if avg_words >= 70 else 0
        score += 1 if has_metrics else 0
        score += 1 if has_tradeoff else 0
        return min(8, score)

    payload_criteria = []
    for criterion in criteria:
        key = (
            str(criterion.get("key", "clarity")) if isinstance(criterion, dict) else str(criterion)
        )
        score = base()
        if key == "clarity" and avg_words >= 30:
            score += 1
        if key == "technical_depth" and (has_metrics or has_tradeoff):
            score += 1
        if key == "problem_solving" and has_testing:
            score += 1
        if key == "communication" and has_team:
            score += 1
        if key == "role_fit" and has_metrics:
            score += 1
        score = max(2, min(9, score))
        note = f"Answers averaged {round(avg_words)} words; " + (
            "concrete metrics and trade-offs were present."
            if has_metrics and has_tradeoff
            else "more concrete evidence was needed."
        )
        improvement = {
            "clarity": "Use a 3-part structure: context, your action, measurable result.",
            "technical_depth": "Name the exact technology, constraint and trade-off you chose.",
            "problem_solving": "Explain how you validated the fix, not only what you built.",
            "communication": "Close each answer with the outcome and what you learned.",
            "role_fit": "Tie each example back to the responsibilities in the job description.",
        }.get(key, "Add one concrete, verifiable detail to each answer.")
        payload_criteria.append(
            {"key": key, "score": score, "note": note, "improvement": improvement}
        )
    if not payload_criteria:
        payload_criteria = [
            {
                "key": "clarity",
                "score": base(),
                "note": "Evidence reviewed.",
                "improvement": "Use structure.",
            }
        ]
    return {
        "criteria": payload_criteria,
        "strengths": [
            "Stayed engaged through all three rounds." if answers else "Completed the session.",
            "Grounded answers in resume projects."
            if has_metrics
            else "Answers referenced real projects.",
        ],
        "improvements": [
            "Quantify outcomes with the real numbers you measured.",
            "State your individual contribution when describing team work.",
        ],
        "summary": (
            "A promising practice run with clear ownership signals. "
            "The next step is replacing general statements with specific, verifiable outcomes."
        ),
    }


class MockProvider:
    """Deterministic provider; same inputs always produce the same JSON."""

    name = "mock"

    def generate(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
        task: str = "",
        variables: dict[str, Any] | None = None,
    ) -> LLMResult:
        started = time.perf_counter()
        variables = variables or {}
        if task == "resume_parse":
            payload = _mock_resume_parse(variables)
        elif task == "resume_analysis":
            payload = _mock_analysis(variables)
        elif task == "interview_question":
            payload = _mock_question(variables)
        elif task == "interview_followup":
            payload = _mock_followup(variables)
        elif task == "scoring":
            payload = _mock_score(variables)
        else:
            payload = {"result": "ok"}
        text = json.dumps(payload, ensure_ascii=False)
        prompt_chars = sum(len(m.content) for m in messages) + len(json.dumps(variables))
        latency = int((time.perf_counter() - started) * 1000)
        return LLMResult(
            text=text,
            model="mock",
            input_tokens=max(1, prompt_chars // 4),
            output_tokens=max(1, len(text) // 4),
            provider=self.name,
            latency_ms=latency,
        )

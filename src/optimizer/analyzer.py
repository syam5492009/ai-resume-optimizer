"""
src/optimizer/analyzer.py
--------------------------
ATS scoring and keyword analysis — calls the LLM to assess a resume.
"""
import json
import logging
from dataclasses import dataclass

from src.optimizer.prompts import ATS_ANALYSIS_PROMPT, SCORE_ONLY_PROMPT
from src.utils.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ATSReport:
    ats_score: int
    score_breakdown: dict
    critical_issues: list[str]
    improvements: list[str]
    missing_keywords: list[str]
    found_keywords: list[str]
    strengths: list[str]
    parsed_sections: dict

    @property
    def grade(self) -> str:
        if self.ats_score >= 85:
            return "Excellent"
        elif self.ats_score >= 70:
            return "Good"
        elif self.ats_score >= 55:
            return "Needs Work"
        else:
            return "Poor — likely filtered by ATS"


def analyze_resume(
    resume_text: str,
    target_role: str = "",
    job_description: str = "",
) -> ATSReport:
    """
    Run ATS analysis on a resume and return a detailed report.

    Args:
        resume_text:     Plain text of the resume.
        target_role:     Optional job title (e.g. "Senior Software Engineer").
        job_description: Optional JD text for keyword matching.

    Returns:
        ATSReport with score, issues, and improvements.
    """
    prompt = ATS_ANALYSIS_PROMPT.format(
        resume_text=resume_text,
        target_role=target_role or "Not specified",
        job_description=job_description or "Not provided",
    )

    raw = _call_llm(prompt)
    data = _safe_parse(raw)

    return ATSReport(
        ats_score=int(data.get("ats_score", 50)),
        score_breakdown=data.get("score_breakdown", {}),
        critical_issues=data.get("critical_issues", []),
        improvements=data.get("improvements", []),
        missing_keywords=data.get("missing_keywords", []),
        found_keywords=data.get("found_keywords", []),
        strengths=data.get("strengths", []),
        parsed_sections=data.get("parsed_sections", {}),
    )


def quick_score(resume_text: str) -> tuple[int, str]:
    """Fast ATS score only — cheaper than full analysis."""
    prompt = SCORE_ONLY_PROMPT.format(resume_text=resume_text[:3000])
    raw = _call_llm(prompt)
    data = _safe_parse(raw)
    return int(data.get("score", 50)), data.get("one_line_verdict", "")


# ── LLM caller (supports Anthropic + OpenAI) ─────────────────────────────────

def _call_llm(prompt: str) -> str:
    if settings.AI_PROVIDER == "anthropic":
        return _call_anthropic(prompt)
    return _call_openai(prompt)


def _call_anthropic(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _call_openai(prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096,
        temperature=0.3,
    )
    return response.choices[0].message.content


def _safe_parse(raw: str) -> dict:
    """Parse JSON from LLM output, stripping markdown fences if present."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("LLM returned non-JSON. Raw: %s", raw[:200])
        return {}

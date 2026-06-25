"""
src/optimizer/analyzer.py
--------------------------
ATS scoring and keyword analysis — calls the LLM to assess a resume.
"""
import json
import logging
from dataclasses import dataclass, field

from src.optimizer.prompts import ATS_ANALYSIS_PROMPT, SCORE_ONLY_PROMPT
from src.utils.config import settings

logger = logging.getLogger(__name__)

# Approximate pricing per 1M tokens (input, output) as of 2025
_COST_PER_1M: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-8": (15.0, 75.0),
    "claude-haiku-4-5-20251001": (0.80, 4.0),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.0),
}


@dataclass
class ATSReport:
    ats_score: int
    score_breakdown: dict
    critical_issues: list[str]
    improvements: list[str]
    missing_keywords: list[str]
    found_keywords: list[str]
    strengths: list[str]
    parsed_sections: dict = field(default_factory=dict)
    tokens_used: dict = field(default_factory=dict)

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
        ATSReport with score, issues, improvements, and token usage.
    """
    prompt = ATS_ANALYSIS_PROMPT.format(
        resume_text=resume_text,
        target_role=target_role or "Not specified",
        job_description=job_description or "Not provided",
    )

    raw, tokens = _call_llm(prompt)
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
        tokens_used=tokens,
    )


def quick_score(resume_text: str) -> tuple[int, str]:
    """Fast ATS score only — cheaper than full analysis."""
    prompt = SCORE_ONLY_PROMPT.format(resume_text=resume_text[:3000])
    raw, _ = _call_llm(prompt)
    data = _safe_parse(raw)
    return int(data.get("score", 50)), data.get("one_line_verdict", "")


# ── LLM caller (supports Anthropic + OpenAI) ─────────────────────────────────

def _call_llm(prompt: str) -> tuple[str, dict]:
    if settings.AI_PROVIDER == "anthropic":
        return _call_anthropic(prompt)
    return _call_openai(prompt)


def _call_anthropic(prompt: str) -> tuple[str, dict]:
    import anthropic
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    inp, out = message.usage.input_tokens, message.usage.output_tokens
    return message.content[0].text, _build_usage(inp, out, settings.ANTHROPIC_MODEL)


def _call_openai(prompt: str) -> tuple[str, dict]:
    from openai import OpenAI
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096,
        temperature=0.3,
    )
    inp = response.usage.prompt_tokens
    out = response.usage.completion_tokens
    return response.choices[0].message.content, _build_usage(inp, out, settings.OPENAI_MODEL)


def _build_usage(input_tokens: int, output_tokens: int, model: str) -> dict:
    """Build a token usage dict including estimated cost."""
    input_rate, output_rate = _COST_PER_1M.get(model, (3.0, 15.0))
    cost = round((input_tokens * input_rate + output_tokens * output_rate) / 1_000_000, 6)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "estimated_cost_usd": cost,
    }


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

"""
src/optimizer/rewriter.py
--------------------------
AI-powered resume rewriting. Takes raw resume text + options,
returns a structured ResumeData object ready for document generation.
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Literal

from src.optimizer.prompts import REWRITE_PROMPT
from src.optimizer.analyzer import _call_llm, _safe_parse, ATSReport

logger = logging.getLogger(__name__)

Style = Literal["minimal", "professional", "executive"]


@dataclass
class ContactInfo:
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""


@dataclass
class Experience:
    company: str = ""
    title: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    bullets: list[str] = field(default_factory=list)


@dataclass
class Project:
    name: str = ""
    role: str = ""
    period: str = ""
    url: str = ""
    technologies: str = ""
    description: str = ""


@dataclass
class POC:
    name: str = ""
    description: str = ""


@dataclass
class Education:
    degree: str = ""
    field: str = ""
    institution: str = ""
    year: str = ""


@dataclass
class ResumeData:
    """Structured resume data — fed directly into document generators."""
    name: str = ""
    title: str = ""
    contact: ContactInfo = field(default_factory=ContactInfo)
    summary: str = ""
    skills: dict[str, list[str]] = field(default_factory=dict)
    experience: list[Experience] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    pocs: list[POC] = field(default_factory=list)
    education: list[Education] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    publications: list[str] = field(default_factory=list)


def rewrite_resume(
    resume_text: str,
    target_role: str = "",
    job_description: str = "",
    style: Style = "professional",
    analysis: ATSReport | None = None,
) -> tuple[ResumeData, dict]:
    """
    Rewrite a resume to be ATS-optimized.

    Args:
        resume_text:     Original resume plain text.
        target_role:     Optional job title to tailor for.
        job_description: Optional JD text for keyword matching.
        style:           "minimal" | "professional" | "executive"
        analysis:        Pre-computed ATS analysis (avoids duplicate LLM call).

    Returns:
        Tuple of (ResumeData, tokens_used dict) ready for DOCX/PDF generation.
    """
    missing_keywords = analysis.missing_keywords if analysis else []

    prompt = REWRITE_PROMPT.format(
        resume_text=resume_text,
        target_role=target_role or "Not specified — optimize for general senior technical roles",
        job_description=job_description or "Not provided",
        style=style,
        missing_keywords=", ".join(missing_keywords) if missing_keywords else "None identified",
    )

    raw, tokens = _call_llm(prompt)
    data = _safe_parse(raw)

    if not data:
        raise ValueError("AI returned empty response. Check your API key and try again.")

    return _map_to_resume_data(data), tokens


def _map_to_resume_data(data: dict) -> ResumeData:
    """Map raw LLM JSON → ResumeData dataclass."""
    contact_raw = data.get("contact", {})
    contact = ContactInfo(
        email=contact_raw.get("email", ""),
        phone=contact_raw.get("phone", ""),
        location=contact_raw.get("location", ""),
        linkedin=contact_raw.get("linkedin", ""),
        github=contact_raw.get("github", ""),
        portfolio=contact_raw.get("portfolio", ""),
    )

    experience = [
        Experience(
            company=e.get("company", ""),
            title=e.get("title", ""),
            location=e.get("location", ""),
            start_date=e.get("start_date", ""),
            end_date=e.get("end_date", ""),
            bullets=e.get("bullets", []),
        )
        for e in data.get("experience", [])
    ]

    projects = [
        Project(
            name=p.get("name", ""),
            role=p.get("role", ""),
            period=p.get("period", ""),
            url=p.get("url", ""),
            technologies=p.get("technologies", ""),
            description=p.get("description", ""),
        )
        for p in data.get("projects", [])
    ]

    pocs = [
        POC(name=p.get("name", ""), description=p.get("description", ""))
        for p in data.get("pocs", [])
    ]

    education = [
        Education(
            degree=e.get("degree", ""),
            field=e.get("field", ""),
            institution=e.get("institution", ""),
            year=e.get("year", ""),
        )
        for e in data.get("education", [])
    ]

    return ResumeData(
        name=data.get("name", ""),
        title=data.get("title", ""),
        contact=contact,
        summary=data.get("summary", ""),
        skills=data.get("skills", {}),
        experience=experience,
        projects=projects,
        pocs=pocs,
        education=education,
        certifications=data.get("certifications", []),
        publications=data.get("publications", []),
    )

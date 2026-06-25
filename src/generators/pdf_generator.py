"""
src/generators/pdf_generator.py
---------------------------------
Generate a PDF resume using ReportLab — clean, ATS-parseable layout.
No columns, no images, no text boxes.
"""
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, ListFlowable, ListItem
)
from reportlab.platypus import KeepTogether

from src.optimizer.rewriter import ResumeData

NAVY  = HexColor("#1F456E")
DARK  = HexColor("#222222")
MID   = HexColor("#555555")
LIGHT = HexColor("#E8EEF4")

PAGE_W, PAGE_H = A4
MARGIN = 1.8 * cm


def generate_pdf(resume: ResumeData, output_path: str | Path) -> Path:
    """
    Generate an ATS-friendly PDF.

    Args:
        resume:      Structured resume data.
        output_path: Where to save the .pdf file.

    Returns:
        Path to the generated file.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    styles = _build_styles()
    story = []

    _header(story, resume, styles)
    _summary(story, resume.summary, styles)
    _skills(story, resume.skills, styles)
    _experience(story, resume.experience, styles)
    _projects(story, resume.projects, styles)
    if resume.pocs:
        _pocs(story, resume.pocs, styles)
    _education(story, resume.education, styles)
    if resume.certifications:
        _simple_list(story, "Certifications", resume.certifications, styles)
    if resume.publications:
        _simple_list(story, "Publications", resume.publications, styles)

    doc.build(story)
    return out


# ── Section builders ──────────────────────────────────────────────────────────

def _header(story, resume: ResumeData, styles):
    story.append(Paragraph(resume.name.upper(), styles["Name"]))
    if resume.title:
        story.append(Paragraph(resume.title, styles["Title"]))
    story.append(Spacer(1, 4))

    c = resume.contact
    parts = " | ".join(x for x in [c.location, c.phone, c.email] if x)
    links = " | ".join(x for x in [c.portfolio, c.linkedin, c.github] if x)
    if parts:
        story.append(Paragraph(parts, styles["ContactLine"]))
    if links:
        story.append(Paragraph(links, styles["ContactLine"]))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=NAVY))
    story.append(Spacer(1, 6))


def _summary(story, summary: str, styles):
    if not summary:
        return
    story.append(Paragraph("PROFESSIONAL SUMMARY", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=NAVY))
    story.append(Spacer(1, 4))
    story.append(Paragraph(summary, styles["Body"]))
    story.append(Spacer(1, 8))


def _skills(story, skills: dict, styles):
    if not skills:
        return
    story.append(Paragraph("CORE TECHNICAL SKILLS", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=NAVY))
    story.append(Spacer(1, 4))
    for cat, items in skills.items():
        line = f"<b>{cat}:</b> {', '.join(items)}"
        story.append(Paragraph(line, styles["Body"]))
        story.append(Spacer(1, 2))
    story.append(Spacer(1, 6))


def _experience(story, experience: list, styles):
    if not experience:
        return
    story.append(Paragraph("PROFESSIONAL EXPERIENCE", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=NAVY))
    story.append(Spacer(1, 4))

    for exp in experience:
        dates = f"{exp.start_date} – {exp.end_date}".strip(" –")
        co_line = f"<b><font color='#1F456E'>{exp.company}</font></b>   |   <font color='#555555'>{dates}</font>"
        story.append(Paragraph(co_line, styles["CompanyLine"]))
        tl_line = f"<b>{exp.title}</b>"
        if exp.location:
            tl_line += f"  ·  <font color='#555555'>{exp.location}</font>"
        story.append(Paragraph(tl_line, styles["SubHeading"]))
        for bullet in exp.bullets:
            story.append(Paragraph(f"• {bullet}", styles["Bullet"]))
        story.append(Spacer(1, 6))


def _projects(story, projects: list, styles):
    if not projects:
        return
    story.append(Paragraph("TECHNICAL PROJECT PORTFOLIO", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=NAVY))
    story.append(Spacer(1, 4))

    for proj in projects:
        header = f"<b><font color='#1F456E'>{proj.name}</font></b>"
        if proj.role:
            header += f"  |  {proj.role}"
        if proj.period:
            header += f"  |  <font color='#555555'>{proj.period}</font>"
        story.append(Paragraph(header, styles["CompanyLine"]))
        if proj.url:
            story.append(Paragraph(f"<i>Live: {proj.url}</i>", styles["Small"]))
        if proj.technologies:
            story.append(Paragraph(f"<b>Technologies:</b> {proj.technologies}", styles["Small"]))
        if proj.description:
            story.append(Paragraph(proj.description, styles["Body"]))
        story.append(Spacer(1, 5))


def _pocs(story, pocs: list, styles):
    story.append(Paragraph("PROOF OF CONCEPTS (POCs) & R&D", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=NAVY))
    story.append(Spacer(1, 4))
    for poc in pocs:
        story.append(Paragraph(f"<b><font color='#1F456E'>{poc.name}</font></b>", styles["CompanyLine"]))
        if poc.description:
            story.append(Paragraph(poc.description, styles["Body"]))
        story.append(Spacer(1, 5))


def _education(story, education: list, styles):
    if not education:
        return
    story.append(Paragraph("EDUCATION", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=NAVY))
    story.append(Spacer(1, 4))
    for edu in education:
        degree = f"{edu.degree}" + (f" in {edu.field}" if edu.field else "")
        line = f"<b>{degree}</b>"
        if edu.institution:
            line += f"  –  {edu.institution}"
        if edu.year:
            line += f"  |  <font color='#555555'>{edu.year}</font>"
        story.append(Paragraph(line, styles["Body"]))
        story.append(Spacer(1, 2))
    story.append(Spacer(1, 6))


def _simple_list(story, title: str, items: list, styles):
    story.append(Paragraph(title.upper(), styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=NAVY))
    story.append(Spacer(1, 4))
    for item in items:
        story.append(Paragraph(f"• {item}", styles["Bullet"]))
    story.append(Spacer(1, 6))


# ── Style sheet ───────────────────────────────────────────────────────────────

def _build_styles() -> dict:
    base = getSampleStyleSheet()

    def S(name, **kwargs):
        return ParagraphStyle(name, parent=base["Normal"], **kwargs)

    return {
        "Name": S("Name", fontSize=18, fontName="Helvetica-Bold",
                  textColor=NAVY, alignment=TA_CENTER, spaceAfter=2),
        "Title": S("Title", fontSize=11, fontName="Helvetica-Bold",
                   textColor=MID, alignment=TA_CENTER, spaceAfter=2),
        "ContactLine": S("ContactLine", fontSize=9, textColor=DARK,
                         alignment=TA_CENTER, spaceAfter=1),
        "SectionHeading": S("SectionHeading", fontSize=11, fontName="Helvetica-Bold",
                             textColor=NAVY, spaceBefore=8, spaceAfter=2),
        "CompanyLine": S("CompanyLine", fontSize=10.5, fontName="Helvetica-Bold",
                         spaceBefore=4, spaceAfter=1),
        "SubHeading": S("SubHeading", fontSize=10, spaceBefore=0, spaceAfter=2),
        "Body": S("Body", fontSize=10, textColor=DARK, leading=14,
                  alignment=TA_JUSTIFY, spaceAfter=2),
        "Bullet": S("Bullet", fontSize=10, textColor=DARK, leading=14,
                    leftIndent=12, spaceAfter=2),
        "Small": S("Small", fontSize=9, textColor=MID, spaceAfter=1),
    }

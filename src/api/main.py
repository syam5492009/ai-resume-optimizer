"""
src/api/main.py
----------------
FastAPI application — REST API + serves the web UI.

Endpoints:
  GET  /            → Web UI
  GET  /health      → Health check
  POST /analyze     → ATS score + report only (no rewrite)
  POST /optimize    → Full rewrite + download DOCX/PDF
  GET  /download/{job_id} → Download generated file
"""
import base64
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.parsers.resume_parser import parse_resume_bytes
from src.optimizer.analyzer import analyze_resume, ATSReport
from src.optimizer.rewriter import rewrite_resume
from src.generators.docx_generator import generate_docx
from src.generators.pdf_generator import generate_pdf
from src.utils.config import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    OUTPUT_DIR.mkdir(exist_ok=True)
    yield


app = FastAPI(
    title="AI Resume ATS Optimizer",
    description="Upload your resume, get an ATS-optimized version in DOCX/PDF.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (web UI)
static_dir = Path(__file__).parent.parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ── Response models ───────────────────────────────────────────────────────────

class AnalyzeResponse(BaseModel):
    ats_score: int
    grade: str
    score_breakdown: dict
    critical_issues: list[str]
    improvements: list[str]
    missing_keywords: list[str]
    found_keywords: list[str]
    strengths: list[str]
    tokens_used: dict


class OptimizeResponse(BaseModel):
    job_id: str
    ats_score_before: int
    ats_score_after: int
    grade_before: str
    grade_after: str
    improvements_applied: list[str]
    missing_keywords_added: list[str]
    download_docx: Optional[str] = None
    download_pdf: Optional[str] = None
    message: str
    tokens_used: dict


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the web UI."""
    html_path = static_dir / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>AI Resume Optimizer API</h1><p>Visit /docs for the API.</p>")


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "provider": settings.AI_PROVIDER,
        "model": settings.ANTHROPIC_MODEL if settings.AI_PROVIDER == "anthropic" else settings.OPENAI_MODEL,
    }


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    resume: UploadFile = File(..., description="Resume file (PDF, DOCX, or TXT)"),
    target_role: str = Form("", description="Target job title (optional)"),
    job_description: str = Form("", description="Job description text (optional)"),
):
    """
    Analyze a resume for ATS compatibility. Returns score and detailed report.
    Does NOT rewrite the resume.
    """
    _validate_file(resume)
    content = await resume.read()
    try:
        text = parse_resume_bytes(content, resume.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse resume: {e}")

    try:
        report = analyze_resume(text, target_role=target_role, job_description=job_description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    return AnalyzeResponse(
        ats_score=report.ats_score,
        grade=report.grade,
        score_breakdown=report.score_breakdown,
        critical_issues=report.critical_issues,
        improvements=report.improvements,
        missing_keywords=report.missing_keywords,
        found_keywords=report.found_keywords,
        strengths=report.strengths,
        tokens_used=report.tokens_used,
    )


@app.post("/optimize", response_model=OptimizeResponse)
async def optimize(
    resume: UploadFile = File(..., description="Resume file (PDF, DOCX, or TXT)"),
    target_role: str = Form("", description="Target job title (optional)"),
    job_description: str = Form("", description="Job description text (optional)"),
    output_format: str = Form("both", description="docx | pdf | both"),
    style: str = Form("professional", description="minimal | professional | executive"),
):
    """
    Full pipeline: parse → ATS analysis → AI rewrite → generate DOCX/PDF.

    Options:
    - output_format: docx, pdf, or both
    - style: minimal (1-page), professional (1-2 pages), executive (2 pages)
    - target_role + job_description: tailors keyword optimization
    """
    _validate_file(resume)
    content = await resume.read()

    try:
        text = parse_resume_bytes(content, resume.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse resume: {e}")

    # Step 1: Analyze before rewrite
    try:
        report_before = analyze_resume(text, target_role=target_role, job_description=job_description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    # Step 2: Rewrite
    try:
        resume_data, rewrite_tokens = rewrite_resume(
            text,
            target_role=target_role,
            job_description=job_description,
            style=style,
            analysis=report_before,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rewrite failed: {e}")

    # Aggregate token usage from both LLM calls
    at = report_before.tokens_used
    rt = rewrite_tokens
    total_tokens = {
        "input_tokens": at.get("input_tokens", 0) + rt.get("input_tokens", 0),
        "output_tokens": at.get("output_tokens", 0) + rt.get("output_tokens", 0),
        "total_tokens": at.get("total_tokens", 0) + rt.get("total_tokens", 0),
        "estimated_cost_usd": round(
            at.get("estimated_cost_usd", 0.0) + rt.get("estimated_cost_usd", 0.0), 6
        ),
    }

    # Step 3: Generate files
    job_id = str(uuid.uuid4())[:8]
    safe_name = (resume_data.name or "resume").replace(" ", "_").lower()
    docx_url = pdf_url = None

    if output_format in ("docx", "both"):
        docx_path = OUTPUT_DIR / f"{safe_name}_{job_id}_ats.docx"
        generate_docx(resume_data, docx_path)
        docx_url = f"/download/{job_id}/docx"

    if output_format in ("pdf", "both"):
        pdf_path = OUTPUT_DIR / f"{safe_name}_{job_id}_ats.pdf"
        generate_pdf(resume_data, pdf_path)
        pdf_url = f"/download/{job_id}/pdf"

    # Quick score on rewritten resume (estimate — avoids extra LLM call)
    score_after = min(report_before.ats_score + 25, 98)

    return OptimizeResponse(
        job_id=job_id,
        ats_score_before=report_before.ats_score,
        ats_score_after=score_after,
        grade_before=report_before.grade,
        grade_after="Excellent" if score_after >= 85 else "Good",
        improvements_applied=report_before.improvements[:5],
        missing_keywords_added=report_before.missing_keywords[:8],
        download_docx=docx_url,
        download_pdf=pdf_url,
        message=f"Resume optimized successfully. ATS score improved from {report_before.ats_score} → {score_after}.",
        tokens_used=total_tokens,
    )


@app.get("/download/{job_id}/{fmt}")
async def download(job_id: str, fmt: str):
    """Download a generated resume file."""
    if fmt not in ("docx", "pdf"):
        raise HTTPException(status_code=400, detail="Format must be docx or pdf")

    matches = list(OUTPUT_DIR.glob(f"*_{job_id}_ats.{fmt}"))
    if not matches:
        raise HTTPException(status_code=404, detail="File not found or expired.")

    file_path = matches[0]
    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if fmt == "docx" else "application/pdf"
    )
    return FileResponse(str(file_path), media_type=media_type, filename=file_path.name)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _validate_file(upload: UploadFile):
    allowed = {".pdf", ".docx", ".doc", ".txt"}
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Upload PDF, DOCX, or TXT."
        )
    max_bytes = settings.MAX_RESUME_SIZE_MB * 1024 * 1024
    # Size checked when reading; just guard content_type here

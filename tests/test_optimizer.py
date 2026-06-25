"""
tests/test_optimizer.py
-----------------------
Unit tests for the ai-resume-optimizer project.
Mocks all LLM calls — no real API keys required.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ── Parser tests ──────────────────────────────────────────────────────────────

class TestResumeParser:
    def test_parse_txt(self, tmp_path):
        from src.parsers.resume_parser import parse_resume, parse_resume_bytes
        f = tmp_path / "resume.txt"
        f.write_text("John Doe\nSoftware Engineer\nPython, FastAPI")
        result = parse_resume(f)
        assert "John Doe" in result
        assert "Software Engineer" in result

    def test_parse_bytes_txt(self):
        from src.parsers.resume_parser import parse_resume_bytes
        content = b"Jane Smith\nData Scientist\nPython, ML"
        result = parse_resume_bytes(content, "resume.txt")
        assert "Jane Smith" in result
        assert "Data Scientist" in result

    def test_parse_unsupported_extension(self, tmp_path):
        from src.parsers.resume_parser import parse_resume
        f = tmp_path / "resume.rtf"
        f.write_text("some content")
        result = parse_resume(f)
        assert result == "" or isinstance(result, str)

    def test_parse_resume_bytes_unknown_ext(self):
        from src.parsers.resume_parser import parse_resume_bytes
        result = parse_resume_bytes(b"hello", "file.xyz")
        assert isinstance(result, str)

    def test_empty_txt_file(self, tmp_path):
        from src.parsers.resume_parser import parse_resume
        f = tmp_path / "empty.txt"
        f.write_bytes(b"")
        result = parse_resume(f)
        assert result == ""


# ── Analyzer tests ────────────────────────────────────────────────────────────

MOCK_ANALYSIS_JSON = json.dumps({
    "ats_score": 72,
    "score_breakdown": {"keyword_match": 70.0, "formatting": 80.0},
    "critical_issues": ["Missing measurable achievements"],
    "improvements": ["Add quantified metrics to bullets"],
    "missing_keywords": ["Docker", "Kubernetes"],
    "found_keywords": ["Python", "FastAPI"],
    "strengths": ["Strong technical skills section"],
    "parsed_sections": {},
})

MOCK_SCORE_JSON = json.dumps({"score": 72, "one_line_verdict": "Decent resume"})


class TestATSAnalyzer:
    def _make_mock_response(self, text):
        mock = MagicMock()
        mock.content[0].text = text
        mock.usage.input_tokens = 100
        mock.usage.output_tokens = 50
        return mock

    def test_analyze_returns_report_anthropic(self):
        from src.optimizer.analyzer import analyze_resume, ATSReport
        with patch("anthropic.Anthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create.return_value = self._make_mock_response(MOCK_ANALYSIS_JSON)
            with patch("src.optimizer.analyzer.settings") as mock_settings:
                mock_settings.AI_PROVIDER = "anthropic"
                mock_settings.ANTHROPIC_API_KEY = "test-key"
                mock_settings.ANTHROPIC_MODEL = "claude-test"
                report = analyze_resume("Some resume text", target_role="Engineer")
        assert isinstance(report, ATSReport)
        assert report.ats_score == 72
        assert report.tokens_used["input_tokens"] == 100
        assert report.tokens_used["output_tokens"] == 50
        assert report.tokens_used["total_tokens"] == 150

    def test_analyze_returns_report_openai(self):
        from src.optimizer.analyzer import analyze_resume, ATSReport
        mock_choice = MagicMock()
        mock_choice.message.content = MOCK_ANALYSIS_JSON
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]
        mock_resp.usage.prompt_tokens = 200
        mock_resp.usage.completion_tokens = 80
        with patch("openai.OpenAI") as MockClient:
            instance = MockClient.return_value
            instance.chat.completions.create.return_value = mock_resp
            with patch("src.optimizer.analyzer.settings") as mock_settings:
                mock_settings.AI_PROVIDER = "openai"
                mock_settings.OPENAI_API_KEY = "test-key"
                mock_settings.OPENAI_MODEL = "gpt-test"
                report = analyze_resume("Some resume text")
        assert isinstance(report, ATSReport)
        assert report.ats_score == 72
        assert report.tokens_used["input_tokens"] == 200
        assert report.tokens_used["output_tokens"] == 80

    def test_ats_report_grade_excellent(self):
        from src.optimizer.analyzer import ATSReport
        r = ATSReport(ats_score=90, score_breakdown={}, critical_issues=[],
                      improvements=[], missing_keywords=[], found_keywords=[], strengths=[])
        assert r.grade == "Excellent"

    def test_ats_report_grade_good(self):
        from src.optimizer.analyzer import ATSReport
        r = ATSReport(ats_score=75, score_breakdown={}, critical_issues=[],
                      improvements=[], missing_keywords=[], found_keywords=[], strengths=[])
        assert r.grade == "Good"

    def test_ats_report_grade_needs_work(self):
        from src.optimizer.analyzer import ATSReport
        r = ATSReport(ats_score=55, score_breakdown={}, critical_issues=[],
                      improvements=[], missing_keywords=[], found_keywords=[], strengths=[])
        assert r.grade == "Needs Work"

    def test_ats_report_grade_poor(self):
        from src.optimizer.analyzer import ATSReport
        r = ATSReport(ats_score=35, score_breakdown={}, critical_issues=[],
                      improvements=[], missing_keywords=[], found_keywords=[], strengths=[])
        assert r.grade == "Poor"

    def test_safe_parse_strips_markdown(self):
        from src.optimizer.analyzer import ATSAnalyzer
        a = ATSAnalyzer.__new__(ATSAnalyzer)
        raw = f"```json\n{MOCK_ANALYSIS_JSON}\n```"
        result = a._safe_parse(raw)
        assert result["ats_score"] == 72

    def test_safe_parse_plain_json(self):
        from src.optimizer.analyzer import ATSAnalyzer
        a = ATSAnalyzer.__new__(ATSAnalyzer)
        result = a._safe_parse(MOCK_ANALYSIS_JSON)
        assert result["missing_keywords"] == ["Docker", "Kubernetes"]

    def test_safe_parse_returns_empty_on_bad_json(self):
        from src.optimizer.analyzer import ATSAnalyzer
        a = ATSAnalyzer.__new__(ATSAnalyzer)
        result = a._safe_parse("not json at all")
        assert result == {}


# ── Rewriter tests ────────────────────────────────────────────────────────────

MOCK_REWRITE_JSON = json.dumps({
    "name": "Jane Smith",
    "title": "Senior Software Engineer",
    "contact": {
        "email": "jane@example.com",
        "phone": "+1-555-1234",
        "location": "New York, NY",
        "linkedin": "linkedin.com/in/janesmith",
        "github": "github.com/janesmith",
        "portfolio": "",
    },
    "summary": "Results-driven engineer with 5+ years of experience.",
    "skills": {
        "Programming Languages": ["Python", "Go", "TypeScript"],
        "Frameworks": ["FastAPI", "React"],
    },
    "experience": [
        {
            "company": "Acme Corp",
            "title": "Software Engineer",
            "location": "Remote",
            "start_date": "2021-01",
            "end_date": "Present",
            "bullets": ["Reduced latency by 40%", "Led team of 5 engineers"],
        }
    ],
    "projects": [
        {
            "name": "AI Chatbot",
            "role": "Lead Developer",
            "period": "2023",
            "description": "Built production chatbot serving 10k users.",
            "technologies": "Python, LangChain, OpenAI",
            "url": "github.com/janesmith/chatbot",
        }
    ],
    "pocs": [],
    "education": [
        {"degree": "B.Tech", "field": "Computer Science", "institution": "MIT", "year": "2020"}
    ],
    "certifications": ["AWS Solutions Architect"],
    "publications": [],
})


class TestResumeRewriter:
    def _make_anthropic_mock(self, text):
        mock = MagicMock()
        mock.content[0].text = text
        mock.usage.input_tokens = 300
        mock.usage.output_tokens = 120
        return mock

    def test_rewrite_returns_resume_data(self):
        from src.optimizer.rewriter import rewrite_resume, ResumeData
        with patch("anthropic.Anthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create.return_value = self._make_anthropic_mock(MOCK_REWRITE_JSON)
            with patch("src.optimizer.rewriter.settings") as mock_settings:
                mock_settings.AI_PROVIDER = "anthropic"
                mock_settings.ANTHROPIC_API_KEY = "test-key"
                mock_settings.ANTHROPIC_MODEL = "claude-test"
                result, tokens = rewrite_resume("old resume text", target_role="Engineer")
        assert isinstance(result, ResumeData)
        assert result.name == "Jane Smith"
        assert result.title == "Senior Software Engineer"
        assert tokens["input_tokens"] == 300
        assert tokens["output_tokens"] == 120
        assert tokens["total_tokens"] == 420

    def test_rewrite_maps_experience_bullets(self):
        from src.optimizer.rewriter import rewrite_resume, ResumeData
        with patch("anthropic.Anthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create.return_value = self._make_anthropic_mock(MOCK_REWRITE_JSON)
            with patch("src.optimizer.rewriter.settings") as mock_settings:
                mock_settings.AI_PROVIDER = "anthropic"
                mock_settings.ANTHROPIC_API_KEY = "test-key"
                mock_settings.ANTHROPIC_MODEL = "claude-test"
                result, _ = rewrite_resume("old resume text")
        assert len(result.experience) == 1
        assert "Reduced latency by 40%" in result.experience[0].bullets

    def test_rewrite_maps_skills(self):
        from src.optimizer.rewriter import rewrite_resume
        with patch("anthropic.Anthropic") as MockClient:
            instance = MockClient.return_value
            instance.messages.create.return_value = self._make_anthropic_mock(MOCK_REWRITE_JSON)
            with patch("src.optimizer.rewriter.settings") as mock_settings:
                mock_settings.AI_PROVIDER = "anthropic"
                mock_settings.ANTHROPIC_API_KEY = "test-key"
                mock_settings.ANTHROPIC_MODEL = "claude-test"
                result, _ = rewrite_resume("old resume text")
        assert "Programming Languages" in result.skills
        assert "Python" in result.skills["Programming Languages"]


# ── Generator tests ───────────────────────────────────────────────────────────

def _make_resume_data():
    from src.optimizer.rewriter import (
        ResumeData, ContactInfo, Experience, Project, Education
    )
    return ResumeData(
        name="John Doe",
        title="ML Engineer",
        contact=ContactInfo(
            email="john@example.com",
            phone="+1-555-9999",
            location="San Francisco, CA",
            linkedin="linkedin.com/in/johndoe",
            github="github.com/johndoe",
            portfolio="johndoe.dev",
        ),
        summary="Experienced ML Engineer with expertise in LLMs and RAG systems.",
        skills={"AI/ML": ["Python", "TensorFlow", "PyTorch"], "Cloud": ["AWS", "GCP"]},
        experience=[
            Experience(
                company="TechCorp",
                title="Senior ML Engineer",
                location="Remote",
                start_date="2022-01",
                end_date="Present",
                bullets=["Built RAG pipeline serving 100k queries/day", "Reduced model latency by 35%"],
            )
        ],
        projects=[
            Project(
                name="Enterprise RAG Agent",
                role="Lead Engineer",
                period="2024",
                description="Multi-agent LLM system with hybrid retrieval.",
                technologies="Python, LangChain, Qdrant, FastAPI",
                url="github.com/johndoe/rag-agent",
            )
        ],
        pocs=[],
        education=[Education(degree="B.Tech", field="CS", institution="IIT", year="2019")],
        certifications=["AWS ML Specialty", "Google Cloud Professional ML Engineer"],
        publications=[],
    )


class TestDOCXGenerator:
    def test_generates_docx_file(self, tmp_path):
        from src.generators.docx_generator import generate_docx
        resume = _make_resume_data()
        out = tmp_path / "test_resume.docx"
        result = generate_docx(resume, out)
        assert result.exists()
        assert result.suffix == ".docx"
        assert result.stat().st_size > 1000

    def test_docx_contains_name(self, tmp_path):
        from src.generators.docx_generator import generate_docx
        from docx import Document
        resume = _make_resume_data()
        out = tmp_path / "test_resume.docx"
        generate_docx(resume, out)
        doc = Document(str(out))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "JOHN DOE" in full_text

    def test_docx_creates_parent_dirs(self, tmp_path):
        from src.generators.docx_generator import generate_docx
        resume = _make_resume_data()
        out = tmp_path / "nested" / "dir" / "resume.docx"
        generate_docx(resume, out)
        assert out.exists()


class TestPDFGenerator:
    def test_generates_pdf_file(self, tmp_path):
        from src.generators.pdf_generator import generate_pdf
        resume = _make_resume_data()
        out = tmp_path / "test_resume.pdf"
        result = generate_pdf(resume, out)
        assert result.exists()
        assert result.suffix == ".pdf"
        assert result.stat().st_size > 1000

    def test_pdf_header_magic_bytes(self, tmp_path):
        from src.generators.pdf_generator import generate_pdf
        resume = _make_resume_data()
        out = tmp_path / "test_resume.pdf"
        generate_pdf(resume, out)
        magic = out.read_bytes()[:4]
        assert magic == b"%PDF"

    def test_pdf_creates_parent_dirs(self, tmp_path):
        from src.generators.pdf_generator import generate_pdf
        resume = _make_resume_data()
        out = tmp_path / "a" / "b" / "resume.pdf"
        generate_pdf(resume, out)
        assert out.exists()


# ── API tests ─────────────────────────────────────────────────────────────────

class TestAPI:
    def test_health_endpoint(self):
        from fastapi.testclient import TestClient
        from src.api.main import app
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "provider" in data
        assert "model" in data

    def test_root_returns_html(self):
        from fastapi.testclient import TestClient
        from src.api.main import app
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_analyze_rejects_wrong_filetype(self):
        from fastapi.testclient import TestClient
        from src.api.main import app
        client = TestClient(app)
        resp = client.post(
            "/analyze",
            files={"resume": ("resume.xlsx", b"fake", "application/octet-stream")},
            data={"target_role": "", "job_description": ""},
        )
        assert resp.status_code == 400

    def test_download_missing_job(self):
        from fastapi.testclient import TestClient
        from src.api.main import app
        client = TestClient(app)
        resp = client.get("/download/nonexistent123/pdf")
        assert resp.status_code == 404

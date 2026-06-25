# AI Resume Optimizer

> Upload your resume → get an ATS-optimized DOCX + PDF back in seconds.

Powered by **Claude (Anthropic)** or **GPT-4o-mini (OpenAI)** — your choice.  
Works as a **web app**, a **REST API**, or a **CLI tool**.

---

## Features

| Feature | Details |
|---|---|
| **ATS Score** | Rates your resume 0–100 with breakdown (keywords, formatting, sections…) |
| **AI Rewrite** | Full resume rewritten — STAR bullets, quantified achievements, ATS keywords |
| **DOCX output** | ATS-safe Word document: Calibri font, no tables, proper heading styles |
| **PDF output** | Clean PDF via ReportLab: same ATS rules, navy-accent professional design |
| **Multi-provider** | Switch between Anthropic Claude and OpenAI GPT from UI or CLI |
| **Style options** | `minimal` (1-page), `professional` (1–2 pages), `executive` (2 pages) |
| **Target role** | Tailor keyword density to a specific job title |
| **JD matching** | Paste a job description — missing keywords are injected into the rewrite |

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/syam5492009/ai-resume-optimizer.git
cd ai-resume-optimizer

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY or OPENAI_API_KEY
```

### 3. Run the web app

```bash
uvicorn src.api.main:app --reload
```

Open **http://localhost:8000** — drag-and-drop your resume and get results.

---

## Web UI

The web UI is a single-page app at `http://localhost:8000`:

1. **Drag & drop** your PDF, DOCX, or TXT resume
2. Optionally enter a **target role** and paste a **job description**
3. Pick **output format** (DOCX / PDF / Both) and **style**
4. Choose your **AI provider** (Anthropic or OpenAI)
5. Click **Optimize** — the UI shows:
   - Before / after ATS score
   - Keywords added, critical issues fixed
   - Download buttons for DOCX and PDF

---

## CLI

```bash
# Basic usage
python scripts/optimize.py my_resume.pdf

# With options
python scripts/optimize.py my_resume.pdf \
  --role "Senior AI Engineer" \
  --format pdf \
  --style professional \
  --provider anthropic

# Just get the ATS score (no rewrite)
python scripts/optimize.py my_resume.pdf --score-only

# Use a job description file
python scripts/optimize.py my_resume.docx --jd job_description.txt

# Specify output directory
python scripts/optimize.py my_resume.pdf --output-dir ./optimized
```

### CLI options

| Option | Values | Default | Description |
|---|---|---|---|
| `resume` | path | — | Resume file (PDF, DOCX, TXT) |
| `--role` / `-r` | text | "" | Target job title |
| `--jd` | path | "" | Path to job description .txt file |
| `--format` / `-f` | `docx` `pdf` `both` | `both` | Output format |
| `--style` / `-s` | `minimal` `professional` `executive` | `professional` | Page style |
| `--provider` | `anthropic` `openai` | from `.env` | Override AI provider |
| `--score-only` | flag | off | Only score, no rewrite |
| `--output-dir` / `-o` | path | `outputs/` | Where to save generated files |

---

## REST API

### `POST /analyze`
ATS analysis only — no rewrite.

```bash
curl -X POST http://localhost:8000/analyze \
  -F "resume=@my_resume.pdf" \
  -F "target_role=Software Engineer" \
  -F "job_description=We need Python, Docker, Kubernetes..."
```

**Response:**
```json
{
  "ats_score": 68,
  "grade": "Needs Work",
  "score_breakdown": {"keyword_match": 65, "formatting": 80, ...},
  "critical_issues": ["Missing quantified achievements"],
  "improvements": ["Add metrics to bullets", "Include Docker in skills"],
  "missing_keywords": ["Docker", "Kubernetes", "CI/CD"],
  "found_keywords": ["Python", "FastAPI", "PostgreSQL"],
  "strengths": ["Strong technical skills section"]
}
```

### `POST /optimize`
Full pipeline: analyze → rewrite → generate files.

```bash
curl -X POST http://localhost:8000/optimize \
  -F "resume=@my_resume.pdf" \
  -F "target_role=Senior AI Engineer" \
  -F "output_format=both" \
  -F "style=professional"
```

**Response:**
```json
{
  "job_id": "a3f8c012",
  "ats_score_before": 68,
  "ats_score_after": 93,
  "grade_before": "Needs Work",
  "grade_after": "Excellent",
  "improvements_applied": ["Added metrics to all bullets", ...],
  "missing_keywords_added": ["Docker", "Kubernetes", ...],
  "download_docx": "/download/a3f8c012/docx",
  "download_pdf": "/download/a3f8c012/pdf",
  "message": "Resume optimized successfully."
}
```

### `GET /download/{job_id}/{fmt}`
Download a generated file (`fmt`: `docx` or `pdf`).

### `GET /health`
Check API status and configured provider.

---

## Project Structure

```
ai-resume-optimizer/
├── src/
│   ├── api/
│   │   └── main.py              # FastAPI app + endpoints
│   ├── generators/
│   │   ├── docx_generator.py    # ATS-safe Word document generator
│   │   └── pdf_generator.py     # PDF generator (ReportLab)
│   ├── optimizer/
│   │   ├── analyzer.py          # ATS scoring + ATSReport
│   │   ├── prompts.py           # LLM prompt templates
│   │   └── rewriter.py          # AI resume rewrite + ResumeData model
│   ├── parsers/
│   │   └── resume_parser.py     # PDF/DOCX/TXT parser
│   └── utils/
│       └── config.py            # Settings (pydantic-settings)
├── scripts/
│   └── optimize.py              # CLI tool (argparse)
├── static/
│   └── index.html               # Single-page web UI
├── tests/
│   └── test_optimizer.py        # Unit tests (pytest, mocked LLM)
├── .env.example                 # Config template
├── requirements.txt
└── README.md
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `AI_PROVIDER` | yes | `anthropic` | `anthropic` or `openai` |
| `ANTHROPIC_API_KEY` | if anthropic | — | From console.anthropic.com |
| `ANTHROPIC_MODEL` | no | `claude-sonnet-4-6` | Claude model ID |
| `OPENAI_API_KEY` | if openai | — | From platform.openai.com |
| `OPENAI_MODEL` | no | `gpt-4o-mini` | OpenAI model ID |
| `OUTPUT_DIR` | no | `outputs` | Generated file directory |
| `MAX_RESUME_SIZE_MB` | no | `5` | Upload size limit |

---

## ATS Rules Applied

The generated DOCX and PDF follow strict ATS-compatibility rules:

- **No tables or text boxes** — parsers skip content inside tables
- **No multi-column layout** — single-column only
- **Standard fonts** — Calibri (DOCX), Helvetica (PDF)
- **Word heading styles** — not custom formatted text
- **Bullet lists** — proper Word list styles, not manual hyphens
- **No headers/footers** — content that may be skipped
- **No images or graphics**
- **Machine-readable contact info** — plain text, not fancy icons

---

## Tests

```bash
pytest tests/ -v
```

All tests mock LLM calls — no API key required for testing.

---

## Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feature/your-feature`
3. Add tests in `tests/test_optimizer.py`
4. Submit a pull request

---

## License

MIT — free for personal and commercial use.

---

Built by [Syama Sundara Rao](https://syamai.vercel.app/) | [LinkedIn](https://linkedin.com/in/syamsundar)

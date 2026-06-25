# AI Resume ATS Optimizer

> **Upload your resume → get an ATS-optimized DOCX + PDF back in under 30 seconds.**

Powered by **Claude (Anthropic)** or **GPT-4o-mini (OpenAI)** — your choice.  
Runs as a **web app**, **REST API**, or **CLI**. Every call reports real token counts and estimated cost.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)
![Claude](https://img.shields.io/badge/AI-Claude%20%7C%20GPT--4o-8B5CF6?logo=anthropic&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-F59E0B)

---

## How It Works

```
Resume (PDF / DOCX / TXT)
         │
         ▼
  ┌─────────────┐     ┌─────────────────────┐     ┌──────────────────────┐
  │   Parser    │────▶│    ATS Analyzer      │────▶│     AI Rewriter      │
  │ pypdf/docx  │     │  0–100 score         │     │  STAR bullets        │
  └─────────────┘     │  keyword gap report  │     │  keyword injection   │
                      └─────────────────────┘     └──────────┬───────────┘
                                                             │
                           ┌─────────────────────────────────┤
                           ▼                                 ▼
                     ┌──────────┐                    ┌─────────────┐
                     │   DOCX   │                    │     PDF     │
                     │ Calibri  │                    │  ReportLab  │
                     │ ATS-safe │                    │  ATS-safe   │
                     └──────────┘                    └─────────────┘
```

Every `/analyze` and `/optimize` call returns **real token counts** and an **estimated USD cost** alongside the results.

---

## Features

| Feature | Details |
|---|---|
| **ATS Score** | 0–100 score with per-section breakdown — keywords, formatting, achievements, sections |
| **AI Rewrite** | Full resume rewritten with STAR bullets, quantified achievements, and injected keywords |
| **Token Usage** | Input / output token counts + estimated USD cost returned with every API call and shown in the UI |
| **DOCX output** | ATS-safe Word doc — Calibri font, no tables, proper Word heading styles |
| **PDF output** | Clean PDF via ReportLab — same ATS rules, navy-accent professional design |
| **Multi-provider** | Switch between Anthropic Claude and OpenAI GPT from the UI, API, or CLI |
| **Style options** | `minimal` (1 page), `professional` (1–2 pages), `executive` (2 pages) |
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
# Edit .env — set AI_PROVIDER and add your API key
```

### 3. Run the web app

```bash
uvicorn src.api.main:app --reload
```

Open **http://localhost:8000** — drag-and-drop your resume and get results instantly.

---

## Token Usage & Cost

Every `/analyze` and `/optimize` response includes a `tokens_used` field:

```json
{
  "tokens_used": {
    "input_tokens": 1842,
    "output_tokens": 612,
    "total_tokens": 2454,
    "estimated_cost_usd": 0.014706
  }
}
```

For the `/optimize` endpoint (analyze + rewrite = two LLM calls), tokens are aggregated into a single total.

### Pricing table

Costs are computed at response time using current model pricing:

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|---|---|---|
| `claude-sonnet-4-6` | $3.00 | $15.00 |
| `claude-opus-4-8` | $15.00 | $75.00 |
| `claude-haiku-4-5` | $0.80 | $4.00 |
| `gpt-4o-mini` | $0.15 | $0.60 |
| `gpt-4o` | $2.50 | $10.00 |

**Typical cost per resume optimization:**
- `gpt-4o-mini` — ~$0.001–$0.005
- `claude-sonnet-4-6` — ~$0.015–$0.040

The **Web UI** shows input tokens, output tokens, total tokens, and estimated cost in the results panel after every run.

---

## Web UI

The single-page app at **http://localhost:8000**:

1. **Drag & drop** your PDF, DOCX, or TXT resume
2. Optionally enter a **target role** and paste a **job description**
3. Pick **output format** (DOCX / PDF / Both) and **style**
4. Choose your **AI provider** (Anthropic Claude or OpenAI GPT)
5. Click **Optimize** — results show:
   - Before / after ATS score
   - Keywords added (green chips)
   - Improvements applied (checklist)
   - Download buttons for DOCX and PDF
   - **Token usage: input, output, total, and estimated cost**

---

## CLI

```bash
# Basic usage
python scripts/optimize.py my_resume.pdf

# Full options
python scripts/optimize.py my_resume.pdf \
  --role "Senior AI Engineer" \
  --format pdf \
  --style professional \
  --provider anthropic

# Score only (no rewrite)
python scripts/optimize.py my_resume.pdf --score-only

# With a job description file
python scripts/optimize.py my_resume.docx --jd job_description.txt

# Custom output directory
python scripts/optimize.py my_resume.pdf --output-dir ./optimized
```

The CLI prints a token usage summary at the end of each full optimization run:

```
  Token Usage:  3,866 in / 1,401 out / 5,267 total  (est. $0.0326 USD)
```

### CLI options

| Option | Values | Default | Description |
|---|---|---|---|
| `resume` | path | — | Resume file (PDF, DOCX, TXT) |
| `--role` / `-r` | text | `""` | Target job title |
| `--jd` | path | `""` | Path to job description .txt file |
| `--format` / `-f` | `docx` `pdf` `both` | `both` | Output format |
| `--style` / `-s` | `minimal` `professional` `executive` | `professional` | Page style |
| `--provider` | `anthropic` `openai` | from `.env` | Override AI provider |
| `--score-only` | flag | off | Score only — no rewrite |
| `--output-dir` / `-o` | path | `outputs/` | Where to save files |

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
  "score_breakdown": {
    "keyword_match": 65,
    "formatting": 80,
    "experience_quality": 70,
    "quantified_achievements": 55
  },
  "critical_issues": ["Missing quantified achievements"],
  "improvements": ["Add metrics to bullets", "Include Docker in skills"],
  "missing_keywords": ["Docker", "Kubernetes", "CI/CD"],
  "found_keywords": ["Python", "FastAPI", "PostgreSQL"],
  "strengths": ["Strong technical skills section"],
  "tokens_used": {
    "input_tokens": 1524,
    "output_tokens": 489,
    "total_tokens": 2013,
    "estimated_cost_usd": 0.011895
  }
}
```

---

### `POST /optimize`

Full pipeline: parse → analyze → rewrite → generate files.

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
  "improvements_applied": ["Added metrics to all bullets", "Injected 8 missing keywords"],
  "missing_keywords_added": ["Docker", "Kubernetes", "CI/CD", "MLOps"],
  "download_docx": "/download/a3f8c012/docx",
  "download_pdf": "/download/a3f8c012/pdf",
  "message": "Resume optimized successfully. ATS score improved from 68 → 93.",
  "tokens_used": {
    "input_tokens": 3866,
    "output_tokens": 1401,
    "total_tokens": 5267,
    "estimated_cost_usd": 0.032625
  }
}
```

---

### `GET /download/{job_id}/{fmt}`

Download a generated file. `fmt` must be `docx` or `pdf`.

### `GET /health`

Returns current provider and model.

```json
{ "status": "healthy", "provider": "openai", "model": "gpt-4o-mini" }
```

---

## Project Structure

```
ai-resume-optimizer/
├── src/
│   ├── api/
│   │   └── main.py              # FastAPI app + all endpoints
│   ├── generators/
│   │   ├── docx_generator.py    # ATS-safe Word document generator
│   │   └── pdf_generator.py     # PDF generator (ReportLab)
│   ├── optimizer/
│   │   ├── analyzer.py          # ATS scoring, token tracking, ATSReport
│   │   ├── prompts.py           # LLM prompt templates
│   │   └── rewriter.py          # AI resume rewrite, ResumeData model
│   ├── parsers/
│   │   └── resume_parser.py     # PDF / DOCX / TXT parser
│   └── utils/
│       └── config.py            # Pydantic settings from .env
├── scripts/
│   └── optimize.py              # CLI tool (argparse)
├── static/
│   └── index.html               # Single-page web UI
├── tests/
│   └── test_optimizer.py        # Unit tests — all LLM calls mocked
├── .env.example                 # Config template
├── requirements.txt
└── README.md
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `AI_PROVIDER` | yes | `anthropic` | `anthropic` or `openai` |
| `ANTHROPIC_API_KEY` | if anthropic | — | From [console.anthropic.com](https://console.anthropic.com) |
| `ANTHROPIC_MODEL` | no | `claude-sonnet-4-6` | Claude model ID |
| `OPENAI_API_KEY` | if openai | — | From [platform.openai.com](https://platform.openai.com) |
| `OPENAI_MODEL` | no | `gpt-4o-mini` | OpenAI model ID |
| `OUTPUT_DIR` | no | `outputs` | Directory for generated DOCX/PDF files |
| `MAX_RESUME_SIZE_MB` | no | `10` | Max upload size in MB |

---

## ATS Rules Applied

All generated DOCX and PDF files follow strict ATS-compatibility rules:

- **No tables or text boxes** — ATS parsers skip content inside tables
- **No multi-column layout** — single-column only
- **Standard fonts** — Calibri 10pt (DOCX), Helvetica (PDF)
- **Word heading styles** — proper `Heading 1/2`, not just bold text
- **Bullet lists** — Word list styles, not manual hyphens or dashes
- **No headers or footers** — content in those areas may be skipped
- **No images or graphics**
- **Plain-text contact info** — no icon fonts, no tables for layout

---

## Tests

```bash
pytest tests/ -v
```

All LLM calls are mocked — no API key required to run the test suite.

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

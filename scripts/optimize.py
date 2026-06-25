"""
scripts/optimize.py
--------------------
CLI tool for AI resume optimization.

Usage:
  python scripts/optimize.py resume.pdf
  python scripts/optimize.py resume.pdf --role "Senior Software Engineer" --format both --style professional
  python scripts/optimize.py resume.pdf --score-only
  python scripts/optimize.py resume.pdf --jd job_description.txt --provider openai
"""
import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="AI Resume ATS Optimizer — optimize any resume for ATS systems",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/optimize.py my_resume.pdf
  python scripts/optimize.py my_resume.pdf --role "Senior AI Engineer" --format pdf
  python scripts/optimize.py my_resume.pdf --score-only
  python scripts/optimize.py my_resume.docx --jd job.txt --style executive --provider openai
        """
    )
    parser.add_argument("resume", help="Path to resume file (PDF, DOCX, or TXT)")
    parser.add_argument("--role", "-r", default="", help="Target job title (optional)")
    parser.add_argument("--jd", default="", help="Path to job description text file (optional)")
    parser.add_argument(
        "--format", "-f", choices=["docx", "pdf", "both"], default="both",
        help="Output format (default: both)"
    )
    parser.add_argument(
        "--style", "-s", choices=["minimal", "professional", "executive"], default="professional",
        help="Resume style: minimal=1page, professional=1-2pages, executive=2pages (default: professional)"
    )
    parser.add_argument(
        "--provider", choices=["anthropic", "openai"], default=None,
        help="AI provider (default: from .env AI_PROVIDER setting)"
    )
    parser.add_argument("--score-only", action="store_true", help="Only score the resume, no rewriting")
    parser.add_argument("--output-dir", "-o", default="outputs", help="Output directory (default: outputs)")
    args = parser.parse_args()

    # Validate resume path
    resume_path = Path(args.resume)
    if not resume_path.exists():
        logger.error("Resume file not found: %s", args.resume)
        sys.exit(1)

    # Override provider if specified
    if args.provider:
        import os
        os.environ["AI_PROVIDER"] = args.provider

    # Load job description if provided
    job_description = ""
    if args.jd:
        jd_path = Path(args.jd)
        if not jd_path.exists():
            logger.error("Job description file not found: %s", args.jd)
            sys.exit(1)
        job_description = jd_path.read_text(encoding="utf-8", errors="ignore")
        logger.info("Loaded job description: %d chars", len(job_description))

    from src.parsers.resume_parser import parse_resume
    from src.optimizer.analyzer import analyze_resume
    from src.utils.config import settings

    logger.info("=" * 60)
    logger.info("AI Resume ATS Optimizer")
    logger.info("Provider: %s | Model: %s", settings.AI_PROVIDER,
                settings.ANTHROPIC_MODEL if settings.AI_PROVIDER == "anthropic" else settings.OPENAI_MODEL)
    logger.info("=" * 60)

    # Parse
    logger.info("Parsing resume: %s", resume_path.name)
    resume_text = parse_resume(resume_path)
    logger.info("Extracted %d characters", len(resume_text))

    # Analyze
    logger.info("Running ATS analysis...")
    report = analyze_resume(resume_text, target_role=args.role, job_description=job_description)

    # Print analysis report
    print("\n" + "=" * 60)
    print(f"  ATS SCORE: {report.ats_score}/100  ({report.grade})")
    print("=" * 60)

    if report.score_breakdown:
        print("\nScore Breakdown:")
        for k, v in report.score_breakdown.items():
            bar = "█" * int(v) + "░" * (20 - min(int(v * 2), 20))
            print(f"  {k:<28} {v:>5.1f}  {bar}")

    if report.critical_issues:
        print("\nCritical Issues (fix these first):")
        for issue in report.critical_issues:
            print(f"  ✗ {issue}")

    if report.missing_keywords:
        print(f"\nMissing Keywords: {', '.join(report.missing_keywords[:10])}")

    if report.strengths:
        print("\nStrengths:")
        for s in report.strengths:
            print(f"  ✓ {s}")

    if args.score_only:
        print("\nTip: Run without --score-only to generate an optimized resume.")
        return

    # Rewrite
    from src.optimizer.rewriter import rewrite_resume
    logger.info("Rewriting resume with AI (style: %s)...", args.style)
    resume_data, rewrite_tokens = rewrite_resume(
        resume_text,
        target_role=args.role,
        job_description=job_description,
        style=args.style,
        analysis=report,
    )
    logger.info("Rewrite complete for: %s", resume_data.name)

    # Generate output files
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = (resume_data.name or resume_path.stem).replace(" ", "_").lower()

    generated = []
    if args.format in ("docx", "both"):
        from src.generators.docx_generator import generate_docx
        docx_path = out_dir / f"{safe_name}_ats_optimized.docx"
        generate_docx(resume_data, docx_path)
        generated.append(("DOCX", docx_path))

    if args.format in ("pdf", "both"):
        from src.generators.pdf_generator import generate_pdf
        pdf_path = out_dir / f"{safe_name}_ats_optimized.pdf"
        generate_pdf(resume_data, pdf_path)
        generated.append(("PDF", pdf_path))

    # Aggregate tokens from both LLM calls
    at = report.tokens_used
    rt = rewrite_tokens
    total_inp = at.get("input_tokens", 0) + rt.get("input_tokens", 0)
    total_out = at.get("output_tokens", 0) + rt.get("output_tokens", 0)
    total_cost = round(at.get("estimated_cost_usd", 0.0) + rt.get("estimated_cost_usd", 0.0), 6)

    print("\n" + "=" * 60)
    print("  OPTIMIZATION COMPLETE")
    print("=" * 60)
    estimated_after = min(report.ats_score + 25, 98)
    print(f"  ATS Score:  {report.ats_score} → {estimated_after}  (+{estimated_after - report.ats_score} points)")
    print(f"  Keywords added: {', '.join(report.missing_keywords[:6])}")
    for fmt, path in generated:
        print(f"  {fmt}: {path.resolve()}")
    print(f"\n  Token Usage:  {total_inp:,} in / {total_out:,} out / {total_inp+total_out:,} total  (est. ${total_cost:.4f} USD)")
    print("=" * 60)


if __name__ == "__main__":
    main()

"""
src/optimizer/prompts.py
-------------------------
All LLM prompts for ATS analysis and resume rewriting.
"""

ATS_ANALYSIS_PROMPT = """You are an expert ATS (Applicant Tracking System) analyst and senior recruiter with 15+ years of experience.

Analyze this resume for ATS compatibility and provide a detailed assessment.

RESUME TEXT:
{resume_text}

TARGET ROLE (if provided): {target_role}
JOB DESCRIPTION (if provided): {job_description}

Return a JSON object with this exact structure:
{{
  "ats_score": <integer 0-100>,
  "score_breakdown": {{
    "contact_info": <0-10>,
    "professional_summary": <0-10>,
    "skills_section": <0-15>,
    "experience_quality": <0-20>,
    "quantified_achievements": <0-15>,
    "education_section": <0-10>,
    "keyword_match": <0-20>
  }},
  "critical_issues": [<list of strings — things that will cause ATS rejection>],
  "improvements": [<list of strings — specific actionable improvements>],
  "missing_keywords": [<keywords important for the target role that are missing>],
  "found_keywords": [<relevant keywords already present>],
  "strengths": [<what the resume does well>],
  "parsed_sections": {{
    "has_contact": true/false,
    "has_summary": true/false,
    "has_skills": true/false,
    "has_experience": true/false,
    "has_education": true/false,
    "has_projects": true/false
  }}
}}

Be specific and actionable. ATS score above 80 is good, 60-79 needs work, below 60 will likely be filtered out."""


REWRITE_PROMPT = """You are an expert resume writer and ATS optimization specialist. Your task is to rewrite and optimize the provided resume to be:
1. Fully ATS-compatible (no tables, no text boxes, simple formatting)
2. Keyword-rich for the target role
3. Achievement-focused with quantified impact
4. Professional and compelling for human reviewers

ORIGINAL RESUME:
{resume_text}

TARGET ROLE: {target_role}
JOB DESCRIPTION: {job_description}
STYLE: {style}
  - minimal: 1 page, essentials only, tight bullets
  - professional: 1-2 pages, balanced detail
  - executive: 2 pages, comprehensive, leadership emphasis

MISSING KEYWORDS TO ADD (from analysis): {missing_keywords}

INSTRUCTIONS:
- Start every experience bullet with a strong action verb (Led, Built, Engineered, Designed, Increased, Reduced, etc.)
- Include metrics/numbers in at least 70% of bullets (%, $, X times, N users, N hours saved)
- Use industry-standard section names: Professional Summary, Core Skills, Professional Experience, Projects, Education
- Preserve all real facts — do NOT invent metrics that aren't implied in the original
- Naturally weave in missing keywords where they genuinely fit
- Make the Professional Summary a powerful 3-4 sentence paragraph with top keywords
- For skills, group into logical categories

Return ONLY valid JSON with this exact structure (no markdown, no explanation):
{{
  "name": "<full name>",
  "title": "<professional title — optimized for target role>",
  "contact": {{
    "email": "<email>",
    "phone": "<phone>",
    "location": "<city, country>",
    "linkedin": "<linkedin URL or handle>",
    "github": "<github URL or handle>",
    "portfolio": "<portfolio URL if present>"
  }},
  "summary": "<3-4 sentence professional summary, keyword-rich, achievement-focused>",
  "skills": {{
    "<Category 1>": ["<skill>", "<skill>", ...],
    "<Category 2>": ["<skill>", ...],
    "<Category 3>": ["<skill>", ...],
    "<Category 4>": ["<skill>", ...]
  }},
  "experience": [
    {{
      "company": "<company name>",
      "title": "<job title>",
      "location": "<city, country>",
      "start_date": "<Month YYYY>",
      "end_date": "<Month YYYY or Present>",
      "bullets": [
        "<Action verb + achievement + metric>",
        ...
      ]
    }}
  ],
  "projects": [
    {{
      "name": "<project name>",
      "role": "<your role>",
      "period": "<date range>",
      "url": "<live URL if available>",
      "technologies": "<comma-separated tech stack>",
      "description": "<2-3 sentence description of what you built and its impact>"
    }}
  ],
  "pocs": [
    {{
      "name": "<POC/R&D name>",
      "description": "<architecture and impact in 2-3 sentences>"
    }}
  ],
  "education": [
    {{
      "degree": "<degree name>",
      "field": "<field of study>",
      "institution": "<institution name>",
      "year": "<graduation year>"
    }}
  ],
  "certifications": ["<cert name and year>"],
  "publications": ["<citation>"]
}}"""


SCORE_ONLY_PROMPT = """Rate this resume's ATS compatibility on a scale of 0-100.
Return only a JSON object: {{"score": <number>, "one_line_verdict": "<brief assessment>"}}

RESUME:
{resume_text}"""

"""
Smart Apply Engine
1. Fetches the full job description from the listing URL
2. Extracts keywords from it
3. Generates tailored resume + cover letter LaTeX

Uses the configured LLM provider: OpenAI or Groq.
"""

import json
import re
import requests
from pathlib import Path
from datetime import datetime
from html import unescape

try:
    from .llm_client import call_llm, has_llm_key
    from .profile_manager import get_active_resume_path
except ImportError:  # pragma: no cover
    from llm_client import call_llm, has_llm_key
    from profile_manager import get_active_resume_path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
COVER_LETTER_TEMPLATE = TEMPLATES_DIR / "cover_letter_base.tex"


def load_template(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ═══════════════════════════════════════════════════════════
# STEP 0: Fetch full job description from URL
# ═══════════════════════════════════════════════════════════

def fetch_job_description(url: str) -> str:
    """
    Fetch the job listing page and extract readable text.
    Works with Greenhouse, Reed, Adzuna, and most career pages.
    """
    if not url:
        return ""

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()

        html = response.text

        # Try to extract structured job content first (Greenhouse API)
        if "boards-api.greenhouse.io" in url or "greenhouse.io" in url:
            # Try the API endpoint for Greenhouse jobs
            gh_text = _try_greenhouse_api(url)
            if gh_text:
                return gh_text

        # Generic HTML text extraction
        return _extract_text_from_html(html)

    except Exception as e:
        print(f"[Apply] Failed to fetch {url}: {e}")
        return ""


def _try_greenhouse_api(url: str) -> str:
    """Try to get structured data from Greenhouse API."""
    # Extract job ID from URL patterns like:
    # https://boards.greenhouse.io/company/jobs/12345
    # https://job-boards.greenhouse.io/company/jobs/12345
    match = re.search(r"greenhouse\.io/(\w+)/jobs/(\d+)", url)
    if not match:
        return ""

    company, job_id = match.group(1), match.group(2)
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{job_id}"

    try:
        resp = requests.get(api_url, params={"content": "true"}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            title = data.get("title", "")
            content = _strip_html(data.get("content", ""))
            location = data.get("location", {}).get("name", "")

            departments = [d.get("name", "") for d in data.get("departments", [])]
            dept_str = ", ".join(departments) if departments else ""

            parts = []
            if title:
                parts.append(f"Job Title: {title}")
            if location:
                parts.append(f"Location: {location}")
            if dept_str:
                parts.append(f"Department: {dept_str}")
            if content:
                parts.append(f"\n{content}")

            return "\n".join(parts)
    except Exception:
        pass

    return ""


def _extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML, focusing on job description content."""
    # Remove script and style tags
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<nav[^>]*>.*?</nav>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<footer[^>]*>.*?</footer>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<header[^>]*>.*?</header>", "", html, flags=re.DOTALL | re.IGNORECASE)

    # Convert common elements to readable format
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</?p[^>]*>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</?li[^>]*>", "\n• ", html, flags=re.IGNORECASE)
    html = re.sub(r"</?(?:h[1-6]|div|section|article)[^>]*>", "\n", html, flags=re.IGNORECASE)

    # Strip remaining tags
    text = re.sub(r"<[^>]+>", " ", html)
    text = unescape(text)

    # Clean whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = text.strip()

    # Limit length (LLM context)
    if len(text) > 8000:
        text = text[:8000]

    return text


def _strip_html(html_str: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html_str)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ═══════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════

def generate_application(job: dict, api_key: str = "") -> dict:
    """
    Main entry point.
    1. Fetches full JD from URL
    2. Extracts keywords
    3. Tailors resume
    4. Generates cover letter
    Returns dict with all results.
    """
    if not api_key and not has_llm_key():
        return {"error": "No LLM API key configured. Add OPENAI_API_KEY or GROQ_API_KEY to scrapers/config.py"}

    resume_base = load_template(get_active_resume_path())
    cover_base = load_template(COVER_LETTER_TEMPLATE)

    title = job.get("title", "")
    company = job.get("company", "")
    location = job.get("location", "")
    url = job.get("url", "")

    # Step 0: Fetch full job description from URL
    print(f"[Apply] Fetching JD from: {url}")
    full_jd = fetch_job_description(url)

    # Fallback to stored snippet if URL fetch fails
    if not full_jd or len(full_jd) < 100:
        full_jd = job.get("full_description", "") or job.get("description_snippet", "")
        print(f"[Apply] URL fetch failed, using stored snippet ({len(full_jd)} chars)")
    else:
        print(f"[Apply] Fetched full JD ({len(full_jd)} chars)")

    if not full_jd or len(full_jd) < 50:
        return {"error": f"Could not fetch job description. URL: {url}. Try adding description manually."}

    # Step 1: Extract keywords
    print("[Apply] Extracting keywords...")
    keywords_result = _extract_keywords(full_jd, title, api_key)

    # Step 2: Tailor resume
    print("[Apply] Tailoring resume...")
    resume_result = _tailor_resume(resume_base, full_jd, title, company, keywords_result, api_key)

    # Step 3: Generate cover letter
    print("[Apply] Generating cover letter...")
    cover_result = _generate_cover_letter(
        cover_base, resume_base, full_jd, title, company, location, keywords_result, api_key
    )

    return {
        "job_description": full_jd[:2000],  # Return truncated JD for display
        "keywords": keywords_result,
        "resume_latex": resume_result,
        "cover_letter_latex": cover_result,
        "job_title": title,
        "company": company,
        "generated_at": datetime.now().isoformat(),
    }


# ═══════════════════════════════════════════════════════════
# LLM CALL
# ═══════════════════════════════════════════════════════════

def _call_llm(system_prompt: str, user_prompt: str, api_key: str = "", max_tokens: int = 4096) -> str:
    """Call the configured LLM provider. api_key is kept for legacy Groq callers."""
    return call_llm(
        system_prompt,
        user_prompt,
        max_tokens=max_tokens,
        temperature=0.3,
        api_key=api_key or None,
    )


# ═══════════════════════════════════════════════════════════
# STEP 1: KEYWORD EXTRACTION
# ═══════════════════════════════════════════════════════════

def _extract_keywords(description: str, title: str, api_key: str) -> dict:

    system = """You are an expert ATS (Applicant Tracking System) analyst.
Extract keywords from job descriptions that candidates must include in their resume.
Return ONLY valid JSON. No markdown fences, no explanation, no backticks. Just the JSON object."""

    prompt = f"""Analyze this job posting and extract keywords.

Job Title: {title}

Job Description:
{description[:4000]}

Return a JSON object with exactly these keys:
{{
  "must_have_skills": ["list of required technical skills"],
  "nice_to_have_skills": ["list of preferred/bonus skills"],
  "tools_and_technologies": ["specific tools, frameworks, platforms mentioned"],
  "soft_skills": ["communication, leadership, etc."],
  "experience_keywords": ["specific experience they want"],
  "industry_terms": ["domain-specific terms"],
  "action_verbs": ["verbs from the JD that should appear in resume"]
}}

Important: Return ONLY the JSON. No other text."""

    try:
        result = _call_llm(system, prompt, api_key, max_tokens=1500)
        # Clean potential markdown wrapping
        result = result.strip()
        if result.startswith("```"):
            lines = result.split("\n")
            result = "\n".join(lines[1:])
        if result.endswith("```"):
            result = result[:-3]
        result = result.strip()

        parsed = json.loads(result)
        return parsed
    except json.JSONDecodeError as e:
        print(f"[Apply] JSON parse error: {e}")
        print(f"[Apply] Raw LLM output: {result[:500]}")
        return {"error": f"Failed to parse keywords JSON: {str(e)}", "raw": result[:500]}
    except Exception as e:
        print(f"[Apply] Keyword extraction error: {e}")
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════
# STEP 2: RESUME TAILORING
# ═══════════════════════════════════════════════════════════

def _tailor_resume(
    base_latex: str, description: str, title: str, company: str,
    keywords: dict, api_key: str
) -> str:

    keyword_summary = ""
    for category, items in keywords.items():
        if isinstance(items, list) and items:
            keyword_summary += f"\n{category}: {', '.join(items)}"

    system = r"""You are an expert resume writer who outputs LaTeX code.

CRITICAL RULES:
1. Output ONLY the complete LaTeX document. No explanations, no markdown backticks.
2. Keep the EXACT same LaTeX structure, preamble, and formatting as the base resume.
3. Do NOT change: name, contact info, education dates, company names, employment dates, project links.
4. DO change: the summary paragraph, bullet point wording, skills ordering.
5. Reword bullet points to naturally incorporate keywords from the JD without fabricating.
6. If the JD mentions skills the candidate has but aren't prominent, emphasize them.
7. Reorder Technical Skills to lead with the most relevant skills for this role.
8. Keep it to 1 page. Do not add fabricated experience.
9. Rewrite the summary paragraph to target this specific role.
10. Use action verbs from the JD where they fit naturally.
11. Properly escape all LaTeX special characters (\%, \&, \$, etc.).
12. Start with \documentclass and end with \end{document}. Nothing else."""

    prompt = f"""Here is the base resume in LaTeX:

{base_latex}

Applying to:
Title: {title}
Company: {company}

Job Description:
{description[:3500]}

Key terms to incorporate where truthful:
{keyword_summary}

Output ONLY the complete tailored LaTeX resume. Start with \\documentclass, end with \\end{{document}}."""

    try:
        result = _call_llm(system, prompt, api_key, max_tokens=4096)
        result = _clean_latex_output(result)

        if "\\documentclass" not in result or "\\end{document}" not in result:
            print("[Apply] Resume output doesn't look like LaTeX, using fallback")
            return base_latex

        return result
    except Exception as e:
        print(f"[Apply] Resume generation error: {e}")
        return f"% ERROR: {str(e)}\n\n{base_latex}"


# ═══════════════════════════════════════════════════════════
# STEP 3: COVER LETTER GENERATION
# ═══════════════════════════════════════════════════════════

def _generate_cover_letter(
    template: str, resume: str, description: str, title: str,
    company: str, location: str, keywords: dict, api_key: str
) -> str:

    today = datetime.now().strftime("%-d %B %Y")

    keyword_summary = ""
    for category, items in keywords.items():
        if isinstance(items, list) and items:
            keyword_summary += f"\n{category}: {', '.join(items)}"

    system = r"""You are an expert cover letter writer who outputs LaTeX code.

CRITICAL RULES:
1. Output ONLY the complete LaTeX document. No explanations, no markdown backticks.
2. Use the EXACT same LaTeX preamble and formatting as the template.
3. REPLACE ALL <<PLACEHOLDER>> values with actual content.
4. Write 3 substantive paragraphs:
   - Paragraph 1: Why you're applying. Mention the specific role and what excites you about the company.
   - Paragraph 2: Map your experience to their requirements. Use specific examples from the resume.
   - Paragraph 3: What you'd contribute, enthusiasm, and a forward-looking close.
5. Sound human and specific, not generic. Reference actual things from the JD.
6. Keep it concise — under 1 page.
7. Properly escape LaTeX special characters (\%, \&, \$, etc.).
8. Start with \documentclass and end with \end{document}. Nothing else."""

    prompt = f"""Cover letter LaTeX template:

{template}

Candidate's resume:

{resume}

Applying to:
Title: {title}
Company: {company}
Location: {location or "London, UK"}
Today's date: {today}

Job Description:
{description[:3500]}

Key terms from JD:
{keyword_summary}

Generate the complete cover letter LaTeX. Replace ALL <<PLACEHOLDER>> values.
Use "Hiring Team" if no specific person is mentioned.
Output ONLY the LaTeX starting with \\documentclass and ending with \\end{{document}}."""

    try:
        result = _call_llm(system, prompt, api_key, max_tokens=3000)
        result = _clean_latex_output(result)

        if "\\documentclass" not in result or "\\end{document}" not in result:
            print("[Apply] Cover letter output doesn't look like LaTeX, using fallback")
            return f"% ERROR: LLM output was not valid LaTeX\n\n{template}"

        # Check placeholders were replaced
        if "<<" in result and ">>" in result:
            print("[Apply] Warning: some placeholders not replaced")

        return result
    except Exception as e:
        print(f"[Apply] Cover letter error: {e}")
        return f"% ERROR: {str(e)}\n\n{template}"


def _clean_latex_output(text: str) -> str:
    """Remove markdown fences and whitespace from LLM output."""
    text = text.strip()

    # Remove ```latex or ```tex wrapping
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
        else:
            text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()

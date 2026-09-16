"""
Cover Letter Generator - Generates a tailored cover letter for a job posting.

Usage:
  python cover_letter.py "https://job-url" "Company Name" "Role Title"
  python cover_letter.py "https://job-url" "Company Name"   (role extracted from JD)

Output:
  - DOCX saved to cover_letters/CoverLetter_{Company}.docx
  - Text dumped to console
"""

import json
import os
import re
import sys
import time

import requests
from bs4 import BeautifulSoup
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

try:
    from config import TRACKER_FILE, GOOGLE_API_KEY, BASE_RESUME_PATH, RESUME_OUTPUT_DIR
except ImportError:
    print("ERROR: config.py not found!")
    exit(1)

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

COVER_LETTER_OUTPUT_DIR = os.path.join(
    os.path.dirname(RESUME_OUTPUT_DIR), "cover_letters"
)

# ── Fixed template parts ──────────────────────────────────────────────────────

PERSONAL_PROJECTS_PARA = (
    "In parallel to my job search, I built several personal projects end-to-end: "
    "an automated job-tracking pipeline (Python, Excel, SMTP, Gemini API, Claude API), "
    "and Fit-Check — a live AI-powered job fit scorer deployed on Render "
    "(FastAPI, Gemini 2.5 Flash, Docker) that parses any job URL against a resume and "
    "returns a skill-by-skill breakdown. All of these are open sourced, usable by me "
    "almost on daily basis for fast tracking many iterative activities and I learnt it all "
    "by my self with help of claude and built from scratch."
)

CLOSE_PARA = (
    "Currently based in Paris, I am open to remote, hybrid, or on-site roles and am "
    "particularly motivated by opportunities where I can own services end-to-end and "
    "collaborate closely with cross-functional teams. I would welcome the chance to "
    "discuss how my background aligns with {company}'s engineering goals."
)

HEADER = "Paris, France  |  +33 7 73 11 70 85  |  mahashwetha91@gmail.com  |  linkedin.com/in/mahashwetha-rao  |  github.com/Mahashwetha"

COVER_PROMPT = """You are a cover letter writer for a senior backend engineer with 11 years of experience.

CANDIDATE BACKGROUND:
- 11+ years Core Java, Spring, Spring AOP/AspectJ, JUnit, Jenkins CI/CD, Bash scripting
- Former NASDAQ trading surveillance engineer
- Exposure to Python (personal projects), Docker, Kubernetes (conceptual), C++
- Actively upskilling: AI/LLM integration (GitHub Copilot, Gemini API, Claude API)
- Based in Paris, France — open to remote/hybrid/on-site

JOB:
Company: {company}
Role: {role}
Job Description:
{jd}

Generate ONLY a JSON object with these four keys (no markdown, no extra text):
{{
  "company_value_prop": "<what the company/platform does — plain noun phrase, NO 'at the heart of', e.g. 'AI-first ecommerce search and discovery platform', max 12 words>",
  "role_hook": "<what this role builds/delivers — starts with an -ing verb, e.g. 'building scalable services that deliver enriched product metadata', max 15 words>",
  "matched_para": "<full paragraph (3-5 sentences) written in first person (I, my, me) highlighting candidate's existing skills that directly match this JD — name specific tech/tools from JD that candidate has; be concrete not vague>",
  "gap_para": "<full paragraph (2-4 sentences) written in first person (I, my, me) briefly bridging the most important gaps — be honest but positive; mention any genuine adjacent skills; don't list all gaps, pick the 1-2 most important>"
}}

Rules:
- matched_para and gap_para MUST be written in first person (I, my, me) — never refer to the candidate by name or use 'she/her/he/his/they'
- matched_para: only mention tech/skills explicitly in both the JD and the candidate background above
- gap_para: don't fabricate experience; use phrases like 'exposure to', 'actively expanding', 'hands-on with adjacent X and motivated to deepen Y'
- Keep paragraphs at roughly the same length as natural cover letter prose
- Tone: confident, specific, not generic"""


# ── JD fetching (same as resume_tailor.py) ───────────────────────────────────

def fetch_job_description(url):
    try:
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        for ld in soup.find_all('script', type='application/ld+json'):
            if not ld.string:
                continue
            try:
                data = json.loads(ld.string)
                desc = data.get('description', '')
                title = data.get('title', '') or data.get('name', '')
                if desc and len(desc) > 100:
                    text = BeautifulSoup(desc, 'html.parser').get_text('\n', strip=True)
                    if title:
                        text = f"Job Title: {title}\n\n{text}"
                    return text[:8000], title
            except Exception:
                pass

        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        text = soup.get_text('\n', strip=True)

        # Try og:title for role title
        og = soup.find('meta', attrs={'property': 'og:title'})
        page_title = og.get('content', '') if og else ''
        m = re.match(r'^(.+?)\s+at\s+', page_title)
        extracted_title = m.group(1).strip() if m else ''

        if len(text) < 500:
            meta = (soup.find('meta', attrs={'name': 'description'})
                    or soup.find('meta', attrs={'property': 'og:description'}))
            content = meta.get('content', '') if meta else ''
            if len(content) > len(text):
                text = content
        return text[:8000], extracted_title
    except Exception as e:
        print(f"  Failed to fetch JD: {e}")
        return '', ''


# ── Gemini call ───────────────────────────────────────────────────────────────

def call_gemini(prompt, max_retries=3):
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 8192,
        },
    }
    for attempt in range(max_retries):
        resp = requests.post(
            f"{GEMINI_URL}?key={GOOGLE_API_KEY}",
            json=payload,
            timeout=60,
        )
        if resp.status_code in (429, 503) and attempt < max_retries - 1:
            wait = 10 * (attempt + 1)
            print(f"  Gemini {resp.status_code}, waiting {wait}s (attempt {attempt+1}/{max_retries})...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        text = resp.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            text = m.group(0)
        return json.loads(text)
    raise Exception("Gemini rate limit exceeded after all retries")


# ── Assemble cover letter ─────────────────────────────────────────────────────

def assemble_text(company, role, parts):
    value_prop = parts.get('company_value_prop', f"building great products at {company}")
    role_hook = parts.get('role_hook', f"contribute to {role}")

    intro = (
        f"I am writing to express my interest in the {role} position at {company}. "
        f"With over 11 years of experience building and maintaining mission-critical backend systems, "
        f"I am excited by the opportunity to contribute to {company}'s {value_prop} "
        f"by {role_hook}."
    )

    paragraphs = [
        "Respected Hiring Manager,",
        "",
        intro,
        "",
        parts.get('matched_para', ''),
        "",
        parts.get('gap_para', ''),
        "",
        PERSONAL_PROJECTS_PARA,
        "",
        CLOSE_PARA.format(company=company),
        "",
        "Thank you for considering my application. I look forward to the possibility of speaking with you.",
        "",
        "Sincerely,",
        "Mahashwetha Rao",
    ]
    return "\n".join(paragraphs)


def save_docx(company, role, parts, output_path):
    doc = Document()

    # Page margins
    for section in doc.sections:
        section.top_margin = section.bottom_margin = Pt(72)
        section.left_margin = section.right_margin = Pt(72)

    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(11)

    def add(text, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=8):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.space_before = Pt(0)
        p.alignment = align
        run = p.add_run(text)
        run.bold = bold
        run.font.name = 'Calibri'
        run.font.size = Pt(11)
        return p

    add(HEADER, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=16)

    add("Respected Hiring Manager,", space_after=8)

    value_prop = parts.get('company_value_prop', f"building great products at {company}")
    role_hook = parts.get('role_hook', f"contribute to {role}")
    intro = (
        f"I am writing to express my interest in the "
    )
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(intro)
    r.font.name = 'Calibri'; r.font.size = Pt(11)
    r = p.add_run(role)
    r.bold = True; r.font.name = 'Calibri'; r.font.size = Pt(11)
    r = p.add_run(f" position at ")
    r.font.name = 'Calibri'; r.font.size = Pt(11)
    r = p.add_run(company)
    r.bold = True; r.font.name = 'Calibri'; r.font.size = Pt(11)
    r = p.add_run(
        f". With over 11 years of experience building and maintaining mission-critical backend systems, "
        f"I am excited by the opportunity to contribute to {company}'s {value_prop} by {role_hook}."
    )
    r.font.name = 'Calibri'; r.font.size = Pt(11)

    add(parts.get('matched_para', ''), space_after=8)
    add(parts.get('gap_para', ''), space_after=8)
    add(PERSONAL_PROJECTS_PARA, space_after=8)
    add(CLOSE_PARA.format(company=company), space_after=8)
    add("Thank you for considering my application. I look forward to the possibility of speaking with you.", space_after=16)
    add("Sincerely,", space_after=4)
    add("Mahashwetha Rao", bold=True, space_after=0)

    doc.save(output_path)


# ── Main ──────────────────────────────────────────────────────────────────────

def safe_name(s):
    return re.sub(r'[^a-z0-9_]', '_', s.lower().strip()).strip('_')


def generate(url, company, role=''):
    os.makedirs(COVER_LETTER_OUTPUT_DIR, exist_ok=True)

    print(f"  Fetching JD from {url}...")
    jd_text, extracted_role = fetch_job_description(url)
    if not jd_text:
        print("  ERROR: Could not fetch job description.")
        return

    if not role:
        role = extracted_role or company + ' role'

    print(f"  Calling Gemini ({GEMINI_MODEL}) to tailor cover letter...")
    prompt = COVER_PROMPT.format(company=company, role=role, jd=jd_text[:5000])
    try:
        parts = call_gemini(prompt)
    except Exception as e:
        print(f"  ERROR: Gemini call failed: {e}")
        return

    text = assemble_text(company, role, parts)

    output_path = os.path.join(COVER_LETTER_OUTPUT_DIR, f"CoverLetter_{safe_name(company)}.docx")
    save_docx(company, role, parts, output_path)

    print(f"\n{'='*60}")
    print(text)
    print(f"{'='*60}")
    print(f"\n  Saved: {output_path}")
    return output_path


def main():
    if len(sys.argv) < 3:
        print("Usage: python cover_letter.py \"https://job-url\" \"Company Name\" [\"Role Title\"]")
        exit(1)
    url = sys.argv[1]
    company = sys.argv[2]
    role = sys.argv[3] if len(sys.argv) >= 4 else ''
    generate(url, company, role)


if __name__ == '__main__':
    main()

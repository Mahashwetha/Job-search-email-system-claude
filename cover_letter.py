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
    "Outside work, I build and ship my own tools. I built an automated job-search pipeline "
    "(Python, Gemini and Claude APIs) and Fit-Check, a live AI app on Render (FastAPI, Gemini, "
    "Docker) that scores any job posting against a resume, skill by skill. Both are open source "
    "and I use them every day, which is how I learned to design, deploy and maintain "
    "AI-powered systems end to end."
)

BANNED_OPENINGS = ("i am writing", "i'm writing", "express my interest", "i am excited",
                   "i'm excited", "with over", "i am thrilled", "i would like to apply",
                   "aligns perfectly")
# claims that the candidate has domain expertise she doesn't have (NASDAQ = trade surveillance)
FALSE_DOMAIN_CLAIM = re.compile(
    r"(expertise|experience|background|expert|specialist)\s+(in|with|of)\s+(\w+\s){0,2}"
    r"(payments?|transaction processing|trade execution|banking|lending|insurance)", re.I)

FALLBACK_OPENING = (
    "At NASDAQ, I led development of the alerting framework behind the SMARTS trade surveillance "
    "platform, cutting development effort by 15% across more than 350 subscription deployments. "
    "I would like to bring that production-grade backend experience to the {role} role at {company}."
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
- Former NASDAQ trade surveillance engineer (SMARTS market-abuse alerting platform; NOT payments or trade execution)
- Exposure to Python (personal projects), Docker, Kubernetes (conceptual), C++
- Actively upskilling: AI/LLM integration (GitHub Copilot, Gemini API, Claude API)
- Based in Paris, France — open to remote/hybrid/on-site

CANDIDATE ACHIEVEMENTS (verified facts; the ONLY achievements and numbers you may cite, never invent others):
- Led development of a Spring AspectJ + Jackson framework for structured alerting on NASDAQ's SMARTS trade surveillance platform; performance tuning cut development effort by 15%
- Deployed 350+ SMARTS alert subscriptions across APAC, EMEA and NSAC using Agile practices
- Delivered 500+ subscription migrations across production systems through 30+ backend investigations
- Upgraded APIs from Java 7 to Java 11
- Built an XML-based Java parameter migration tool with Jenkins integration, used for all subscription migrations
- Senior Tech Lead at NASDAQ: mentored junior developers, led code reviews and design discussions
- 5 years at Cisco Video Technology on Set Top Box / OTT: EPG features, MPEG DASH, DRM, JavaScript; delivered the Viasat Ukraine Zapper project
- Personal projects: built and deployed Fit-Check (FastAPI, Gemini, Docker, live on Render) and an open-source AI job-search pipeline (Python, Gemini and Claude APIs)

REFERRAL: {referral}

JOB:
Company: {company}
Role: {role}
Job Description:
{jd}

Generate ONLY a JSON object with these keys (no markdown, no extra text):
{{
  "opening_type": "<one of: referral, achievement, company, capability>",
  "opening_para": "<exactly 2 sentences that open the letter. Choose the ONE strongest opening for this job: referral (only if REFERRAL is not 'none': name the referrer in sentence 1); achievement (one item from CANDIDATE ACHIEVEMENTS tied to an outcome this JD cares about); company (a concrete detail from the JD about what the company builds or has just announced, connected to the candidate's experience); capability (the JD's single most critical requirement, stated with specific evidence from the achievements). Sentence 2 connects it to the {role} role at {company}.>",
  "company_value_prop": "<what the company/platform does — plain noun phrase, NO 'at the heart of', e.g. 'AI-first ecommerce search and discovery platform', max 12 words>",
  "role_hook": "<what this role builds/delivers — starts with an -ing verb, e.g. 'building scalable services that deliver enriched product metadata', max 15 words>",
  "matched_para": "<full paragraph (3-5 sentences) written in first person (I, my, me) highlighting candidate's existing skills that directly match this JD — name specific tech/tools from JD that candidate has; be concrete not vague>",
  "gap_para": "<full paragraph (2-4 sentences) written in first person (I, my, me) briefly bridging the most important gaps — be honest but positive; mention any genuine adjacent skills; don't list all gaps, pick the 1-2 most important>"
}}

Rules:
- matched_para and gap_para MUST be written in first person (I, my, me) — never refer to the candidate by name or use 'she/her/he/his/they'
- matched_para: only mention tech/skills explicitly in both the JD and the candidate background above
- gap_para: don't fabricate experience. State plainly what the candidate has not used, then mention only real adjacent experience from the background above. Never claim the candidate is currently learning, deepening, expanding or upskilling in a gap technology unless the background explicitly says so (only the 'Actively upskilling' line above counts)
- opening_para must NOT contain "I am writing", "express my interest", "I am excited", "With over", "aligns perfectly", must not summarise the CV and must not explain why the candidate wants the job; it must name {company}; it may only use facts from CANDIDATE ACHIEVEMENTS and CANDIDATE BACKGROUND
- NEVER re-label the candidate's domain to match the company's. NASDAQ work was TRADE SURVEILLANCE (market-abuse alerting), not payments, trading execution, banking or transaction processing; Cisco work was video/Set Top Box. Say what the work actually was, then connect it with "similar" or "transferable" if relevant (e.g. "high-reliability financial systems")
- matched_para must NOT start with "With over" or restate the achievement already used in opening_para; use different evidence
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

def build_opening(company, role, parts):
    """Gemini's opening_para if it follows the rules, else a safe achievement-led opening."""
    opening = (parts.get('opening_para') or '').strip()
    low = opening.lower()
    reasons = [f"banned phrase '{b}'" for b in BANNED_OPENINGS if b in low]
    if opening and company.lower() not in low:
        reasons.append("company not named")
    m = FALSE_DOMAIN_CLAIM.search(opening)
    if m:
        reasons.append(f"false domain claim '{m.group(0)}'")
    if opening and not reasons:
        return opening
    if opening:
        print(f"  Opening rejected ({'; '.join(reasons)}), using fallback. Rejected text: {opening}")
    return FALLBACK_OPENING.format(company=company, role=role)


def assemble_text(company, role, parts):
    intro = build_opening(company, role, parts)

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
        "Mahashwetha",
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

    add(build_opening(company, role, parts), space_after=8)

    add(parts.get('matched_para', ''), space_after=8)
    add(parts.get('gap_para', ''), space_after=8)
    add(PERSONAL_PROJECTS_PARA, space_after=8)
    add(CLOSE_PARA.format(company=company), space_after=8)
    add("Thank you for considering my application. I look forward to the possibility of speaking with you.", space_after=16)
    add("Sincerely,", space_after=4)
    add("Mahashwetha", bold=True, space_after=0)

    cp = doc.core_properties
    cp.author = cp.last_modified_by = "Mahashwetha"
    cp.comments = ""
    doc.save(output_path)


# ── Main ──────────────────────────────────────────────────────────────────────

def safe_name(s):
    return re.sub(r'[^a-z0-9_]', '_', s.lower().strip()).strip('_')


def generate(url, company, role='', referral=''):
    os.makedirs(COVER_LETTER_OUTPUT_DIR, exist_ok=True)

    print(f"  Fetching JD from {url}...")
    jd_text, extracted_role = fetch_job_description(url)
    if not jd_text:
        print("  ERROR: Could not fetch job description.")
        return

    if not role:
        role = extracted_role or company + ' role'

    print(f"  Calling Gemini ({GEMINI_MODEL}) to tailor cover letter...")
    prompt = COVER_PROMPT.format(company=company, role=role, jd=jd_text[:5000],
                                 referral=referral.strip() or 'none')
    try:
        parts = call_gemini(prompt)
    except Exception as e:
        print(f"  ERROR: Gemini call failed: {e}")
        return
    print(f"  Opening type: {parts.get('opening_type', '?')}")

    text = assemble_text(company, role, parts)

    output_path = os.path.join(COVER_LETTER_OUTPUT_DIR, f"CoverLetter_{safe_name(company)}.docx")
    save_docx(company, role, parts, output_path)

    print(f"\n{'='*60}")
    print(text)
    print(f"{'='*60}")
    print(f"\n  Saved: {output_path}")
    return output_path


def main():
    args = sys.argv[1:]
    referral = ''
    if '--referral' in args:
        i = args.index('--referral')
        referral = args[i + 1] if i + 1 < len(args) else ''
        args = args[:i] + args[i + 2:]
    if len(args) < 2:
        print("Usage: python cover_letter.py \"https://job-url\" \"Company Name\" [\"Role Title\"] [--referral \"Name, their role\"]")
        exit(1)
    generate(args[0], args[1], args[2] if len(args) >= 3 else '', referral)


if __name__ == '__main__':
    main()

"""
Fit Scorer — rates job-to-resume match using Gemini 2.5 Flash.

Public API:
  score_fit_batch(items)  → list of fit dicts  (for digest emails — title+company only, one call)
  score_fit_single(url, title, company) → fit dict  (for fit-check CLI — full description)
  fit_badge_html(fit)     → inline HTML badge
  fetch_job_description(url) → str  (reusable scraper)
"""

import json
import os
import re
import requests
from bs4 import BeautifulSoup

# ── Config ──────────────────────────────────────────────────────────────────

try:
    from config import GOOGLE_API_KEY, BASE_RESUME_PATH
    _FIT_SCORER_AVAILABLE = bool(GOOGLE_API_KEY and GOOGLE_API_KEY != 'your_gemini_api_key_here')
except ImportError:
    _FIT_SCORER_AVAILABLE = False
    GOOGLE_API_KEY = ''
    BASE_RESUME_PATH = ''

try:
    FIT_SCORE_ENABLED = __import__('config').FIT_SCORE_ENABLED
except (ImportError, AttributeError):
    FIT_SCORE_ENABLED = True

GEMINI_MODEL = 'gemini-2.5-flash'
GEMINI_URL = (
    f'https://generativelanguage.googleapis.com/v1beta/models/'
    f'{GEMINI_MODEL}:generateContent'
)

# ── Resume loading (cached) ──────────────────────────────────────────────────

_RESUME_CACHE = None


def _load_resume_text():
    global _RESUME_CACHE
    if _RESUME_CACHE:
        return _RESUME_CACHE

    try:
        from docx import Document
        doc = Document(BASE_RESUME_PATH)
        lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        _RESUME_CACHE = '\n'.join(lines)
        return _RESUME_CACHE
    except Exception:
        pass

    # Fallback: myquickintro.txt
    fallback = os.path.join(
        os.path.expanduser('~'),
        'OneDrive', 'Desktop', 'Resume2026', 'myquickintro.txt'
    )
    try:
        with open(fallback, encoding='utf-8') as f:
            _RESUME_CACHE = f.read()
            return _RESUME_CACHE
    except Exception:
        pass

    _RESUME_CACHE = (
        'Senior Java Backend Developer, ~12 years experience (NASDAQ, Cisco), Paris-based. '
        'Core skills: Java, Spring Boot, microservices, OTT platforms, trade surveillance, '
        'REST APIs, Kafka, distributed systems. Upskilling: GenAI/LLM integration.'
    )
    return _RESUME_CACHE


# ── Gemini call ──────────────────────────────────────────────────────────────

def _call_gemini(prompt):
    payload = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {
            'temperature': 0.2,
            'maxOutputTokens': 4096,
            # gemini-2.5-flash spends "thinking" tokens from this same budget;
            # disable it for this structured JSON task so the array isn't truncated.
            'thinkingConfig': {'thinkingBudget': 0},
        },
    }
    last_exc = None
    for attempt in range(3):  # retry transient 429/500/503 with backoff
        try:
            resp = requests.post(
                GEMINI_URL,
                headers={'Content-Type': 'application/json'},
                params={'key': GOOGLE_API_KEY},
                json=payload,
                timeout=30,
            )
            if resp.status_code in (429, 500, 503) and attempt < 2:
                import time as _t
                _t.sleep(2 * (attempt + 1))
                continue
            resp.raise_for_status()
            return resp.json()['candidates'][0]['content']['parts'][0]['text']
        except requests.exceptions.RequestException as e:
            last_exc = e
            import time as _t
            _t.sleep(2 * (attempt + 1))
    raise last_exc


# ── Job description fetching ─────────────────────────────────────────────────

def fetch_job_description(url):
    """Fetch and clean job description text from a URL.
    Supports LinkedIn, WTTJ (Algolia), BuiltIn, and generic HTML pages.
    Returns plain text (up to 4000 chars).
    """
    url_lower = url.lower()
    if 'linkedin.com/jobs/view/' in url_lower:
        return _fetch_linkedin(url)
    if 'welcometothejungle.com' in url_lower:
        return _fetch_wttj(url)
    return _fetch_generic(url)


def _fetch_linkedin(url):
    m = re.search(r'-(\d+)(?:\?|$)', url)
    if not m:
        return ''
    job_id = m.group(1)
    api_url = f'https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}'
    try:
        resp = requests.get(api_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if resp.status_code != 200:
            return ''
        match = re.search(r'show-more-less-html__markup[^>]*>(.*?)</div', resp.text, re.DOTALL)
        if not match:
            return ''
        text = re.sub(r'<[^>]+>', ' ', match.group(1))
        return ' '.join(text.split())[:4000]
    except Exception:
        return ''


def _fetch_wttj(url):
    # Extract job slug from URL and query Algolia for description
    m = re.search(r'/companies/([^/]+)/jobs/([^?&#]+)', url)
    if not m:
        return _fetch_generic(url)
    job_slug = m.group(2)
    try:
        algolia_url = 'https://CSEKHVMS53-dsn.algolia.net/1/indexes/wttj_jobs_production_fr/query'
        headers = {
            'X-Algolia-Application-Id': 'CSEKHVMS53',
            'X-Algolia-API-Key': '4bd8f6215d0cc52b26430765769e65a0',
            'Content-Type': 'application/json',
            'Origin': 'https://www.welcometothejungle.com',
            'Referer': 'https://www.welcometothejungle.com/',
        }
        query = job_slug.replace('-', ' ')
        payload = {'params': f'query={query}&hitsPerPage=5'}
        resp = requests.post(algolia_url, headers=headers, json=payload, timeout=15)
        if resp.ok:
            for hit in resp.json().get('hits', []):
                if hit.get('slug') == job_slug:
                    # description can be plain text or nested dict
                    desc = hit.get('description') or hit.get('profile') or ''
                    if isinstance(desc, dict):
                        desc = ' '.join(str(v) for v in desc.values())
                    if desc:
                        return str(desc)[:4000]
    except Exception:
        pass
    return _fetch_generic(url)


def _fetch_generic(url):
    try:
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
        }
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return ''
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Try JSON-LD first (Greenhouse, Workday, BuiltIn, etc.)
        ld = soup.find('script', type='application/ld+json')
        if ld and ld.string:
            try:
                data = json.loads(ld.string)
                desc = data.get('description', '')
                if desc and len(desc) > 100:
                    return BeautifulSoup(desc, 'html.parser').get_text(' ', strip=True)[:4000]
            except Exception:
                pass
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        return soup.get_text(' ', strip=True)[:4000]
    except Exception:
        return ''


# ── Scoring ──────────────────────────────────────────────────────────────────

_VERDICT_THRESHOLDS = [
    (80, 'Strong'),
    (65, 'Good'),
    (40, 'Moderate'),
    (0,  'Weak'),
]


def _parse_fit_response(text):
    """Parse a Gemini JSON response into a fit dict. Returns None on failure."""
    text = text.strip()
    text = re.sub(r'^```[a-z]*\n?', '', text).rstrip('`').strip()
    try:
        return json.loads(text)
    except Exception:
        return None


# Max jobs per Gemini call. Smaller chunks avoid output-token truncation and
# reduce the blast radius of a single failed/rate-limited request.
_FIT_CHUNK_SIZE = 15


def _score_fit_chunk(items):
    """Score up to _FIT_CHUNK_SIZE jobs in ONE Gemini call. Returns a list of
    fit dicts (same order) or a list of None on failure."""
    resume = _load_resume_text()
    job_lines = [
        f"{i + 1}. [{item.get('company', '?')}] {item['title']}"
        for i, item in enumerate(items)
    ]

    prompt = f"""Score each job's fit for this candidate's resume. Use title + company as context.

CANDIDATE RESUME:
{resume[:1800]}

JOBS (title + company only):
{chr(10).join(job_lines)}

Reply ONLY with a JSON array — one object per job, same order, no extra text:
[
  {{"score": 75, "verdict": "Good", "strengths": "Java backend match, fintech", "gaps": "No Go exp"}},
  ...
]

Verdict scale: Strong (80-100), Good (65-79), Moderate (40-64), Weak (0-39).
Max 8 words each for strengths and gaps."""

    try:
        raw = _call_gemini(prompt)
        arr_match = re.search(r'\[.*\]', raw, re.DOTALL)
        if not arr_match:
            return [None] * len(items)
        results = json.loads(arr_match.group(0))
        if isinstance(results, list) and len(results) == len(items):
            return results
    except Exception as e:
        print(f'  Fit scorer chunk error: {e}')
    return [None] * len(items)


def score_fit_batch(items):
    """Score a list of jobs against the resume (title + company, no description fetch).

    Splits into chunks of _FIT_CHUNK_SIZE to avoid output truncation, scores each
    chunk in one Gemini call, and concatenates. Returns a list of fit dicts in the
    same order (None for any job whose chunk failed).

    Prints a clear warning if scoring fully or partially fails, so callers/logs
    don't silently ship an empty Fit column.

    Each fit dict: {'score': int, 'verdict': str, 'strengths': str, 'gaps': str}
    """
    if not _FIT_SCORER_AVAILABLE or not FIT_SCORE_ENABLED or not items:
        return [None] * len(items)

    results = []
    for start in range(0, len(items), _FIT_CHUNK_SIZE):
        results.extend(_score_fit_chunk(items[start:start + _FIT_CHUNK_SIZE]))

    scored = sum(1 for r in results if r)
    if scored == 0:
        print(f'  WARNING: Fit scoring returned 0/{len(items)} results '
              f'(likely Gemini quota/rate limit) — sending without badges.')
    elif scored < len(results):
        print(f'  WARNING: Fit scoring partial — {scored}/{len(results)} scored; '
              f'the rest will show no badge.')
    return results


def score_fit_single(url, title, company=''):
    """Score one job with full description fetch.
    Used by fit-check CLI for detailed analysis.

    Returns fit dict with extra 'description_used' bool and 'detail' str.
    """
    if not _FIT_SCORER_AVAILABLE:
        return None

    resume = _load_resume_text()
    print(f'  Fetching description from: {url}')
    description = fetch_job_description(url)
    has_desc = bool(description and len(description) > 100)

    desc_section = f'\n\nJOB DESCRIPTION:\n{description[:3000]}' if has_desc else ''

    prompt = f"""You are a senior tech recruiter. Assess this job fit for the candidate.

CANDIDATE RESUME:
{resume[:2000]}

JOB:
Title: {title}
Company: {company}{desc_section}

Reply ONLY in this JSON format (no markdown):
{{
  "score": <0-100>,
  "verdict": "<Weak|Moderate|Good|Strong>",
  "strengths": "<2-3 sentences on matching points>",
  "gaps": "<2-3 sentences on missing requirements>",
  "recommendation": "<1 sentence — apply / apply with cover note / skip>"
}}

Be honest and specific. If you lack a job description, base it on title + company reputation."""

    try:
        raw = _call_gemini(prompt)
        obj_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not obj_match:
            return None
        result = json.loads(obj_match.group(0))
        result['description_used'] = has_desc
        return result
    except Exception as e:
        print(f'  Fit scorer error: {e}')
        return None


# ── HTML rendering ───────────────────────────────────────────────────────────

_VERDICT_STYLES = {
    'Strong':   ('color:#155724;background:#d4edda', 'Strong'),
    'Good':     ('color:#1e5f14;background:#c8f0c0', 'Good'),
    'Moderate': ('color:#856404;background:#fff3cd', 'OK'),
    'Weak':     ('color:#721c24;background:#f8d7da', 'Weak'),
}


def fit_badge_html(fit):
    """Return a compact HTML badge for embedding in email tables.

    fit: dict returned by score_fit_batch / score_fit_single, or None.
    Returns '' if fit is None or scoring is disabled.
    """
    if not fit:
        return ''
    verdict = fit.get('verdict', '')
    score = fit.get('score', 0)
    style, label = _VERDICT_STYLES.get(verdict, ('color:#555;background:#eee', verdict))
    tooltip = f"✓ {fit.get('strengths', '')} | ✗ {fit.get('gaps', '')}"
    return (
        f'<span style="{style};padding:2px 5px;border-radius:3px;'
        f'font-size:9px;font-weight:bold;white-space:nowrap;" title="{tooltip}">'
        f'{score}% {label}</span>'
    )

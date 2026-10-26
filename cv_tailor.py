"""
CV Tailor - evidence-only edits to the current CV DOCX for one job.

The comparison (which JD skills are missing, which ones the candidate confirms) is done by
the resume-tailor skill in Claude Code; this script only does the deterministic parts.

Usage:
  python cv_tailor.py jd <job-url>                 print the job description text
  python cv_tailor.py cv                           print the base CV, one paragraph per line
  python cv_tailor.py apply "<Company>" <edits.json>
  python cv_tailor.py jds <out_dir> <url> [<url> ...]   fetch several JDs in parallel into out_dir/jd_<n>.txt
  python cv_tailor.py apply-batch <batch.json> [--workers N]   build several tailored CVs in parallel

edits.json:
  {"replace": [{"old": "exact text inside one run", "new": "replacement"}, ...],
   "add_skills": ["Cucumber (TDD)", "YourKit Java Profiler"]}

batch.json (apply-batch):
  [{"company": "Acme Backend", "edits": {...same as edits.json...}, "base": "main" | "ai"}, ...]
  "base" picks BASE_CV_DOCX (default) or BASE_CV_DOCX_AI from config.py.

Output: RESUME_OUTPUT_DIR/resume_<company>.docx + .pdf (PDF via Microsoft Word).
"""

import html
import json
import os
import re
import sys

import requests
from bs4 import BeautifulSoup
from docx import Document

try:
    import config
except ImportError:
    print("ERROR: config.py not found!")
    sys.exit(1)

BASE_CV_DOCX = os.environ.get("BASE_CV_DOCX") or getattr(
    config, "BASE_CV_DOCX", os.path.join(os.path.expanduser("~"), "resume.docx"))
SKILLS_LABEL = getattr(config, "CV_SKILLS_LABEL", "Frameworks & Tools:")
# Skills added to the AI skills line of EVERY tailored CV. Empty by default: list only skills you really have.
ALWAYS_AI_SKILLS = list(getattr(config, "CV_ALWAYS_AI_SKILLS", []))
AI_LABELS = tuple(getattr(config, "CV_AI_LABELS", ("AI & ", "AI:", "AI Skills")))
# True: the '  |  ...' tail of the AI line is replaced by ALWAYS_AI_SKILLS (keeps the line short).
# False (default): the skills are inserted before the '|' and the tail is kept.
REPLACE_AI_TAIL = getattr(config, "CV_REPLACE_AI_TAIL", False)
# Replacements applied to every CV built from BASE_CV_DOCX_AI (e.g. a project line kept out of the base file).
# Same shape as edits.json "replace" items; an "old" text that isn't found is skipped with a note.
AI_DEFAULT_REPLACE = list(getattr(config, "CV_AI_DEFAULT_REPLACE", []))
NL = "\n"


def _console_utf8():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ── Job description fetching ─────────────────────────────────────────────────

def _html_text(markup):
    return BeautifulSoup(markup or "", "html.parser").get_text(NL, strip=True)


def _ashby_jd(url):
    """Ashby pages are JS-rendered; its public posting API returns the full description."""
    m = re.search(r"jobs\.ashbyhq\.com/([^/?#]+)/([0-9a-f-]{36})", url)
    if not m:
        return ""
    org, job_id = m.groups()
    resp = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{org}", timeout=20)
    if resp.status_code != 200:
        return ""
    job = next((j for j in resp.json().get("jobs", []) if j.get("id") == job_id), None)
    if not job:
        return ""
    head = f"Job Title: {job.get('title', '')}{NL}Location: {job.get('location', '')}"
    return head + NL + NL + _html_text(job.get("descriptionHtml"))


def _greenhouse_jd(url):
    """job-boards / boards.greenhouse.io pages: the public board API has the full description."""
    m = re.search(r"greenhouse\.io/([^/?#&]+)/jobs/(\d+)", url)
    if not m:
        return ""
    org, job_id = m.groups()
    resp = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{org}/jobs/{job_id}?content=true", timeout=20)
    if resp.status_code != 200:
        return ""
    job = resp.json()
    head = f"Job Title: {job.get('title', '')}{NL}Location: {(job.get('location') or {}).get('name', '')}"
    return head + NL + NL + _html_text(html.unescape(job.get("content", "")))


def _wttj_jd(url):
    """WTTJ pages are JS-rendered; its Algolia index has the summary, missions and profile."""
    m = re.search(r"/companies/([^/]+)/jobs/([^?&#/]+)", url)
    if not m:
        return ""
    job_slug = m.group(2)
    resp = requests.post(
        "https://CSEKHVMS53-dsn.algolia.net/1/indexes/wttj_jobs_production_fr/query",
        headers={"X-Algolia-Application-Id": "CSEKHVMS53", "X-Algolia-API-Key": "4bd8f6215d0cc52b26430765769e65a0",
                 "Origin": "https://www.welcometothejungle.com", "Referer": "https://www.welcometothejungle.com/"},
        json={"params": f"query={job_slug.replace('-', ' ')}&hitsPerPage=10"}, timeout=20)
    if resp.status_code != 200:
        return ""
    hit = next((h for h in resp.json().get("hits", []) if h.get("slug") == job_slug), None)
    if not hit:
        return ""
    missions = NL.join(f"- {x}" for x in hit.get("key_missions") or [])
    parts = [f"Job Title: {hit.get('name', '')}", hit.get("summary") or "",
             ("Key missions:" + NL + missions) if missions else "", hit.get("profile") or ""]
    return (NL + NL).join(x for x in parts if x)


def _site_jd(url):
    """Clean description from the site's own API, or '' if the URL isn't a supported site."""
    import fit_scorer
    u = url.lower()
    if "linkedin.com/jobs/view/" in u:
        return fit_scorer._fetch_linkedin(url)
    if "welcometothejungle.com" in u:
        return _wttj_jd(url)
    if "ashbyhq.com" in u:
        return _ashby_jd(url)
    if "greenhouse.io" in u:
        return _greenhouse_jd(url)
    return ""


def get_jd(url):
    """Site API first (LinkedIn, WTTJ, Ashby, Greenhouse); otherwise the longest page-text extraction.
    Returns "" when nothing usable (< 200 chars) was found."""
    import fit_scorer
    import resume_tailor
    text = ""
    try:
        text = _site_jd(url) or ""
    except Exception:
        pass
    if len(text.strip()) < 200:
        texts = []
        for f in (fit_scorer.fetch_job_description, resume_tailor.fetch_job_description):
            try:
                texts.append(f(url) or "")
            except Exception:
                pass
        text = max(texts, key=len, default="")
    return text if len(text.strip()) >= 200 else ""


def cmd_jd(url):
    text = get_jd(url)
    if not text:
        print("ERROR: could not fetch the job description. Paste it into the chat instead.")
        sys.exit(1)
    print(text)


def cmd_jds(out_dir, urls):
    """Fetch several JDs at once (threads: the work is network-bound). One file per URL, in input order."""
    from concurrent.futures import ThreadPoolExecutor
    os.makedirs(out_dir, exist_ok=True)
    with ThreadPoolExecutor(max_workers=min(8, len(urls))) as ex:
        texts = list(ex.map(get_jd, urls))
    for n, (url, text) in enumerate(zip(urls, texts), 1):
        path = os.path.join(out_dir, f"jd_{n}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"URL: {url}{NL}{NL}{text}")
        status = f"{len(text)} chars" if text else "FAILED (paste it into the chat)"
        print(f"jd_{n}: {status}  {path}  {url}")


# ── CV editing ───────────────────────────────────────────────────────────────

def cmd_cv():
    for i, p in enumerate(Document(BASE_CV_DOCX).paragraphs):
        if p.text.strip():
            print(f"{i}: {p.text}")


def _replace_in_runs(doc, old, new):
    for p in doc.paragraphs:
        for r in p.runs:
            if old in r.text:
                r.text = r.text.replace(old, new, 1)
                return
    raise SystemExit(f"ERROR: text not found inside a single run: {old!r}")


def _add_skills(doc, skills):
    p = next((p for p in doc.paragraphs if p.text.startswith(SKILLS_LABEL)), None)
    if p is None:
        raise SystemExit(f"ERROR: no paragraph starting with {SKILLS_LABEL!r}")
    last = next(r for r in reversed(p.runs) if r.text.strip())
    last.text = last.text.rstrip() + ", " + ", ".join(skills)


def _add_always_ai_skills(doc):
    """Add ALWAYS_AI_SKILLS (config CV_ALWAYS_AI_SKILLS) to the first line starting with one of AI_LABELS.
    With CV_REPLACE_AI_TAIL the '  |  ...' tail of that line is replaced by the skills, otherwise
    they go before the '|'. Tailored copies only; the base CV is never modified. Skips skills already present."""
    if not ALWAYS_AI_SKILLS:
        return
    p = next((p for p in doc.paragraphs if p.text.strip().startswith(AI_LABELS)), None)
    if p is None:
        print("NOTE: no AI skills line found; ALWAYS_AI_SKILLS not added")
        return
    todo = [s for s in ALWAYS_AI_SKILLS if s.lower() not in p.text.lower()]
    if not todo:
        return
    value_runs = [r for r in p.runs if r.text.strip()][1:] or [r for r in p.runs if r.text.strip()]
    for r in value_runs:                                   # the run holding the '|' separator, if any
        if "|" in r.text:
            head, sep, tail = r.text.partition("|")
            r.text = head.rstrip() + ", " + ", ".join(todo) + ("" if REPLACE_AI_TAIL else "  " + sep + tail)
            return
    last = value_runs[-1]
    last.text = last.text.rstrip() + ", " + ", ".join(todo)


def _export_pdf(docx_path):
    import win32com.client
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    try:
        d = word.Documents.Open(docx_path, ReadOnly=True)
        pages = d.ComputeStatistics(2)  # wdStatisticPages
        d.ExportAsFixedFormat(docx_path[:-5] + ".pdf", 17)  # wdExportFormatPDF
        d.Close(False)
    finally:
        word.Quit()
    return pages


def word_diff(base_path, new_path):
    """Changed words per paragraph: [-removed-] {+added+}."""
    import difflib
    base = [p.text for p in Document(base_path).paragraphs]
    new = [p.text for p in Document(new_path).paragraphs]
    for i, (a, b) in enumerate(zip(base, new)):
        if a == b:
            continue
        aw, bw = a.split(), b.split()
        parts = []
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, aw, bw).get_opcodes():
            if op == "equal":
                continue
            ctx = " ".join(aw[max(0, i1 - 2):i1])
            old = " ".join(aw[i1:i2])
            new_ = " ".join(bw[j1:j2])
            parts.append(f"...{ctx} " + (f"[-{old}-] " if old else "") + (f"{{+{new_}+}}" if new_ else ""))
        print(f"Para {i}: " + "  |  ".join(parts))


def _build_docx(company, edits, base_path):
    """Apply edits to a copy of base_path and save it as RESUME_OUTPUT_DIR/resume_<company>.docx."""
    from resume_tailor import safe_company_name
    doc = Document(base_path)
    for e in edits.get("replace", []):
        _replace_in_runs(doc, e["old"], e["new"])
    if edits.get("add_skills"):
        _add_skills(doc, edits["add_skills"])
    _add_always_ai_skills(doc)
    ai_base = getattr(config, "BASE_CV_DOCX_AI", "")
    if ai_base and os.path.normcase(os.path.abspath(base_path)) == os.path.normcase(os.path.abspath(ai_base)):
        for e in AI_DEFAULT_REPLACE:
            try:
                _replace_in_runs(doc, e["old"], e["new"])
            except SystemExit:
                print(f"NOTE: AI default edit skipped, text not found: {e['old']!r}")
    os.makedirs(config.RESUME_OUTPUT_DIR, exist_ok=True)
    out = os.path.join(config.RESUME_OUTPUT_DIR, f"resume_{safe_company_name(company)}.docx")
    doc.save(out)
    return out


def _report(out, pages, base_path):
    print(f"Saved: {out[:-5]}.pdf{NL}Pages: {pages}{NL}{NL}Words changed:")
    word_diff(base_path, out)
    os.remove(out)  # only the PDF is kept


def cmd_apply(company, edits_path):
    with open(edits_path, encoding="utf-8") as f:
        edits = json.load(f)
    out = _build_docx(company, edits, BASE_CV_DOCX)
    _report(out, _export_pdf(out), BASE_CV_DOCX)


def cmd_apply_batch(batch_path, workers=3):
    """Edit every CV first (fast, and an edit error stops the batch before any PDF is made), then
    export the PDFs in parallel: each worker process drives its own Word instance."""
    from concurrent.futures import ProcessPoolExecutor
    with open(batch_path, encoding="utf-8") as f:
        jobs = json.load(f)
    bases = {"main": BASE_CV_DOCX, "ai": getattr(config, "BASE_CV_DOCX_AI", "")}
    built = []
    for j in jobs:
        base = bases.get(j.get("base", "main"))
        if not base or not os.path.exists(base):
            raise SystemExit(f"ERROR: base CV {j.get('base')!r} not found for {j['company']!r}")
        built.append((j["company"], _build_docx(j["company"], j.get("edits", {}), base), base))
    with ProcessPoolExecutor(max_workers=max(1, min(workers, len(built)))) as ex:
        futures = [ex.submit(_export_pdf, out) for _, out, _ in built]
        results = []
        for f in futures:
            try:
                results.append(f.result())
            except Exception as e:  # a Word instance can fail under load: retry that one alone below
                results.append(e)
    for (company, out, base), res in zip(built, results):
        pages = _export_pdf(out) if isinstance(res, Exception) else res
        print(f"{NL}=== {company} ===")
        _report(out, pages, base)


def main():
    _console_utf8()
    args = sys.argv[1:]
    if args[:1] == ["jd"] and len(args) == 2:
        cmd_jd(args[1])
    elif args == ["cv"]:
        cmd_cv()
    elif args[:1] == ["apply"] and len(args) == 3:
        cmd_apply(args[1], args[2])
    elif args[:1] == ["jds"] and len(args) >= 3:
        cmd_jds(args[1], args[2:])
    elif args[:1] == ["apply-batch"] and len(args) in (2, 4) and (len(args) == 2 or args[2] == "--workers"):
        cmd_apply_batch(args[1], int(args[3]) if len(args) == 4 else 3)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

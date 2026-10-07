"""
CV Tailor - evidence-only edits to the current CV DOCX for one job.

The comparison (which JD skills are missing, which ones the candidate confirms) is done by
the cv-tailor skill in Claude Code; this script only does the deterministic parts.

Usage:
  python cv_tailor.py jd <job-url>                 print the job description text
  python cv_tailor.py cv                           print the base CV, one paragraph per line
  python cv_tailor.py apply "<Company>" <edits.json>

edits.json:
  {"replace": [{"old": "exact text inside one run", "new": "replacement"}, ...],
   "add_skills": ["Cucumber (TDD)", "YourKit Java Profiler"]}

Output: RESUME_OUTPUT_DIR/resume_<company>.docx + .pdf (PDF via Microsoft Word).
"""

import json
import os
import sys

from docx import Document

try:
    import config
except ImportError:
    print("ERROR: config.py not found!")
    sys.exit(1)

BASE_CV_DOCX = getattr(config, "BASE_CV_DOCX", os.path.join(
    os.path.expanduser("~"), "OneDrive", "Desktop", "Resume2026", "SingleBlockResume- 2026augnew",
    "Mahashwetha_resume_2026_centurygothic_aug.docx"))
SKILLS_LABEL = "Frameworks & Tools:"


def _console_utf8():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def cmd_jd(url):
    from resume_tailor import fetch_job_description
    text = fetch_job_description(url)
    if not text or len(text.strip()) < 200:
        print("ERROR: could not fetch the job description. Paste it into the chat instead.")
        sys.exit(1)
    print(text)


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


def cmd_apply(company, edits_path):
    from resume_tailor import safe_company_name
    with open(edits_path, encoding="utf-8") as f:
        edits = json.load(f)
    doc = Document(BASE_CV_DOCX)
    for e in edits.get("replace", []):
        _replace_in_runs(doc, e["old"], e["new"])
    if edits.get("add_skills"):
        _add_skills(doc, edits["add_skills"])

    os.makedirs(config.RESUME_OUTPUT_DIR, exist_ok=True)
    out = os.path.join(config.RESUME_OUTPUT_DIR, f"resume_{safe_company_name(company)}.docx")
    doc.save(out)
    pages = _export_pdf(out)
    print(f"Saved: {out}\nSaved: {out[:-5]}.pdf\nPages: {pages}\n\nWords changed:")
    word_diff(BASE_CV_DOCX, out)


def main():
    _console_utf8()
    args = sys.argv[1:]
    if args[:1] == ["jd"] and len(args) == 2:
        cmd_jd(args[1])
    elif args == ["cv"]:
        cmd_cv()
    elif args[:1] == ["apply"] and len(args) == 3:
        cmd_apply(args[1], args[2])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

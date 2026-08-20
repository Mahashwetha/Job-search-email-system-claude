---
name: cover-letter
description: Generate a tailored cover letter for a job posting URL. Triggers on /cover-letter, "cover letter <url>", "generate cover letter for [company]", "write cover letter for [url]", "draft cover letter [company]".
---

# Cover Letter Generator

Generate a tailored cover letter using `cover_letter.py`.

## How to invoke

Slash command (preferred):
```
/cover-letter https://job-url
/cover-letter https://job-url Company Name
/cover-letter https://job-url Company Name "Role Title"
```

Or natural language: `cover letter <url>`, `generate cover letter for Constructor`

## How to run

```
python cover_letter.py "https://job-url" "Company Name" "Role Title"
python cover_letter.py "https://job-url" "Company Name"   # role extracted from JD
```

## What it does

1. Fetches the job description from the URL (same scraper as resume_tailor.py)
2. Calls Gemini to generate two tailored paragraphs:
   - **Matched skills paragraph** — specific tech/tools from the JD that the candidate has
   - **Gap bridge paragraph** — honest bridge for the 1-2 most important gaps
3. Assembles the full letter using a fixed template (intro, generated paras, fixed personal projects + close)
4. Saves DOCX to `cover_letters/CoverLetter_{Company}.docx`
5. Dumps the full text to console

## Output location

`C:\Users\mahas\OneDrive\Desktop\Applications\JobSearch\cover_letters\CoverLetter_{Company}.docx`

## Template structure (fixed)

1. Header (Paris, France | phone | email)
2. "Respected Hiring Manager,"
3. **Intro** — role, company, company value prop (Gemini-generated hook)
4. **Matched skills para** — Gemini-generated
5. **Gap bridge para** — Gemini-generated
6. **Personal projects para** — hardcoded (job pipeline + Fit-Check)
7. **Close para** — hardcoded (Paris, open to remote/hybrid, aligns with company goals)
8. Sign-off

## Steps

1. Extract URL, company, and (optional) role from user message.
2. Run the script.
3. Dump the cover letter text in the response inside a plain fenced code block (``` with no language tag) so the user gets a one-click copy button.
4. Confirm the DOCX path.

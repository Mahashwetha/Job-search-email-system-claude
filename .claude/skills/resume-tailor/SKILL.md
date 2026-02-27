---
name: resume-tailor
description: This skill should be used when the user wants to tailor or customize their resume for a specific job or company. Triggers on phrases like "tailor resume for [company]", "customize resume for [job]", "generate resume for [company]", "adapt resume to this job posting", "create resume for [company] role".
---

# Resume Tailor

Generate a per-company tailored resume using Gemini 2.5 Flash via `resume_tailor.py`.

## How to run

For a single job, run `resume_tailor.py` with the job posting URL and company name as arguments.

For batch mode (all companies with status `done` and non-LinkedIn links in the tracker), run it with no arguments.

## Output

Saved to the `resume_adjusted/` folder configured in `config.py`, named `resume_{CompanyName}.docx`. The script skips a company if the file already exists — delete the file to regenerate it.

## What it does

Fetches the job description from the URL, reads the base resume, and asks Gemini to suggest minimal tweaks — reordering skills, surfacing existing keywords. It never fabricates experience. Gemini's markdown formatting (`**bold**`) is stripped automatically before writing to the DOCX.

## Site compatibility

Most standard job pages work. Workday works via JSON-LD extraction. Ashby and internal portals (like BPCE) may fail — in that case, skip the URL and tailor manually, or paste the job description text into a temp file and adjust the call.

LinkedIn URLs are skipped automatically in batch mode.

## If you hit rate limits

The free Gemini tier occasionally returns 429 errors — the script retries automatically. If it keeps failing, wait a minute and re-run. Use `gemini-2.5-flash`, not `gemini-2.0-flash` (that quota runs out faster).

---
name: resume-tailor
description: This skill should be used when the user wants to tailor or customize their resume for a specific job or company. Triggers on phrases like "tailor resume for [company]", "customize resume for [job]", "generate resume for [company]", "adapt resume to this job posting", "create resume for [company] role".
---

# Resume Tailor

Generate a per-company tailored resume DOCX using Gemini 2.5 Flash via `resume_tailor.py`.

## Usage

### Single job (most common)
```bash
cd C:/Users/mahas/Learnings/claude-job-agent
python resume_tailor.py "https://job-posting-url" "Company Name"
```

### Batch (all 'done' status companies in tracker with non-LinkedIn links)
```bash
python resume_tailor.py
```

## Output
Saved to:
```
C:\Users\mahas\OneDrive\Desktop\Applications\JobSearch\resume_adjusted\resume_{CompanyName}.docx
```

**Idempotent**: skips if the output file already exists. To regenerate, delete the existing file first.

## What it does
- Fetches the job description from the URL
- Reads base resume from `resume\mahashwetharao_2025resume_Dec_English.docx`
- Asks Gemini to suggest minimal tweaks: skill reordering, keyword surfacing
- **Never fabricates experience** — only reorders and surfaces existing skills
- Strips any `**markdown**` formatting Gemini adds before writing to DOCX

## Known site compatibility
| Site type | Status |
|-----------|--------|
| Workday | Works (JSON-LD extraction) |
| Standard HTML job pages | Works |
| Ashby | May need manual copy-paste of JD |
| BPCE/internal portals | May need Selenium or skip |
| LinkedIn job pages | Skipped (batch mode filters these out) |

## If the URL is JS-rendered and fails
Pass the job description text directly — copy the JD from the browser and paste it into a temp `.txt` file, then modify the call or paste directly when prompted. Alternatively, skip and tailor manually.

## Rate limits
- Gemini free tier: 5s delay between calls in batch mode
- On 429 error: script retries automatically
- Model used: `gemini-2.5-flash` (not `gemini-2.0-flash` — that quota exhausts faster)

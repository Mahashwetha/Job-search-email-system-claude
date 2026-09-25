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
python cover_letter.py "https://job-url" "Company Name" "Role Title" --referral "Name, their role"
```

Use `--referral` whenever the user mentions a referral (someone at the company recommended her): the opening line then names the referrer.

## What it does

1. Fetches the job description from the URL (same scraper as resume_tailor.py)
2. Calls Gemini to generate three tailored paragraphs:
   - **Opening paragraph** — 2 sentences, never "I am writing to express my interest". Gemini picks the strongest type for the job: referral, specific achievement (only from the verified CANDIDATE ACHIEVEMENTS list in the prompt), company-specific observation, or direct capability. The code rejects banned phrases and false domain claims (NASDAQ = trade surveillance, not payments/banking) and falls back to a safe achievement-led opening; the console prints the opening type and any rejection reason.
   - **Matched skills paragraph** — specific tech/tools from the JD that the candidate has
   - **Gap bridge paragraph** — honest: states what she hasn't used, never claims she is "learning/deepening" a gap technology
3. Assembles the full letter using a fixed template (opening, generated paras, fixed personal projects + close)
4. Saves DOCX to `cover_letters/CoverLetter_{Company}.docx`
5. Dumps the full text to console

## Output location

`C:\Users\mahas\OneDrive\Desktop\Applications\JobSearch\cover_letters\CoverLetter_{Company}.docx`

## Template structure (fixed)

1. Header (Paris, France | phone | email)
2. "Respected Hiring Manager,"
3. **Opening** — Gemini-generated (achievement / company / capability / referral), validated in code
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

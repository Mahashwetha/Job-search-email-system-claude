---
name: new-job
description: This skill should be used when the user wants to add a new company or job to their Excel tracker (List.xlsx). Triggers on phrases like "add [company] to tracker", "I applied to [company]", "track [company]", "save [company] for later", "add [company] [role]", "new application at [company]".
---

# Add New Job to Tracker

Add a new row to `List.xlsx` (Sheet1) with the bundled script. Do not write ad hoc openpyxl code.

## Column layout
- A: Company name
- B: Role title
- C: Role link (job posting URL, without tracking redirects; `/thanks` pages are fine)
- D: Status
- E: HR contact (leave empty; use the update-hr skill)
- F: Comments (optional)

## Status values
- `done` = applied (default)
- `In progress` = ONLY when a callback/response was received
- `Rejected` = only when logging a rejection for a job that was never tracked

## Steps
1. Get the company name (required), role title and job URL. If the user only pasted a link, fetch the page (or the ATS public API: Ashby/Lever/Greenhouse) to get company and role.
2. Run from the project root (`C:/Users/mahas/Learnings/claude-job-agent`):
   ```
   python .claude/skills/new-job/scripts/add_job.py --company "Company" --role "Role" --url "https://..." [--status done] [--comment "..."]
   ```
3. Handle the result:
   - `ADDED: row N` (exit 0) → confirm company, role, status and row to the user.
   - `DUPLICATE` (exit 2) → the same job URL is already tracked; tell the user the existing row, do not add.
   - `COMPANY EXISTS` (exit 3) → show the existing rows. If it's a different role, re-run with `--force`.
   - `ERROR` (exit 1) → e.g. Excel has the file open; ask the user to close it and retry.

The script takes the shared tracker lock, backs up List.xlsx to `backups/` before writing, and matches URLs ignoring `www`, query strings, trailing slashes and `/thanks` or `/application` suffixes.

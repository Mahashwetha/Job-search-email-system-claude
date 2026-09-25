---
name: search
description: This skill should be used when the user wants to check if a company or job URL is already in their tracker, or list all applications for a company. Triggers on phrases like "have I applied to [company]", "is [company] in tracker", "check [url]", "already applied [url]", "search [company]", "what jobs do I have at [company]", "did I apply to [company]", "[company] already in tracker?".
---

# Search Tracker

Look up a company or job URL in `List.xlsx` (Sheet1). Rejected applications are rows on Sheet1 with status `Rejected` and strikethrough; the old separate "Rejected" sheet was merged into Sheet1 on 2026-09-25.

## Steps

Run the script from the project root (`C:/Users/mahas/Learnings/claude-job-agent`):

```
python .claude/skills/search/scripts/search_tracker.py "Company Name"
python .claude/skills/search/scripts/search_tracker.py "https://job-url"
```

Add `--json` for machine-readable output.

The script is read-only. It:
- matches company names case-insensitively, both ways (`query in company` or `company in query`), skipping empty cells
- for a URL: matches column C, including URLs inside `=HYPERLINK(...)` formulas, ignoring `www`, query strings, trailing slashes and `/thanks` or `/application` suffixes
- for a URL not found: fetches the page title, extracts the company, and searches by company
- prints row number, company, role, status (with emoji), URL and comments

Show the script output to the user. Do not write ad hoc openpyxl code for searches.

## Status emoji mapping (used by the script)
- `done` / `applied` → ✅ Applied
- `in progress` / `under review` → 🕐 In Progress
- `rejected` → ❌ Rejected
- `not available` / `nothing to apply` → ⏸️ No Jobs Available
- empty / other → ⬜ Not Contacted

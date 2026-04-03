---
name: search
description: This skill should be used when the user wants to check if a company or job URL is already in their tracker, or list all applications for a company. Triggers on phrases like "have I applied to [company]", "is [company] in tracker", "check [url]", "already applied [url]", "search [company]", "what jobs do I have at [company]", "did I apply to [company]", "[company] already in tracker?".
---

# Search Tracker

Look up a company or URL across **both sheets** of `List.xlsx` (Sheet1 = active applications, Rejected = rejected/closed applications).

## What to do based on input

### User gives a URL
1. Open `List.xlsx` with openpyxl (use temp copy if PermissionError).
2. Search column C in **both sheets** for that URL (exact or substring match). Also handle cells with `=HYPERLINK(...)` formula — extract the URL from inside the formula.
3. If found → show all matching rows (see Output Format below).
4. If not found → use `requests` to fetch the page and extract the `<title>` tag. Parse the company name from the title (format is usually `"Job Title - Company | Platform"`). Then search column A in both sheets by that company name.
5. Report clearly: "Not in tracker" if nothing matches after both attempts.

### User gives a company name only
1. Open `List.xlsx` with openpyxl (use temp copy if PermissionError).
2. Search column A in **both sheets** — case-insensitive substring match.
3. Show all matching rows across both sheets (see Output Format below).
4. Report "Not in tracker" if nothing found.

## Output Format

Group results by sheet, show row number, company, role, status (with emoji), URL, and any comments:

```
Found 3 match(es) for "Theodo":

  [Sheet1]
    Row 45 — Theodo | AI Engineer | ✅ Applied
             URL: https://welcometothejungle.com/...
    Row 67 — Theodo | Tech Lead | 🕐 In Progress
             URL: https://...

  [Rejected]
    Row 12 — Theodo | Backend Engineer | ❌ Rejected
             Note: French required
```

Status emoji mapping:
- `done` / `applied` → ✅ Applied
- `in progress` / `under review` → 🕐 In Progress
- `rejected` → ❌ Rejected
- `not available` / `nothing to apply` → ⏸️ No Jobs Available
- empty / other → ⬜ Not Contacted

Always show the Comments column (col F) if it has content — it often has useful notes like "Job posting CLOSED" or "French required".

## Rules
- Always search BOTH sheets — Sheet1 and Rejected.
- Skip header row (row 1) when iterating.
- Company match is case-insensitive substring both ways: `query in company` OR `company in query`.
- For URL search, also check if the URL is wrapped in a HYPERLINK formula.
- If the user gave a URL that's not in the tracker, always attempt to identify the company from the page before saying "not found".

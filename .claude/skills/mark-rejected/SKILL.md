---
name: mark-rejected
description: This skill should be used when the user wants to mark a company as rejected in their Excel job tracker (List.xlsx). Triggers on phrases like "mark [company] as rejected", "reject [company] in the tracker", "[company] rejected me", "strikethrough [company]", "update [company] to rejected", "I got rejected by [company]", "remove [company] from active".
---

# Mark Company as Rejected

Updates `List.xlsx` for a company: sets column D to `"Rejected"` and applies strikethrough font across columns A–F.

## Run the script

```bash
cd C:/Users/YOU/Learnings/claude-job-agent
python .claude/skills/mark-rejected/scripts/mark_rejected.py "Company Name"
```

Matching is **case-insensitive substring** — `"stripe"` matches `"Stripe"`, `"Stripe EMEA"`, etc.

## What the script does
1. Finds all rows where column A contains the company name (substring match)
2. Sets column D to `"Rejected"`
3. Applies strikethrough font to columns A–F, preserving existing font properties (bold, size, color)
4. Handles `PermissionError` via temp copy if List.xlsx is open in Excel
5. Saves and reports rows updated

## After running
- Verify the output shows the correct row number and company name
- If multiple rows matched unexpectedly, the company name substring was too broad — manually revert unwanted rows in Excel
- The daily email will automatically reflect the ❌ Rejected status on next run

## Manual alternative (if script fails)
1. Open `List.xlsx`
2. Find the company row
3. Type `Rejected` in column D
4. Select cells A–F in that row → `Ctrl+1` → Font tab → check Strikethrough
5. Save

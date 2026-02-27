---
name: mark-rejected
description: This skill should be used when the user wants to mark a company as rejected in their Excel job tracker (List.xlsx). Triggers on phrases like "mark [company] as rejected", "reject [company] in the tracker", "[company] rejected me", "strikethrough [company]", "update [company] to rejected", "I got rejected by [company]", "remove [company] from active".
---

# Mark Company as Rejected

Update `List.xlsx` for a company that rejected you: set column D to `Rejected` and apply strikethrough formatting across columns A–F.

## Steps

Run the bundled script at `.claude/skills/mark-rejected/scripts/mark_rejected.py` with the company name as the argument, from the project root.

The script finds all rows where column A contains the company name (case-insensitive substring match), sets column D to `Rejected`, applies strikethrough to columns A–F while preserving existing font properties, and saves the file. It handles `PermissionError` automatically via a temp copy if the file is open in Excel.

## After running

Check the output — it reports the row number and company name for each row updated. If multiple unexpected rows matched, the company name was too broad. Revert any wrong rows manually in Excel (remove strikethrough, restore the original status).

The daily email will automatically show ❌ Rejected for that company on the next run.

## If the script fails

Open `List.xlsx` manually, find the company row, type `Rejected` in column D, select cells A–F, open Format Cells (`Ctrl+1`), go to the Font tab, and check Strikethrough.

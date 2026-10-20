---
name: mark-rejected
description: This skill should be used when the user wants to mark a company as rejected in their Excel job tracker (List.xlsx). Triggers on phrases like "mark [company] as rejected", "reject [company] in the tracker", "[company] rejected me", "strikethrough [company]", "update [company] to rejected", "I got rejected by [company]", "remove [company] from active", "rejected [company]", rejected [company] [role]".
---

# Mark Company as Rejected

Update `List.xlsx` for a company that rejected you: set column D to `Rejected` and apply strikethrough formatting across columns A–F.

## Steps

Run the bundled script at `.claude/skills/mark-rejected/scripts/mark_rejected.py` with the company name as the argument, from the project root.

By default the script finds all rows where column A contains the company name (case-insensitive substring match), sets column D to `Rejected`, applies strikethrough to columns A–F while preserving existing font properties, and saves the file (lock + backup first). It handles `PermissionError` automatically via a temp copy if the file is open in Excel.

Optional filters (combine freely, all must hold):

| Flag | Effect |
|---|---|
| `--dry-run` | List the rows that would change (and the company's other rows that the filters exclude). Changes nothing. |
| `--role "text"` | Only rows whose column B (role) contains the text, case-insensitive. |
| `--row N` | Only that exact row number. Repeatable (`--row 42 --row 57`). Column A must still match the company, otherwise nothing is changed. |
| `--exact` | Column A must equal the company name (case-insensitive) instead of containing it. Use for short names, e.g. `"Alan"` would otherwise also hit `"Talan"`. |

### When a company has several rows

If the company has more than one active application, or the name is short enough to match other companies, **run with `--dry-run` first**:

```
python .claude/skills/mark-rejected/scripts/mark_rejected.py "Alan" --exact --dry-run
```

Then mark only the rejected ones with `--role` (if the user named the role) or `--row` (pick the row numbers from the dry-run output):

```
python .claude/skills/mark-rejected/scripts/mark_rejected.py "Alan" --exact --role "backend"
python .claude/skills/mark-rejected/scripts/mark_rejected.py "Alan" --exact --row 42 --row 57
```

If it is unclear which of several roles was rejected, show the dry-run list to the user and ask.

Exit codes: `0` updated / dry-run listed, `4` no match (or a `--row` that doesn't belong to the company), `1` error (lock timeout, file open in Excel), `2` bad arguments.

## After running

Check the output — it reports the row number and company name for each row updated. If multiple unexpected rows matched, the company name was too broad. Revert any wrong rows manually in Excel (remove strikethrough, restore the original status).

The daily email will automatically show ❌ Rejected for that company on the next run.

## If the script fails

Open `List.xlsx` manually, find the company row, type `Rejected` in column D, select cells A–F, open Format Cells (`Ctrl+1`), go to the Font tab, and check Strikethrough.

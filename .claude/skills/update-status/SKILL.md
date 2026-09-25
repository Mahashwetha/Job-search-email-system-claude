---
name: update-status
description: This skill should be used when the user wants to change the status of a job already in the tracker (List.xlsx), especially after a company responds. Triggers on phrases like "[company] called me back", "[company] replied", "got an interview with [company]", "move [company] to in progress", "set [company] to in progress", "mark [company] as done/applied again", "undo rejection for [company]".
---

# Update Job Status

Change the status of an existing tracker row with the bundled script. For rejections the mark-rejected skill still works; this script is for everything else (and can also set Rejected on one specific row).

## Status values
- `done` = applied
- `In progress` = ONLY when the company called back / replied / scheduled an interview
- `Rejected` = rejected (adds strikethrough)

## Steps
Run from the project root (`C:/Users/mahas/Learnings/claude-job-agent`):
```
python .claude/skills/update-status/scripts/update_status.py --company "Galadrim" --status "In progress" --note "phone screen booked"
python .claude/skills/update-status/scripts/update_status.py --row 352 --status "In progress"
```
- Add `--dry-run` to preview.
- If the output says `AMBIGUOUS` (the company has several rows), show the rows and ask which role, then re-run with `--row N` (or `--all` if the user means all of them).
- `--note` is optional; it is appended to the comments column as `YYYY-MM-DD: note`, keeping existing comments.

The script takes the shared tracker lock, backs up List.xlsx first, adds strikethrough for `Rejected` and removes it for any other status.

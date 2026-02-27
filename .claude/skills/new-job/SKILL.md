---
name: new-job
description: This skill should be used when the user wants to add a new company or job to their Excel tracker (List.xlsx). Triggers on phrases like "add [company] to tracker", "I applied to [company]", "track [company]", "save [company] for later", "add [company] [role]", "new application at [company]".
---

# Add New Job to Tracker

Add a new row to `List.xlsx` (the job application tracker at the path in `config.py → TRACKER_FILE`).

## Column layout
- A: Company name
- B: Role title
- C: Role link (job posting URL)
- D: Status
- E: HR contact (leave empty)
- F: Comments (leave empty)

## Status values
- Default (applied): `done`
- Save for later / not yet applied: `In progress`

If the user doesn't specify, use `done`.

## Steps
1. Ask the user for any missing info: company name (required), role title, job URL. If they provided it already, skip asking.
2. Open `List.xlsx` using openpyxl. Handle `PermissionError` by working from a temp copy.
3. Use the first sheet (`wb.active` at load time — read it before any writes to avoid sheet-shift bugs).
4. Append the new row at the bottom: Company, Role, URL, Status, empty, empty.
5. Save the file.
6. Confirm to the user: company name, role, status, and which row it was added to.

## Things to check
- If the company already exists in the tracker, mention it and ask if they still want to add a new row (they may have a different role).
- Leave columns E and F empty — HR contacts are managed separately via the update-hr workflow.

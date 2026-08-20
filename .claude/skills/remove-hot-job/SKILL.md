---
name: remove-hot-job
description: This skill should be used when the user wants to remove, clear, or blocklist jobs from the Hot Jobs section of the daily email. Triggers on phrases like "remove [company] from hot jobs", "clear hot jobs for [category]", "blocklist [company] hot job", "remove all senior java hot jobs", "clear [category] hot jobs", "I applied to [company] from hot jobs".
---

# Remove Hot Jobs

Manage the hot jobs list in `daily_hot_jobs.json`. Hot jobs are sticky LinkedIn listings shown at the top of the daily email, 5 per category (or 8 for Tech Lead / AI categories).

## Key concepts

- **current_jobs**: dict of category → list of job objects. Clear a slot by removing from this list — it backfills on next run.
- **blocklist**: list of `[company, title]` pairs. Blocklisted jobs never reappear in that category.
- If a job was **applied to** (company is in the tracker), do NOT blocklist it — the system auto-removes tracker companies naturally.
- If a job is being **dismissed without applying**, blocklist it so it doesn't come back.

## Categories (exact keys in JSON)
- `Senior Java`
- `Backend Java`
- `Product Owner`
- `Assistant Project Manager`
- `Tech Lead / Lead Developer`
- `AI / GenAI Engineer`

## What to do based on what the user says

**Remove a single job** (applied or dismissed) — remove it from `current_jobs[category]`. If dismissed (not applied), also add `[company.lower(), title.lower()]` to `blocklist`.

**Clear all jobs in a category** — set `current_jobs[category] = []`. For each job, blocklist it unless the user says they applied to it (or it's already in the tracker).

**Remove from blocklist** — find and delete the matching `[company, title]` pair from the `blocklist` array.

**List current hot jobs for a category** — read and print `current_jobs[category]`.

## Steps

1. If the user didn't specify which jobs they applied to vs dismissed, ask — applied jobs should NOT be blocklisted.
2. For each job to blocklist, run the script:
   ```
   python .claude/skills/remove-hot-job/scripts/blocklist_job.py "Company Name" "Job Title"
   ```
   Run from the project root (`C:/Users/mahas/Learnings/claude-job-agent`).
   - Title is optional — omit to blocklist all jobs from that company.
   - The script removes from `current_jobs` AND adds to blocklist in one shot.
   - Uses `ensure_ascii=False` so no encoding issues.
3. Confirm output to the user: removed from current_jobs + blocklisted.

## Important notes
- Clearing slots triggers backfill on the next daily run (11:00 AM).
- Do NOT run the daily script after editing — changes take effect on the next scheduled run.
- Never manually edit `daily_hot_jobs.json` — always use the script to avoid encoding errors.

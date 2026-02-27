---
name: test-run
description: This skill should be used when the user wants to manually trigger, test, or run the job search scripts — either the daily job search email or the remote job search email. Triggers on phrases like "run daily jobs", "test the remote search", "trigger the job email", "run it manually", "send the job digest now", "test remote job search".
---

# Test Run — Manual Script Execution

Manually trigger the daily or remote job search scripts outside their scheduled runs. Run all commands from the project root: `C:/Users/mahas/Learnings/claude-job-agent`.

## Daily job search

Run `daily_job_search.py`. This reads `List.xlsx`, fetches hot jobs from LinkedIn, and sends the styled HTML digest email.

To force a full hot jobs refresh (re-fetch everything), delete `daily_hot_jobs.json` before running.

## Remote job search

Run `remote_search/remote_job_search.py`.

**Always add `--no-save` for test runs.** Without it, `previous_jobs.json` gets overwritten and the NEW flag detection breaks for the real scheduled run. The Excel file still gets updated either way.

Only omit `--no-save` when running for real (i.e. as a substitute for the scheduled run).

## Common issues
- `config.py not found` — copy `config.template.py` to `config.py` and fill in credentials.
- `PermissionError` on Excel — the script handles this with a temp copy fallback, but closing `List.xlsx` first is cleaner.
- Email not received — check spam, verify `EMAIL_CONFIG` in `config.py`.

---
name: test-run
description: This skill should be used when the user wants to manually trigger, test, or run the job search scripts — either the daily job search email or the remote job search email. Triggers on phrases like "run daily jobs", "test the remote search", "trigger the job email", "run it manually", "send the job digest now", "test remote job search".
---

# Test Run — Manual Script Execution

Manually trigger the daily or remote job search scripts outside their scheduled runs.

## Script locations (run from project root)
```
cd C:/Users/mahas/Learnings/claude-job-agent
```

---

## Daily Job Search

Fetches jobs from LinkedIn/Indeed for Paris roles, reads Excel tracker, sends styled HTML email.

```bash
python daily_job_search.py
```

**What happens:**
- Reads `List.xlsx` for tracked companies and their statuses
- Searches hot job categories (Senior Java, Backend Java, PO, Asst PM, Tech Lead, AI/GenAI)
- Sends HTML digest email to configured address
- Updates `daily_hot_jobs.json` (sticky job state)

**To force full refresh** (re-fetch all hot jobs): delete `daily_hot_jobs.json` first.

---

## Remote Job Search

Fetches remote/EMEA roles from RemoteOK, Remotive, Arbeitnow, WWR, Jobicy, LinkedIn.

```bash
python remote_search/remote_job_search.py --no-save
```

**Always use `--no-save` for test runs.** This prevents overwriting `previous_jobs.json`, so the NEW flag detection stays accurate for the real scheduled run.

**What happens:**
- Fetches from all remote sources
- Filters against `rejected_remote.json` blocklist
- Appends new entries to `remote_search/remote.xlsx`
- Sends HTML digest email
- With `--no-save`: skips updating `previous_jobs.json`

**To run for real** (update state, mark jobs as seen):
```bash
python remote_search/remote_job_search.py
```

---

## Common issues
- `config.py not found` — copy `config.template.py` to `config.py` and fill in credentials
- `PermissionError` on Excel — close `List.xlsx` in Excel first (or script uses temp copy fallback)
- Email not received — check spam, verify `EMAIL_CONFIG` in `config.py`

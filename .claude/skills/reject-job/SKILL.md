---
name: reject-job
description: This skill should be used when the user wants to reject, hide, or filter out a remote job from future email digests. Triggers on phrases like "reject this job", "hide [company]", "add to reject list", "don't show [company] again", "remove [company] from results", or when reviewing remote job emails and marking jobs as not relevant.
---

# Reject Remote Job

Manage the remote jobs blocklist. Jobs on this list are filtered out of all future remote job emails.

The blocklist lives in `remote_search/rejected_remote.json` and is managed via `remote_search/reject_remote.py` (run from the project root).

## What to do based on what the user says

**Reject a specific job** — run the script with company name and job title as arguments.

**Reject all roles from a company** — run the script with the company name and an empty string as the title.

**Reject everything from the last email** — run the script with `--all`. This bulk-rejects all jobs from `previous_jobs.json` (the last run).

**Restore a rejected job** — run the script with `--remove` followed by the company and title.

**Show all rejections** — run the script with `--list`.

## Matching rules — important
- Matching is case-insensitive substring. "grafana" matches "Grafana Labs".
- Special characters (é, ®, ™) must match exactly — double-check character by character if a company name has accents or symbols.
- An empty title rejects all roles from that company permanently.
- To undo, use `--remove` with the exact same strings used when adding.

## Steps
1. Identify what the user wants to reject (company, title, or both).
2. Double-check the company name spelling, especially for special characters.
3. Run the appropriate script command.
4. Confirm the output shows the entry was added and the new total count.

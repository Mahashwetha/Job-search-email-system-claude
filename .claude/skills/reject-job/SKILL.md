---
name: reject-job
description: This skill should be used when the user wants to reject, hide, or filter out a remote job from future email digests. Triggers on phrases like "reject this job", "hide [company]", "add to reject list", "don't show [company] again", "remove [company] from results", or when reviewing remote job emails and marking jobs as not relevant.
---

# Reject Remote Job

Manage the rejected remote jobs blocklist via `remote_search/reject_remote.py`. Jobs on this list are filtered out of all future remote job emails.

## Script location
`remote_search/reject_remote.py` — run from the project root:
```
cd C:/Users/mahas/Learnings/claude-job-agent
python remote_search/reject_remote.py <args>
```

## Commands

| Intent | Command |
|--------|---------|
| Reject a specific job | `python remote_search/reject_remote.py "company" "title"` |
| Reject all roles from a company | `python remote_search/reject_remote.py "company" ""` |
| Reject everything from last run | `python remote_search/reject_remote.py --all` |
| Restore a rejected job | `python remote_search/reject_remote.py --remove "company" "title"` |
| Show all rejections | `python remote_search/reject_remote.py --list` |

## Matching rules (important)
- Matching is **case-insensitive substring** — "grafana" matches "Grafana Labs"
- Special characters (é, ®, ™) in company names must match exactly — verify character-by-character
- Leaving title as `""` rejects **all** roles from that company permanently
- To undo, use `--remove` with the exact same company/title strings used when adding

## Workflow
1. User mentions a job to reject (company + title, or just company)
2. Confirm the exact company name spelling (check for accents, special chars)
3. Run the reject command
4. Confirm output shows "Added: ..." with the new total count

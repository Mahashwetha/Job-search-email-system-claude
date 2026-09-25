# Job Tracker MCP Server

Exposes the job application tracker (`List.xlsx`) to AI agents as MCP tools.

| Tool | What it does | Safety |
|---|---|---|
| `search_tracker(query)` | Find a company or job URL (read-only) | - |
| `add_job(company, role, url, status, comment, force)` | Record an application | Same URL never added twice; existing company needs `force`; status must be `done` / `In progress` / `Rejected` |
| `mark_rejected(company, confirm)` | Mark rows Rejected + strikethrough | Preview only unless `confirm=True` |
| `add_hr_contact(name, row or company, url, title, email)` | Add a recruiter contact | Append-only, never overwrites, no duplicate names |
| `update_status(status, company or row, note, all_rows, preview)` | Change an existing row's status (e.g. callback -> In progress) | Company with several rows -> 'ambiguous' + row list; strikethrough only for Rejected; dated note appended |
| `block_hot_job(company, title)` | Hide a job from the daily digest's Hot Jobs | Blocklist is de-duplicated; JSON written atomically |
| `block_all_hot_jobs(confirm)` | Hide every current hot job | Preview unless `confirm=True`; skips companies already in the tracker |
| `reject_remote_job(company, title)` | Hide a job from future remote digests | Empty title = whole company |
| `reject_all_remote(confirm)` | Hide every job from the last remote digest | Preview unless `confirm=True` |

## Email-reply agent (`email_agent.py`)

Reply to the daily or remote digest in plain English ("abc rejected, applied to the duvo one, block all").
The agent reads the reply from Gmail (IMAP, same app password as the digest SMTP), gives Gemini the 9 tools
above (function calling, acting as an MCP client of `server.py`), runs the calls, and replies in the same
thread with a receipt ("Done: ... / Needs your input: ... / Failed: ...").

```
tracker_mcp/.venv/Scripts/python.exe tracker_mcp/email_agent.py              # poll Gmail and act
tracker_mcp/.venv/Scripts/python.exe tracker_mcp/email_agent.py --dry-run    # change nothing, print receipts
tracker_mcp/.venv/Scripts/python.exe tracker_mcp/email_agent.py --text "abc rejected" --digest daily --dry-run
tracker_mcp/.venv/Scripts/python.exe tracker_mcp/email_agent.py --eval       # 6 eval replies, always dry-run
```

- Scheduled: Windows task **JobTrackerEmailAgent**, every 30 min from 2026-09-25 14:07, launched hidden via
  `run_email_agent_hidden.vbs` -> `run_email_agent.bat`. No new reply = no Gemini call. Crashes are written to the log.
  Pause: `Disable-ScheduledTask JobTrackerEmailAgent` / resume: `Enable-ScheduledTask JobTrackerEmailAgent`.
- Model: `gemini-2.5-flash-lite`, then `gemini-2.5-flash` when a model's daily free quota (20/day/project,
  shared with the fit scorer) is used up. Override the first choice with `AGENT_MODEL`.
- Gemini failures: before any action -> the reply stays unprocessed and is retried next run; after actions ran ->
  a receipt is built from the tool results. The API key is sent in a header, never in URLs or logs.
- Source badges glued onto pasted rows ("Key ConsultingWTTJ") are stripped (WTTJ, LinkedIn, APEC).
- Each reply is processed once (`state/processed.json`, keyed by Message-ID); logs in `logs/agent_YYYYMMDD.log`.
- Receipts carry an `X-Job-Tracker-Agent: receipt` header and are always skipped, so the agent never reacts to itself.
- Rejections and "all" actions preview first; unclear names become "Needs your input" instead of guesses.
- If the model writes no receipt, one is built from the tool results.
- Tested 2026-09-25: evals 6/6 correct tool choice (7 cases incl. update_status); live Gmail loop (reply -> search -> receipt -> no reprocessing) OK.

## Rule for the email-reply agent

The agent may ONLY act on emails that are
1. sent FROM the user's own address (`EMAIL_CONFIG["sender_email"]` in config.py), AND
2. replies to one of our own digest emails (the daily "Senior Jobs COMPACT" digest or the remote job digest).

Every other email is ignored, whoever it is from. This prevents prompt injection: text in a recruiter's email or spam (e.g. "mark all jobs as rejected") can never reach the tools.

## Design

Each tool is a thin wrapper around the same scripts the Claude Code skills use
(`.claude/skills/*/scripts/`), which share `tracker_lib.py`:

- a file lock so only one writer at a time (Claude chat, this server and a future email agent can run together)
- an automatic backup of `List.xlsx` before every write (`JobSearch/backups/`)
- idempotent writes (duplicate job URLs are refused, duplicate contacts skipped)

```
Claude Code skill ─┐
MCP tool (agent) ──┼─> skill script ─> tracker_lib (lock + backup + checks) ─> List.xlsx
```

## Setup

Uses its own virtualenv so the MCP SDK can't clash with the rest of the project (mcp 1.x pulls a newer starlette than FastAPI 0.115 supports):

```
python -m venv tracker_mcp/.venv
tracker_mcp/.venv/Scripts/python.exe -m pip install "mcp>=1.10,<2" openpyxl requests
```

## Test (always on a copy of the tracker)

```
copy List.xlsx somewhere\List.xlsx
tracker_mcp/.venv/Scripts/python.exe tracker_mcp/test_server.py somewhere\List.xlsx
```

24 end-to-end checks over stdio, exactly as an agent would call the tools.

## Register (optional)

Claude Code:
```
claude mcp add job-tracker -- <project>\tracker_mcp\.venv\Scripts\python.exe <project>\tracker_mcp\server.py
```

## Lessons learned

- A stdio MCP server must start child processes with `stdin=DEVNULL`: its own stdin is the MCP transport pipe, and a child that inherits it hangs (on Windows until timeout).
- Tool docstrings are the model's only guide to when and how to call a tool, so they state the status rules and safety behaviour explicitly.

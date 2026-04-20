---
name: send-outreach
description: This skill should be used when the user wants to send a cold outreach or follow-up email to an HR contact at a company. Triggers on phrases like "send outreach to [name] at [company]", "email HR at [company]", "send cold email to [name]", "outreach [company]", "send mail to [name] [email]", "reach out to [company] HR", "email [name] from [company]", "send outreach email".
---

# Send HR Outreach Email

Send a personalised cold outreach email with resume + portfolio attached using `send_outreach_emails.py`.

## Script location

```
C:\Users\mahas\Learnings\claude-job-agent\send_outreach_emails.py
```

## What you need from the user

| Argument | Required | Notes |
|---|---|---|
| `--name` | Yes | HR contact full name (e.g. "Andrea Smith") |
| `--email` | Yes | HR contact email address |
| `--company` | Yes | Company name exactly as in tracker (used for role lookup) |
| `--cc` | No | CC email address (e.g. second recruiter) |

If the user hasn't provided all required info, ask for it before running.

## Steps

### 1 — Preview first (dry run to user's inbox)

Always send a test to `mahashwetha91@gmail.com` first so the user can approve the email:

```bash
cd "C:\Users\mahas\Learnings\claude-job-agent"
echo yes | python send_outreach_emails.py --name "[NAME]" --email "mahashwetha91@gmail.com" --company "[COMPANY]"
```

Show the preview output to the user and ask: **"Looks good? Send to the real recipient?"**

### 2 — Send to real recipient (only after user confirms)

```bash
cd "C:\Users\mahas\Learnings\claude-job-agent"
echo yes | python send_outreach_emails.py --name "[NAME]" --email "[EMAIL]" --company "[COMPANY]"
```

Add `--cc "[CC_EMAIL]"` if a CC was provided.

## What the script does automatically

- Looks up the role from `List.xlsx` (matches company name, status = `done`)
- If found in tracker → fills `{role}` placeholder with the actual role title
- If not in tracker → sets role to `[Company] opportunities`
- Always uses `cold_outreach_template.txt` (Jinka-style with bullet points)
- Attaches both PDFs from `resume/` folder
- Shows full preview before sending

## Rules

- **Never skip the test send step** — always preview to user's inbox first
- **Never send to real recipient without explicit user approval** after the test
- If the script errors on missing attachment, check that `resume/` folder has both PDFs
- If template not found, check that `emailoutreach/cold_outreach_template.txt` exists
- Do not hardcode HR contact details anywhere in code or skill files

---
name: send-outreach
description: This skill should be used when the user wants to send a cold outreach or follow-up email to an HR contact at a company. Triggers on phrases like "send outreach to [name] at [company]", "email HR at [company]", "send cold email to [name]", "outreach [company]", "send mail to [name] [email]", "reach out to [company] HR", "email [name] from [company]", "send outreach email", "send this week's outreach emails", "send weekly outreach", "send the drafted emails".
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
- **If the job listing URL returns 404 or any error (expired/taken down), do not send the outreach email** — the role no longer exists. Either switch to the spontaneous template or skip entirely and notify the user.

---

## Weekly draft mode — "send this week's outreach emails"

Per user instruction (2026-08-17): drafts to **known/verified HR contacts** are sent automatically, no per-email confirmation. This applies to drafts produced by the weekly-hr-search routine, and to any future "draft outreach then send" workflow unless the user says otherwise.

When triggered by "send this week's outreach emails", "send weekly outreach", "send the drafted emails" — or automatically at the end of the weekly-hr-search routine right after drafts are written:

### Step 1 — Read saved drafts
Check `C:\Users\mahas\Learnings\claude-job-agent\outreach_drafts\` for `*_draft.txt` files.

Parse each file:
```
TO: {email}
SUBJECT: {subject}
---
{body}
```

### Step 2 — Send automatically
For each draft, send via `send_outreach_emails.py` (or an equivalent direct SMTP send using `cold_outreach_template.txt` + the tracker role lookup) — no confirmation prompt, no dry-run-to-self step.

Do NOT send, and instead note as skipped in the receipt (see Step 4), if:
- The contact's email is **flagged undeliverable/invalid by Hunter (or any verifier)**. Confirmed 2026-08-17: `cecile.grondin@netatmo.com` was flagged "undeliverable" by Hunter, sent anyway, and did in fact bounce/get flagged by Netatmo's mail server — so trust the verifier's "invalid/undeliverable" status and skip rather than guess-and-send.
- A guessed email has **no verification at all** (Hunter wasn't able to check it, e.g. accept-all domain) — still send it, but flag it clearly as unverified in the receipt so the user knows it's a lower-confidence guess. This is different from a confirmed-bad flag above.
- The job listing URL returns 404 or any "no longer available" signal — skip, do not send, note it in the receipt.

### Step 3 — Clean up sent drafts
After a draft sends successfully, delete that `_draft.txt` file so it doesn't appear again next week.

### Step 4 — Send a receipt email (mandatory, every run)
After sending (or attempting) all drafts, send a plain-text receipt to `mahashwetha91@gmail.com` listing, for every email actually sent:
- Company name
- Role
- HR contact name + email sent to
- Any caveat (e.g. "unverified email, watch for bounce")

And for anything skipped: company, reason skipped.

### Fallback — no drafts folder or empty
If `outreach_drafts/` doesn't exist or has no draft files, fall back to the standard single-email flow and ask the user for `--name`, `--email`, `--company`.

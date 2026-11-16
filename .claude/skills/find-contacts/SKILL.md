---
name: find-contacts
description: Find the recruiter AND the team's hiring manager for jobs, with a free Apollo search and free email building, and add them to the tracker. Triggers on "find contacts", "contacts for my picks", "find HR and hiring manager for [company]", "who should I email at [company]".
---

# Find contacts (recruiter + hiring manager)

Her favourite outreach: email BOTH the recruiter and the hiring manager of the team in the JD.
This skill finds those two people for free. It never sends anything.

## Hard rules
- **Never click "Access email" / "Access Mobile" / any reveal in Apollo** without her explicit OK for that person
  (it spends credits). Searching and reading names and titles is free. An email Apollo already shows unmasked
  (contact saved before) is free to use.
- Hunter / RocketReach only when the free steps fail (step 4). Check their credits first (Hunter `Get-Usage`,
  RocketReach `account`); a tool with 0 credits is skipped. Never Apollo API: Free plan blocks it.
- Never send email from here: drafting and sending is `/send-outreach`, with her approval.

## Which jobs
- Only a company/job she names in chat (or several). The Picks page is NOT used (she wants it unchanged), and no
  scheduled task drives Apollo.

## Step 0: Apollo session check (always first)
Open https://app.apollo.io/#/home in the in-app browser. If it shows the login page (or the pane is closed/hidden),
stop and ask her to open the browser pane (Ctrl+Shift+B) and sign in; continue once she says done. Don't fall back
to Hunter/RocketReach just because Apollo is signed out: fallback is only for when Apollo finds nobody.

## Steps (per job)
1. **Read the JD** (`python cv_tailor.py jd "<url>"`) to get the team name (e.g. "Payments Risk") and city.
2. **Apollo free search in the in-app browser** (she is signed in to app.apollo.io; if the login page shows,
   ask her to sign in, then continue). If the pane is narrow, the results table is hidden: set the viewport to
   1400x900 with `resize_window`, and reset it to `desktop` when done. Use the people search URL with filters:
   `https://app.apollo.io/#/people?page=1&qOrganizationDomainsList[]=<domain>&personLocations[]=<Paris, France | France>&personTitles[]=...`
   - Recruiter: titles `recruiter`, `talent acquisition`, `talent partner`; Paris, then France, then Europe.
     If none, an HR business partner for tech/IT.
   - Hiring manager: titles `engineering manager`, `head of engineering`, `director of engineering`,
     `software development manager`, `vp engineering`; Paris, then France. Prefer the one whose title names the
     JD's team/product. Read results with `get_page_text`.
3. **Build the email for free** (no credits):
   `..\weekly-hr-agent\.venv\Scripts\python ..\routines\pick_contacts.py email "<Company>" "<Full Name>" --domain <domain> [--known "Name=email@domain"]`
   (run from the project root; pass any real email already seen, e.g. in the tracker's
   column E or unmasked in Apollo, as `--known`). Output `verified: "unverified"` = pattern guess.
4. **Only if step 2 finds nobody or step 3 prints NO_PATTERN / BAD_NAME:** Hunter (Email-Finder / Domain-Search),
   then RocketReach, per the global lead order. Hunter Email-Verifier on a guessed email only if quota allows;
   mark `verified: "valid"` only when Hunter says valid.
5. **Write back** to the tracker column E (if the job is in List.xlsx):
     `python .claude/skills/update-hr/scripts/add_hr_contact.py --company "<Company>" --name "<Name>" --title "<Title>" --email "<email>" --url "mailto:<email>"`
6. **Report** a table: Company | Role | Recruiter (email, verified?) | Hiring manager (email, verified?) | Source.
   Then offer `/send-outreach` drafts (one per person, domain-matched), nothing sent until she approves.

---
name: update-hr
description: This skill should be used when the user wants to find, add, or update HR contacts (recruiters, talent acquisition, hiring managers) for a company in the Excel job tracker. Triggers on phrases like "find HR for [company]", "add recruiter for [company]", "search LinkedIn for [company] recruiter", "update HR contacts", "who recruits at [company]", "add this HR contact".
---

# Update HR Contacts

Find LinkedIn recruiter profiles for a company and add them to `List.xlsx` column E via `update_hr_contacts.py`.

## Workflow

### Step 1 — Search for contacts
Use WebSearch with this query template:
```
"{company}" recruiter OR "talent acquisition" OR "hiring manager" OR "HR manager" OR "people partner" Paris OR France OR EMEA site:linkedin.com/in
```

**Location priority**: Paris first → France → EMEA as fallback. Only use EMEA-level contacts when no Paris/France-specific recruiter is found. Reject India/US/APAC contacts unless the company has no EU presence.

### Step 2 — Add to HR_CONTACTS dict
Open `update_hr_contacts.py` and add the company entry to the `HR_CONTACTS` dict:

```python
"CompanyName": [
    ("Full Name", "https://www.linkedin.com/in/profile-slug/"),
    ("Second Name", "https://www.linkedin.com/in/profile-slug/"),
],
```

- Use the company name exactly as it appears in `List.xlsx` column A
- If the company already exists in the dict, append new contacts to its list
- Names with no LinkedIn URL: use `None` as the second element

### Step 3 — Run the script
```bash
cd C:/Users/mahas/Learnings/claude-job-agent
python update_hr_contacts.py
```

**What happens:**
- Script reads existing cell content in column E
- Appends only contacts whose names aren't already in the cell (idempotent)
- Sets row height + wrap text for multi-contact cells
- Creates a backup of `List.xlsx` before writing

### Step 4 — Verify
Script output shows: `Updated X rows, 0 errors`. Running twice produces 0 updates on second run.

---

## Rules
- **Append-only**: script never overwrites manually entered contacts
- **No [UNVERIFIED] prefix** — write names directly as found
- Write `HYPERLINK` formula format is handled automatically by the script
- Do NOT drag fill handle in Excel after — causes ghost rows with duplicated formulas
- To remove a contact: delete from Excel AND remove from `HR_CONTACTS` dict

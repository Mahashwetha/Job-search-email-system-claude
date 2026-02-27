---
name: update-hr
description: This skill should be used when the user wants to find, add, or update HR contacts (recruiters, talent acquisition, hiring managers) for a company in the Excel job tracker. Triggers on phrases like "find HR for [company]", "add recruiter for [company]", "search LinkedIn for [company] recruiter", "update HR contacts", "who recruits at [company]", "add this HR contact".
---

# Update HR Contacts

Find LinkedIn recruiter profiles for a company and add them to column E of `List.xlsx`.

## Step 1 — Search LinkedIn

Use WebSearch with this query:
```
"{company}" recruiter OR "talent acquisition" OR "hiring manager" OR "HR manager" OR "people partner" Paris OR France OR EMEA site:linkedin.com/in
```

Location priority: Paris first, then France, then EMEA as a fallback. Only use EMEA-level contacts when no Paris or France-specific person is found. Ignore contacts based in India, US, or APAC unless the company has no EU presence at all.

## Step 2 — Add to the HR_CONTACTS dict

Open `update_hr_contacts.py` and add or extend the company entry in the `HR_CONTACTS` dictionary. Use the company name exactly as it appears in column A of `List.xlsx`. If the company is already in the dict, append the new contacts to its list — don't replace existing ones.

## Step 3 — Run the script

Run `update_hr_contacts.py` from the project root. The script reads existing cell content first and only appends contacts whose names aren't already there. Running it twice produces zero changes the second time.

## Step 4 — Verify

The script reports how many rows were updated. Check that the count matches expectations.

## Rules
- Never overwrite manually entered contacts — the script is append-only.
- Write names directly, no [UNVERIFIED] prefix.
- To remove a contact: delete it from Excel AND remove it from the `HR_CONTACTS` dict. That's the only case requiring both steps.
- Don't drag the fill handle in Excel after running — it creates ghost rows with duplicated formulas.

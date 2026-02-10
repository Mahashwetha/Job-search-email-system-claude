# Claude Job Search Agent 🎯

An automated daily job search system that emails you curated senior-level job opportunities. Focuses on Software Developer (Java), Backend Java Developer, and Product Owner roles. Easily customize for your location.

## Features

- 📧 **Daily Email Reports** - Automated emails at 10:00 AM CET
- 🎓 **Senior Roles Focus** - Targets positions requiring 8+ years experience
- 📊 **Excel Integration** - Reads and syncs with your application tracker
- 🗂️ **Smart Organization** - Groups companies by role → status
- 🔗 **Clickable Role Links** - Role names link directly to the job posting
- 👤 **HR Contact Column** - Shows recruiter/TA contacts with clickable LinkedIn profiles
- 🔍 **Platform Aggregators** - Curated search links (Glassdoor, LinkedIn, etc.)
- 💼 **Compact Format** - See more companies at a glance
- ⚡ **Windows Automation** - Runs automatically via Task Scheduler

## Email Report Preview

To see what the daily email looks like, download and open [`sample_report.html`](sample_report.html) in your browser. All data in the sample is fictional.

**Report includes:**
- Companies grouped by status (Not Contacted / Review / Applied / No Jobs / Rejected)
- **Role** column with clickable links to the job posting
- **HR Contact** column with clickable LinkedIn profiles (in purple)
- **Links** column with quick search links (Google, LinkedIn, WTTJ)
- Platform aggregator links (Glassdoor, LinkedIn, etc.) under each role category

## What You Get

### Roles Tracked
1. **Software Developer (Java) - SENIOR/EXPERT** (8+ years)
2. **Backend Java Developer - SENIOR** (5-8+ years)
3. **Product Owner** (Senior level)

### Status Tracking
- ⬜ Not Contacted
- 🕐 Under Review / In Progress
- ✅ Applied
- ⏸️ No Jobs Available
- ❌ Rejected

## 🌍 Important: Customize for Your Location

This tool comes with sample job search links. **Before using:**
1. Open `daily_job_search.py`
2. Update the location variables at the top (lines 15-16):
   ```python
   LOCATION_CITY = "YourCity"      # Change from "Paris"
   LOCATION_COUNTRY = "YourCountry" # Change from "France"
   ```
3. Optionally update the job board URLs to match your location (see [Customize URLs](#customize-for-your-location) below)

## Prerequisites

- **Python 3.7+**
- **Gmail account** with App Password enabled
- **Excel tracker** (optional but recommended)
- **Windows OS** (for Task Scheduler automation)

## Quick Start

### 1. Install Python Dependencies

```bash
pip install openpyxl
```

### 2. Configure Your Settings

**IMPORTANT:** Create your configuration file:

1. Copy `config.template.py` to `config.py`
2. Edit `config.py` with your details:

```python
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'YOUR_EMAIL@gmail.com',        # ← Your Gmail
    'sender_password': 'YOUR_APP_PASSWORD',         # ← Gmail App Password (16 chars)
    'recipient_email': 'YOUR_EMAIL@gmail.com',      # ← Recipient email
}

TRACKER_FILE = r'C:\Path\To\Your\Tracker.xlsx'     # ← Your Excel tracker path
```

### 3. Get Gmail App Password

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable **2-Step Verification** (if not already enabled)
3. Go to **App passwords** (at the bottom)
4. Select "Mail" and your device
5. Copy the **16-character password** (no spaces)
6. Paste it in `config.py` as `sender_password`

### 4. Test Run

```bash
python daily_job_search.py
```

Check your email - you should receive the job search report!

### 5. Schedule Daily Emails (10:00 AM)

**Easy Setup (Recommended):**

1. Right-click `setup_task_admin.bat`
2. Select **"Run as administrator"**
3. Click "Yes" when prompted
4. You should see "SUCCESS! Scheduled task created"

**Alternative Methods:**
- Run `setup_scheduled_task.ps1` (PowerShell version)
- Manual setup via Task Scheduler GUI (see `SETUP_INSTRUCTIONS.txt`)

## Excel Tracker Setup

### Option 1: Use the Template (Recommended)

1. **Copy the template:**
   ```bash
   # The repository includes tracker_template.xlsx
   # Copy it and customize with your companies
   ```

2. **Update `config.py` with your tracker path:**
   ```python
   TRACKER_FILE = r'C:\Path\To\Your\tracker.xlsx'
   ```

### Option 2: Use Your Existing Tracker

Format your Excel file like this:

| Company | Role | Role link | status of application | potentialHR contact | Other comments |
|---------|------|-----------|----------------------|---------------------|----------------|
| abc | Backend general specialist | https://... | In progress | Jane Smith | |
| xyz | Engineering Manager Java | https://... | Rejected | | |
| hogwarts | Senior Software Engineer | https://... | done | John Doe | |

**Required Columns:**
- **Column A**: Company name (required)
- **Column B**: Role title (can be empty, script will use "Various")
- **Column C**: Application/job posting link (clickable in email report)
- **Column D**: Status - use one of these:
  - `"done"` or `"applied"` → Shows as ✅ Applied
  - `"In progress"` or `"Under Review"` → Shows as 🕐 Review
  - `"Rejected"` → Shows as ❌ Rejected (apply strikethrough formatting)
  - `"Not available"` or `"Nothing to apply"` → Shows as ⏸️ No Jobs Available
  - Empty or anything else → Shows as ⬜ Not Contacted

**Optional Columns:**
- **Column E**: potentialHR contact - recruiter/TA names with LinkedIn hyperlinks (see HR Contacts below)
- **Column F**: Other comments

**Tips:**
- You can add section headers (e.g., "Product Owner Roles") in Column A
- Use strikethrough formatting on rejected companies (the script will detect it)
- The script automatically categorizes roles based on keywords in Column B
- Close Excel file before running the script to avoid permission errors

## HR Contact Lookup

The system supports a **potentialHR contact** column (Column E) in your Excel tracker, showing recruiter/talent acquisition contacts for each company with clickable LinkedIn links in the email report.

### How to Populate HR Contacts

**Option A: Bulk populate with script (recommended for first setup)**

1. Copy `update_hr_contacts.template.py` to `update_hr_contacts.py`
2. Research recruiters for your target companies (search LinkedIn for `"CompanyName" "talent acquisition" OR "recruiter" YourCity site:linkedin.com/in`)
3. Fill in the `HR_CONTACTS` dictionary with `(name, linkedin_url)` tuples
4. Run: `python update_hr_contacts.py`

This adds a **potentialHR contact** column to your Excel with clickable names.

> **Important:** Web-scraped contacts are **suggestions only** — they may be outdated, in the wrong location, or no longer at the company. Always verify on LinkedIn before reaching out.

**Option B: Add contacts directly in Excel**

Simply type recruiter names into Column E of your Excel tracker. To make them clickable:
- Select the cell, right-click → **Link** → paste the LinkedIn profile URL
- The name will appear as a clickable link in the email report

### Append-Only Workflow

The `update_hr_contacts.py` script uses **append-only** logic — it reads existing cell content first and only adds contacts that aren't already there. This means you can freely mix manual Excel edits with script updates:

| Action | What to do |
|--------|------------|
| **Add a contact in Excel** | Just type it in Column E — the script will never overwrite it |
| **Add a new company row** | Just add it in Excel — the script leaves unknown companies alone |
| **Script finds new contacts** | New contacts are added to the `HR_CONTACTS` dict, then the script appends only the new ones |
| **Remove a contact** | Delete from Excel **and** remove from the `HR_CONTACTS` dict in `update_hr_contacts.py` |

The script is **idempotent** — running it multiple times won't create duplicates. Only truly new contacts get appended.

> **Note:** Removal is the only case where you need to update both places (Excel + script). For everything else, your manual Excel edits are always preserved.

### Auto-Update in Daily Email

The daily email script reads the potentialHR contact column **fresh from your Excel every time it runs**. This means:
- Any contacts you add or edit in Column E are automatically included in the next email
- Deleted contacts are removed from the next email
- New company rows with HR contacts are picked up automatically

> **Note:** `update_hr_contacts.py` is gitignored because it contains real contact data.

## File Structure

```
claude-job-agent/
├── daily_job_search.py                # Main Python script
├── config.template.py                  # Configuration template (copy to config.py)
├── config.py                           # Your private configuration (gitignored)
├── update_hr_contacts.template.py      # HR contacts updater template
├── update_hr_contacts.py               # Your HR contacts data (gitignored)
├── run_daily_job_search.bat           # Windows batch file for scheduler
├── setup_task_admin.bat               # Easy setup for scheduled task
├── setup_scheduled_task.ps1           # PowerShell setup script
├── SETUP_INSTRUCTIONS.txt             # Detailed setup guide
├── tracker_template.xlsx              # Excel tracker template
├── job_search_log.txt                 # Execution log (auto-generated)
├── .gitignore                         # Excludes private files from Git
└── README.md                          # This file
```

## How It Works

1. **Daily Trigger** - Windows Task Scheduler runs the batch file at 10:00 AM
2. **Read Excel** - Script loads your application tracker for latest statuses, role links, and HR contacts
3. **Merge Data** - Combines pre-defined companies + Excel tracker companies
4. **Organize** - Groups by Role → Status (Not Contacted → Review → Applied → Rejected)
5. **Generate HTML** - Creates a compact, styled email report with clickable role links and HR contacts
6. **Send Email** - Sends via Gmail SMTP to your inbox

## Customization

### Add More Companies

**Simply add them to your Excel tracker!** The script automatically:
- Reads all companies from your Excel file
- Categorizes them by role (Java Developer, Backend Developer, Product Owner)
- Merges them with platform aggregator links
- Updates daily with latest statuses

**No code changes needed** - just update your Excel file and the next email will include the new companies.

### Customize for Your Location

**Quick Setup (Just 2 Variables!):**

Open `daily_job_search.py` and update lines 15-16:

```python
LOCATION_CITY = "Paris"         # ← Change to your city (e.g., "London", "Berlin")
LOCATION_COUNTRY = "France"     # ← Change to your country (e.g., "UK", "Germany")
```

This automatically updates:
- ✅ Email header location display
- ✅ All job search link labels

**Optional: Update Job Board URLs**

If you want to customize the actual URLs for your location:

1. Find the `PLATFORM_AGGREGATORS` section (around line 35)
2. Update URLs for your region's job boards
3. Add job boards popular in your country

**Tip:** The link labels already use your location variables, so you only need to update the URLs themselves.

### Change Email Time

To change from 10:00 AM to another time:

1. Delete existing task: `schtasks /delete /tn "DailyJobSearch" /f`
2. Run `setup_task_admin.bat` again after editing the time in the file
3. Or manually update via Task Scheduler GUI

### Modify Email Format

Edit the HTML/CSS in the `create_job_report()` function in `daily_job_search.py`.

## Troubleshooting

### Email Not Sending

- ✅ Check Gmail App Password is correct (16 characters, no spaces)
- ✅ Verify 2-Step Verification is enabled in Google Account
- ✅ Make sure `config.py` exists (copy from `config.template.py`)
- ✅ Test with manual run: `python daily_job_search.py`

### Excel Not Reading

**Common Error:** `Permission denied: 'C:\\...\\List.xlsx'`

This happens when Excel file is open. **Solution:**
1. ✅ **Close the Excel file** before running the script
2. ✅ Make sure Excel isn't running in the background
3. ✅ If error persists, restart your computer

**Other Excel issues:**
- ✅ Verify Excel file path in `config.py` is correct (use raw string: `r'C:\Path\...'`)
- ✅ Check the file exists at that path
- ✅ Ensure `openpyxl` is installed: `pip install openpyxl`
- ✅ Make sure file is `.xlsx` format (not `.xls` or `.csv`)

**Empty Email Received?**
- If email is empty/shows 0 companies, the Excel file couldn't be read
- Check the log: `job_search_log.txt` will show "Warning: Could not read tracker"
- Close Excel file and run again

### Task Scheduler Not Running

- ✅ Check task exists: `schtasks /query /tn "DailyJobSearch"`
- ✅ Verify task is enabled in Task Scheduler (`taskschd.msc`)
- ✅ Run `run_daily_job_search.bat` manually to test
- ✅ Check log file: `job_search_log.txt`
- ✅ Make sure computer is ON at 10:00 AM

### Script Errors

- ✅ Make sure `config.py` exists (not just `config.template.py`)
- ✅ Verify all paths use raw strings: `r'C:\Path\...'`
- ✅ Check Python version: `python --version` (need 3.7+)

## Verify It's Working

**Check Scheduled Task:**
```powershell
Get-ScheduledTask -TaskName "DailyJobSearch"
```

**Manual Test Run:**
```bash
python daily_job_search.py
```

**Check Logs:**
```bash
type job_search_log.txt
```

## Contributing

If you'd like to improve this project:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Security Notes

⚠️ **IMPORTANT:**
- Never commit `config.py` to Git (it's in `.gitignore`)
- Never commit `update_hr_contacts.py` to Git (contains real recruiter names/LinkedIn URLs)
- Keep your Gmail App Password secure
- Don't share your Excel tracker if it contains private data

## License

MIT License - Feel free to use and modify for personal use.

## Support

For issues or questions:
- Check the **Troubleshooting** section above
- Review logs in `job_search_log.txt`
- See `SETUP_INSTRUCTIONS.txt` for detailed setup help
- Test manually first before debugging scheduler

---

**Built with Claude Code** 🤖 | **Last Updated:** 2026-02-10

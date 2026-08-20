"""
Blocklist a hot job: removes it from current_jobs and adds to blocklist.
Usage: python blocklist_job.py "Company Name" ["Job Title"]

Company match is case-insensitive substring. Title is optional -- if omitted,
all jobs from that company are blocklisted.
"""
import sys
import json
import os

HOT_JOBS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'daily_hot_jobs.json')
HOT_JOBS_FILE = os.path.normpath(HOT_JOBS_FILE)

def run(company_arg, title_arg=None):
    with open(HOT_JOBS_FILE, encoding='utf-8') as f:
        data = json.load(f)

    company_lower = company_arg.lower().strip()
    title_lower = title_arg.lower().strip() if title_arg else None

    removed = []
    new_current = {}

    for category, jobs in data['current_jobs'].items():
        kept = []
        for job in jobs:
            jc = job.get('company', '').lower().strip()
            jt = job.get('title', '').lower().strip()
            match_company = company_lower in jc or jc in company_lower
            match_title = (title_lower is None) or (title_lower in jt or jt in title_lower)
            if match_company and match_title:
                removed.append((category, job['company'], job['title']))
            else:
                kept.append(job)
        new_current[category] = kept

    data['current_jobs'] = new_current

    # Add to blocklist (avoid duplicates)
    blocklist = data.get('blocklist', [])
    blocklist_lower = [e.lower() for e in blocklist]

    if removed:
        for _, company, title in removed:
            entry = f"{company}|{title}"
            if entry.lower() not in blocklist_lower:
                blocklist.append(entry)
                print(f"  Blocklisted: {company} | {title}")
            else:
                print(f"  Already in blocklist: {company} | {title}")
    else:
        # Job not in current_jobs -- add blocklist entry anyway
        entry = f"{company_arg}|{title_arg or ''}"
        if entry.lower() not in blocklist_lower:
            blocklist.append(entry)
            print(f"  Blocklisted (not in current_jobs): {company_arg} | {title_arg or '*'}")
        else:
            print(f"  Already in blocklist: {company_arg} | {title_arg or '*'}")

    data['blocklist'] = blocklist

    with open(HOT_JOBS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    if removed:
        print(f"\nRemoved {len(removed)} job(s) from current_jobs:")
        for cat, company, title in removed:
            print(f"  [{cat}] {company} — {title}")
    else:
        print(f"\nNo matching jobs found in current_jobs (blocklist entry still added).")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python blocklist_job.py \"Company Name\" [\"Job Title\"]")
        sys.exit(1)
    company = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else None
    run(company, title)

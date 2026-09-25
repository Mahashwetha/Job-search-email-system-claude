"""
Blocklist a hot job: removes it from current_jobs and adds to blocklist.
Usage:
  python blocklist_job.py "Company Name" ["Job Title"]
  python blocklist_job.py --all [--dry-run]    block every current hot job, except companies
                                               already in the tracker (applied ones clear naturally)

Company match is case-insensitive substring. Title is optional -- if omitted,
all jobs from that company are blocklisted.
Set HOT_JOBS_FILE_OVERRIDE (and TRACKER_FILE_OVERRIDE) to run against copies in tests.
"""
import sys
import json
import os

PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
HOT_JOBS_FILE = os.environ.get('HOT_JOBS_FILE_OVERRIDE') or os.path.join(PROJECT_ROOT, 'daily_hot_jobs.json')


def load():
    with open(HOT_JOBS_FILE, encoding='utf-8') as f:
        return json.load(f)


def save(data):
    tmp = HOT_JOBS_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, HOT_JOBS_FILE)  # atomic: the digest never reads a half-written file


def run_all(dry_run=False):
    sys.path.insert(0, PROJECT_ROOT)
    import tracker_lib as T
    tracked = [T.cell_text(v[0]) for _, _, v in T.rows(T.load(data_only=True)) if T.cell_text(v[0])]
    data = load()
    to_block, skipped = [], []
    for category, jobs in data['current_jobs'].items():
        for job in jobs:
            co, title = job.get('company', ''), job.get('title', '')
            if any(T.company_matches(co, t) for t in tracked):
                skipped.append((category, co, title))
            else:
                to_block.append((category, co, title))
    print(f"{'DRY RUN: would block' if dry_run else 'Blocking'} {len(to_block)} hot job(s):")
    for cat, co, title in to_block:
        print(f"  [{cat}] {co} | {title}")
    if skipped:
        print(f"Skipped {len(skipped)} (company already in tracker):")
        for cat, co, title in skipped:
            print(f"  [{cat}] {co} | {title}")
    if dry_run or not to_block:
        return
    for _, co, title in to_block:
        run(co, title)


def run(company_arg, title_arg=None):
    data = load()

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
    # Blocklist entries are [company, title] pairs
    blocklist = data.get('blocklist', [])

    def to_key(entry):
        if isinstance(entry, list):
            return "||".join(e.lower() for e in entry)
        return str(entry).lower()

    blocklist_keys = {to_key(e) for e in blocklist}

    def make_entry(company, title):
        return [company.lower(), (title or '').lower()]

    if removed:
        for _, company, title in removed:
            entry = make_entry(company, title)
            key = to_key(entry)
            if key not in blocklist_keys:
                blocklist.append(entry)
                blocklist_keys.add(key)
                print(f"  Blocklisted: {company} | {title}")
            else:
                print(f"  Already in blocklist: {company} | {title}")
    else:
        # Job not in current_jobs -- add blocklist entry anyway
        entry = make_entry(company_arg, title_arg or '')
        key = to_key(entry)
        if key not in blocklist_keys:
            blocklist.append(entry)
            print(f"  Blocklisted (not in current_jobs): {company_arg} | {title_arg or '*'}")
        else:
            print(f"  Already in blocklist: {company_arg} | {title_arg or '*'}")

    data['blocklist'] = blocklist
    save(data)

    if removed:
        print(f"\nRemoved {len(removed)} job(s) from current_jobs:")
        for cat, company, title in removed:
            print(f"  [{cat}] {company} — {title}")
    else:
        print(f"\nNo matching jobs found in current_jobs (blocklist entry still added).")


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 2:
        print("Usage: python blocklist_job.py \"Company Name\" [\"Job Title\"]  |  --all [--dry-run]")
        sys.exit(1)
    if sys.argv[1] == '--all':
        run_all(dry_run='--dry-run' in sys.argv)
        sys.exit(0)
    company = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else None
    run(company, title)

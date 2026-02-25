"""
reject_remote.py — manage the rejected remote jobs list

Usage:
  Add a rejection:
    python reject_remote.py "company name" "job title"

  Remove a rejection (restore for review):
    python reject_remote.py --remove "company name" "job title"

  List all rejections:
    python reject_remote.py --list

  Reject all jobs from the last run (previous_jobs.json):
    python reject_remote.py --all

Both company and title are matched as lowercase substrings in remote_job_search.py.
Leave title as "" to reject all roles from a company:
    python reject_remote.py "somecompany" ""
"""

import json
import os
import sys

REJECTED_FILE = os.path.join(os.path.dirname(__file__), 'rejected_remote.json')
PREVIOUS_JOBS_FILE = os.path.join(os.path.dirname(__file__), 'previous_jobs.json')


def load():
    try:
        with open(REJECTED_FILE, 'r', encoding='utf-8') as f:
            return [list(e) for e in json.load(f)]
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save(entries):
    with open(REJECTED_FILE, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def add(company, title):
    entries = load()
    key = [company.lower().strip(), title.lower().strip()]
    if key in entries:
        print(f"Already rejected: {key}")
        return
    entries.append(key)
    save(entries)
    print(f"Added: {key}  (total: {len(entries)})")


def remove(company, title):
    entries = load()
    key = [company.lower().strip(), title.lower().strip()]
    before = len(entries)
    entries = [e for e in entries if e != key]
    if len(entries) == before:
        print(f"Not found: {key}")
        return
    save(entries)
    print(f"Removed: {key}  (total: {len(entries)})")


def add_all():
    """Add all entries from previous_jobs.json to the rejected list."""
    try:
        with open(PREVIOUS_JOBS_FILE, 'r', encoding='utf-8') as f:
            previous = [list(e) for e in json.load(f)]
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"ERROR: {PREVIOUS_JOBS_FILE} not found or empty. Run remote_job_search.py first.")
        return

    entries = load()
    existing = set(tuple(e) for e in entries)
    added = 0
    for company, title in previous:
        key = [company.lower().strip(), title.lower().strip()]
        if tuple(key) not in existing:
            entries.append(key)
            existing.add(tuple(key))
            added += 1

    save(entries)
    print(f"Added {added} new entries from last run  (total: {len(entries)})")


def list_all():
    entries = load()
    if not entries:
        print("No rejections.")
        return
    for i, (company, title) in enumerate(entries, 1):
        print(f"  {i:>3}. [{company}]  {title or '(all roles)'}")
    print(f"\nTotal: {len(entries)}")


if __name__ == '__main__':
    args = sys.argv[1:]

    if args[0] == '--help':
        print("""
reject_remote.py — manage the rejected remote jobs list

COMMANDS:
  --list                        Show all rejected (company, title) pairs
  --all                         Bulk-reject all jobs from the last run (previous_jobs.json)
                                Run this after reviewing the email to hide everything seen
  --remove "company" "title"    Restore a rejected job back for review
  --help                        Show this help message

  "company" "title"             Reject a specific job by company + title substring

EXAMPLES:
  python reject_remote.py --list
  python reject_remote.py --all
  python reject_remote.py --remove "grafana labs" "senior backend engineer"
  python reject_remote.py "canonical" "hpc software engineer"
  python reject_remote.py "somecompany" ""        <- rejects ALL roles from this company
""")
    elif not args or args[0] == '--list':
        list_all()
    elif args[0] == '--all':
        add_all()
    elif args[0] == '--remove':
        if len(args) < 3:
            print("Usage: python reject_remote.py --remove \"company\" \"title\"")
            sys.exit(1)
        remove(args[1], args[2])
    else:
        if len(args) < 2:
            print("Usage: python reject_remote.py \"company\" \"title\"")
            sys.exit(1)
        add(args[0], args[1])

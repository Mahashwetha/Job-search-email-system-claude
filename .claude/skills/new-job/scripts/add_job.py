"""
add_job.py - append a job application to List.xlsx (Sheet1), safely.

Usage:
  python .claude/skills/new-job/scripts/add_job.py --company "Galadrim" --role "AI Engineer" --url "https://..." [--status done] [--comment "..."] [--force]

Rules enforced in code:
  - status must be 'done' (applied, default), 'In progress' (callback received) or 'Rejected'
  - same job URL already tracked -> refused, prints the existing row
  - company already tracked with other roles -> refused unless --force, prints existing rows
  - takes the shared tracker lock and backs up List.xlsx before writing
Exit codes: 0 added, 2 duplicate URL, 3 company exists (use --force), 1 error.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
import tracker_lib as T  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--company", required=True)
    p.add_argument("--role", default="")
    p.add_argument("--url", default="")
    p.add_argument("--status", default="done")
    p.add_argument("--comment", default="")
    p.add_argument("--force", action="store_true", help="add even if the company already has rows")
    a = p.parse_args()

    if a.status not in T.VALID_STATUSES:
        print(f"ERROR: status must be one of {sorted(T.VALID_STATUSES)} (got '{a.status}')")
        return 1

    with T.tracker_lock():
        wb = T.load()
        existing = list(T.rows(wb))

        if a.url:
            target = T.norm_url(a.url)
            dup = [h for h in existing if target and T.norm_url(T.extract_url(h[2][2])) == target]
            if dup:
                _, r, v = dup[0]
                print(f"DUPLICATE: this job URL is already tracked -> row {r}: {v[0]} | {v[1]} | {v[3]}")
                return 2

        same_co = [h for h in existing if T.company_matches(a.company, h[2][0])]
        if same_co and not a.force:
            print(f"COMPANY EXISTS: '{a.company}' already has {len(same_co)} row(s):")
            for _, r, v in same_co:
                print(f"  row {r}: {v[0]} | {v[1]} | {v[3]}")
            print("Different role? Re-run with --force to add it anyway.")
            return 3

        backup_path = T.backup()
        ws = wb["Sheet1"]
        ws.append([a.company.strip(), a.role.strip(), a.url.strip() or None, a.status, None, a.comment.strip() or None])
        T.save(wb)
        print(f"ADDED: row {ws.max_row}: {a.company} | {a.role} | {a.status}")
        print(f"(backup: {backup_path})")
        return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        sys.exit(main())
    except (TimeoutError, PermissionError) as e:
        print(f"ERROR: {e}")
        sys.exit(1)

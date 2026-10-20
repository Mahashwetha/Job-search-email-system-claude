"""
mark_rejected.py - mark a company as Rejected in List.xlsx

Sets column D to "Rejected" and applies strikethrough font across columns A-F.
Only touches the matched company row(s). Takes the shared tracker lock and
backs up List.xlsx before writing.

By default every row whose column A contains the company name (case-insensitive
substring) is marked. Narrow it down when a company has several applications:
  --role "text"   only rows whose column B (role) contains the text (case-insensitive)
  --row N         only this exact row number (repeatable); column A must still match
  --exact         column A must equal the company name (case-insensitive), not just contain it
Filters combine (all must hold). If a --row is not a matching row, nothing is changed.

Usage:
  python .claude/skills/mark-rejected/scripts/mark_rejected.py "Company Name"
  python .claude/skills/mark-rejected/scripts/mark_rejected.py "Company Name" --dry-run   (list matches, change nothing)
  python .claude/skills/mark-rejected/scripts/mark_rejected.py "Alan" --exact --role "backend" --dry-run
  python .claude/skills/mark-rejected/scripts/mark_rejected.py "Alan" --row 42 --row 57
Exit codes: 0 updated (or dry-run listed), 4 no match (or a --row did not match), 1 error, 2 bad arguments.
"""
import argparse
import os
import sys

from openpyxl.styles import Font

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
import tracker_lib as T  # noqa: E402

STRIKETHROUGH_COLS = 6  # A through F


def apply_strikethrough(ws, row_idx):
    for col in range(1, STRIKETHROUGH_COLS + 1):
        cell = ws.cell(row=row_idx, column=col)
        f = cell.font
        cell.font = Font(name=f.name, size=f.size, bold=f.bold, italic=f.italic,
                         color=f.color, underline=f.underline, strike=True)


def _company_match(q, company, exact):
    c = T.cell_text(company).lower()
    return c == q if exact else q in c


def mark_rejected(company_name, dry_run=False, role=None, rows=None, exact=False):
    with T.tracker_lock():
        wb = T.load()
        ws = wb["Sheet1"]
        q = company_name.strip().lower()
        role_q = (role or "").strip().lower()
        wanted_rows = set(rows or [])
        company_rows = [(r, T.cell_text(v[0]), T.cell_text(v[1]), T.cell_text(v[3]))
                        for _, r, v in T.rows(wb) if q and _company_match(q, v[0], exact)]
        if not company_rows:
            print(f"No rows found matching: '{company_name}'" + (" (exact)" if exact else ""))
            return 4
        if wanted_rows:
            bad = sorted(wanted_rows - {r for r, *_ in company_rows})
            if bad:
                print(f"Row(s) {', '.join(map(str, bad))} do not match company '{company_name}'"
                      + (" (exact)" if exact else "") + ". Nothing changed. Rows for this company:")
                for r, co, rl, status in company_rows:
                    print(f"  Row {r}: '{co}' | {rl} | currently: {status}")
                return 4
        matched = [m for m in company_rows
                   if (not wanted_rows or m[0] in wanted_rows)
                   and (not role_q or role_q in m[2].lower())]
        skipped = [m for m in company_rows if m not in matched]
        if not matched:
            print(f"No rows for '{company_name}' match the --role/--row filters. Rows for this company:")
            for r, co, rl, status in company_rows:
                print(f"  Row {r}: '{co}' | {rl} | currently: {status}")
            return 4
        if dry_run:
            print(f"DRY RUN: {len(matched)} row(s) would be marked Rejected:")
            for r, co, rl, status in matched:
                print(f"  Row {r}: '{co}' | {rl} | currently: {status}")
            if skipped:
                print(f"Not touched ({len(skipped)} other row(s) for this company, excluded by filters):")
                for r, co, rl, status in skipped:
                    print(f"  Row {r}: '{co}' | {rl} | currently: {status}")
            return 0
        backup_path = T.backup()
        for r, *_ in matched:
            ws.cell(row=r, column=T.COL_STATUS).value = "Rejected"
            apply_strikethrough(ws, r)
        T.save(wb)
    for r, co, rl, _ in matched:
        print(f"  Row {r}: '{co}' | {rl} -> Rejected + strikethrough applied")
    print(f"Done. {len(matched)} row(s) updated. (backup: {backup_path})")
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Mark a company's tracker row(s) as Rejected.")
    p.add_argument("company", help="company name (matched against column A)")
    p.add_argument("--dry-run", action="store_true", help="list matches, change nothing")
    p.add_argument("--role", help="only rows whose column B contains this text (case-insensitive)")
    p.add_argument("--row", type=int, action="append", help="only this row number (repeatable)")
    p.add_argument("--exact", action="store_true", help="column A must equal the company name (case-insensitive)")
    a = p.parse_args()
    try:
        sys.exit(mark_rejected(a.company, dry_run=a.dry_run, role=a.role, rows=a.row, exact=a.exact))
    except (TimeoutError, PermissionError) as e:
        print(f"ERROR: {e}")
        sys.exit(1)

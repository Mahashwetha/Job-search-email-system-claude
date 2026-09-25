"""
mark_rejected.py - mark a company as Rejected in List.xlsx

Sets column D to "Rejected" and applies strikethrough font across columns A-F.
Only touches the matched company row(s). Takes the shared tracker lock and
backs up List.xlsx before writing.

Usage:
  python .claude/skills/mark-rejected/scripts/mark_rejected.py "Company Name"
  python .claude/skills/mark-rejected/scripts/mark_rejected.py "Company Name" --dry-run   (list matches, change nothing)
Exit codes: 0 updated (or dry-run listed), 4 no match, 1 error.
"""
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


def mark_rejected(company_name, dry_run=False):
    with T.tracker_lock():
        wb = T.load()
        ws = wb["Sheet1"]
        q = company_name.strip().lower()
        matched = [(r, T.cell_text(v[0]), T.cell_text(v[1]), T.cell_text(v[3]))
                   for _, r, v in T.rows(wb) if q and q in T.cell_text(v[0]).lower()]
        if not matched:
            print(f"No rows found matching: '{company_name}'")
            return 4
        if dry_run:
            print(f"DRY RUN: {len(matched)} row(s) would be marked Rejected:")
            for r, co, role, status in matched:
                print(f"  Row {r}: '{co}' | {role} | currently: {status}")
            return 0
        backup_path = T.backup()
        for r, *_ in matched:
            ws.cell(row=r, column=T.COL_STATUS).value = "Rejected"
            apply_strikethrough(ws, r)
        T.save(wb)
    for r, co, role, _ in matched:
        print(f"  Row {r}: '{co}' | {role} -> Rejected + strikethrough applied")
    print(f"Done. {len(matched)} row(s) updated. (backup: {backup_path})")
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    if not args:
        print("Usage: python mark_rejected.py \"Company Name\" [--dry-run]")
        sys.exit(1)
    try:
        sys.exit(mark_rejected(args[0], dry_run="--dry-run" in sys.argv))
    except (TimeoutError, PermissionError) as e:
        print(f"ERROR: {e}")
        sys.exit(1)

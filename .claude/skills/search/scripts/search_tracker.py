"""
search_tracker.py - find a company or job URL in List.xlsx (Sheet1). Read-only.

Usage:
  python .claude/skills/search/scripts/search_tracker.py "Company Name"
  python .claude/skills/search/scripts/search_tracker.py "https://job-url"
  add --json for machine-readable output
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
import tracker_lib as T  # noqa: E402

EMOJI = [("done", "✅ Applied"), ("applied", "✅ Applied"), ("in progress", "🕐 In Progress"),
         ("under review", "🕐 In Progress"), ("rejected", "❌ Rejected"),
         ("not available", "⏸️ No Jobs Available"), ("nothing to apply", "⏸️ No Jobs Available")]


def status_label(status):
    s = T.cell_text(status).lower()
    for key, label in EMOJI:
        if key in s:
            return label
    return "⬜ Not Contacted"


def company_from_page(url):
    try:
        import requests
        html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).text
        title = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        if not title:
            return None
        parts = re.split(r"\s[-|–@]\s|\sat\s|\schez\s", title.group(1).strip())
        return parts[1].strip() if len(parts) > 1 else None
    except Exception:
        return None


def search(query):
    wb = T.load(data_only=False)
    is_url = query.strip().lower().startswith(("http://", "https://"))
    hits, how = [], "company"
    if is_url:
        target = T.norm_url(query)
        hits = [h for h in T.rows(wb) if target and T.norm_url(T.extract_url(h[2][2])) == target]
        how = "url"
        if not hits:
            company = company_from_page(query)
            if company:
                hits = [h for h in T.rows(wb) if T.company_matches(company, h[2][0])]
                how = f"company from page title: {company}"
    else:
        hits = [h for h in T.rows(wb) if T.company_matches(query, h[2][0])]
    return [{"sheet": s, "row": r, "company": T.cell_text(v[0]), "role": T.cell_text(v[1]),
             "url": T.extract_url(v[2]), "status": T.cell_text(v[3]), "notes": T.cell_text(v[5])}
            for s, r, v in hits], how


def main():
    args = [a for a in sys.argv[1:] if a != "--json"]
    if not args:
        print(__doc__)
        sys.exit(1)
    query = args[0]
    hits, how = search(query)
    if "--json" in sys.argv:
        print(json.dumps({"query": query, "matched_by": how, "results": hits}, ensure_ascii=False, indent=1))
        return
    if not hits:
        print(f'Not in tracker: "{query}" (matched by {how})')
        return
    print(f'Found {len(hits)} match(es) for "{query}" (matched by {how}):')
    for sheet in T.SHEETS:
        group = [h for h in hits if h["sheet"] == sheet]
        if not group:
            continue
        print(f"\n  [{sheet}]")
        for h in group:
            print(f"    Row {h['row']} - {h['company']} | {h['role']} | {status_label(h['status'])}")
            if h["url"]:
                print(f"             URL: {h['url']}")
            if h["notes"]:
                print(f"             Note: {h['notes'][:200]}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

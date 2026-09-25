"""
Job tracker MCP server - exposes List.xlsx to AI agents as tools.

Each tool is a thin wrapper around the tested skill scripts, so Claude Code
skills, this server and any future email agent all share one implementation
(same lock, backups, duplicate checks and append-only rules in tracker_lib.py).

Run (stdio):  tracker_mcp/.venv/Scripts/python.exe tracker_mcp/server.py
Tests use TRACKER_FILE_OVERRIDE to point at a copy of the tracker.
"""
import json
import os
import re
import subprocess
import sys

from mcp.server.fastmcp import FastMCP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = {
    "search": os.path.join(ROOT, ".claude", "skills", "search", "scripts", "search_tracker.py"),
    "add_job": os.path.join(ROOT, ".claude", "skills", "new-job", "scripts", "add_job.py"),
    "reject": os.path.join(ROOT, ".claude", "skills", "mark-rejected", "scripts", "mark_rejected.py"),
    "hr": os.path.join(ROOT, ".claude", "skills", "update-hr", "scripts", "add_hr_contact.py"),
    "status": os.path.join(ROOT, ".claude", "skills", "update-status", "scripts", "update_status.py"),
    "hot": os.path.join(ROOT, ".claude", "skills", "remove-hot-job", "scripts", "blocklist_job.py"),
    "remote": os.path.join(ROOT, "remote_search", "reject_remote.py"),
}

mcp = FastMCP("job-tracker")

# Digest rows pasted from Gmail glue the source badge onto names: "Key ConsultingWTTJ", "WTTJ Senior Java ..."
# only source badges the digests show; not real employers like Indeed or Glassdoor
_BADGES = r"(WTTJ|LinkedIn|APEC)"


def _clean(text):
    t = re.sub(rf"^\s*{_BADGES}\s*[:|\-]?\s*", "", text or "", flags=re.I)
    t = re.sub(rf"\s*[:|\-]?\s*{_BADGES}\s*$", "", t, flags=re.I)
    return t.strip()


def _run(script, *args):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    # stdin=DEVNULL: the server's own stdin is the MCP transport pipe; a child that
    # inherits it blocks (and on Windows hangs until timeout).
    p = subprocess.run([sys.executable, SCRIPTS[script], *args], cwd=ROOT, env=env,
                       stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       encoding="utf-8", timeout=60)
    return p.returncode, (p.stdout + p.stderr).strip()


@mcp.tool()
def search_tracker(query: str) -> dict:
    """Look up a company name or a job URL in the job application tracker (read-only).

    Returns every matching row with row number, company, role, URL, status and notes.
    Status meanings: 'done' = applied, 'In progress' = callback received, 'Rejected' = rejected.
    Always call this before add_job or mark_rejected to see what is already tracked.
    """
    code, out = _run("search", query, "--json")
    if code != 0:
        return {"ok": False, "error": out}
    return {"ok": True, **json.loads(out)}


@mcp.tool()
def add_job(company: str, role: str = "", url: str = "", status: str = "done",
            comment: str = "", force: bool = False) -> dict:
    """Record a job application in the tracker.

    status: 'done' when the user applied (default), 'In progress' ONLY when the company
    has replied / called back, 'Rejected' only to log a rejection for an untracked job.
    The same job URL is never added twice (outcome 'duplicate'). If the company already has
    rows for other roles the outcome is 'company_exists' and nothing is written; call again
    with force=True only if this is genuinely a different role.
    """
    args = ["--company", _clean(company), "--role", _clean(role), "--url", url, "--status", status, "--comment", comment]
    if force:
        args.append("--force")
    code, out = _run("add_job", *args)
    outcome = {0: "added", 2: "duplicate", 3: "company_exists"}.get(code, "error")
    return {"ok": code == 0, "outcome": outcome, "message": out}


@mcp.tool()
def mark_rejected(company: str, confirm: bool = False) -> dict:
    """Mark every tracker row whose company name contains `company` as Rejected (with strikethrough).

    Safety: with confirm=False (default) nothing is changed; it returns the rows that WOULD be
    rejected. Show them to the user or check they are right, then call again with confirm=True.
    """
    args = [company] if confirm else [company, "--dry-run"]
    code, out = _run("reject", *args)
    if code == 4:
        return {"ok": False, "outcome": "no_match", "message": out}
    outcome = "rejected" if confirm else "preview"
    return {"ok": code == 0, "outcome": outcome if code == 0 else "error", "message": out}


@mcp.tool()
def update_status(status: str, company: str = "", row: int = 0, note: str = "", all_rows: bool = False,
                  preview: bool = False) -> dict:
    """Change the status of a job that is ALREADY in the tracker.

    status: 'In progress' when the company called back / replied / booked an interview (the main use),
    'done' to undo a mistaken status, 'Rejected' for one specific row. Target a specific `row` (from
    search_tracker) or a `company`. If the company has several rows the outcome is 'ambiguous' and the
    rows are listed: pick the right row (the role she mentioned) and call again with row=N, or
    all_rows=True only if she clearly means every role. note: short optional context, e.g.
    'phone screen booked for Monday', saved with today's date. preview=True changes nothing and shows
    what would happen (including 'ambiguous').
    """
    if not row and not company:
        return {"ok": False, "outcome": "error", "message": "Give either row or company."}
    args = (["--row", str(row)] if row else ["--company", _clean(company)]) + ["--status", status]
    if note:
        args += ["--note", note]
    if all_rows:
        args.append("--all")
    if preview:
        args.append("--dry-run")
    code, out = _run("status", *args)
    outcome = {0: "preview" if preview else "updated", 4: "no_match", 5: "ambiguous"}.get(code, "error")
    return {"ok": code == 0, "outcome": outcome, "message": out}


@mcp.tool()
def add_hr_contact(name: str, row: int = 0, company: str = "", url: str = "",
                   title: str = "", email: str = "") -> dict:
    """Append one HR / recruiter contact to the tracker's contact column. Never overwrites.

    Target either a specific tracker `row` (from search_tracker) or every row of `company`.
    url: the person's LinkedIn profile. title: e.g. 'Tech Recruiter'. email: only if verified.
    If the name is already listed on that row nothing changes (outcome 'unchanged').
    """
    if not row and not company:
        return {"ok": False, "outcome": "error", "message": "Give either row or company."}
    target = ["--row", str(row)] if row else ["--company", company]
    code, out = _run("hr", *target, "--name", name, "--url", url, "--title", title, "--email", email)
    outcome = "error" if code else ("unchanged" if out.startswith("NO CHANGE") else "added")
    return {"ok": code == 0, "outcome": outcome, "message": out}


@mcp.tool()
def block_hot_job(company: str, title: str = "") -> dict:
    """Hide a job from the Hot Jobs section of the DAILY digest email ("Senior Jobs COMPACT").

    Removes it from the current hot jobs (the slot refills on the next daily run) and adds it
    to the blocklist so it never comes back. Leave title empty to block every hot job from that
    company. Do NOT use this for jobs the user applied to: record those with add_job instead.
    """
    company, title = _clean(company), _clean(title)
    args = [company] + ([title] if title else [])
    code, out = _run("hot", *args)
    return {"ok": code == 0, "outcome": "blocked" if code == 0 else "error", "message": out}


@mcp.tool()
def block_all_hot_jobs(confirm: bool = False) -> dict:
    """Block EVERY job currently in the daily digest's Hot Jobs, except companies already in the tracker.

    Safety: with confirm=False (default) nothing changes; it returns the list that WOULD be
    blocked and the ones skipped. Call again with confirm=True to apply.
    """
    code, out = _run("hot", "--all", *([] if confirm else ["--dry-run"]))
    return {"ok": code == 0, "outcome": ("blocked" if confirm else "preview") if code == 0 else "error",
            "message": out}


@mcp.tool()
def reject_remote_job(company: str, title: str = "") -> dict:
    """Hide a job from future REMOTE job digest emails.

    Company and title match as lowercase substrings. Leave title empty to hide every role from
    that company. Use a very short title fragment only when the user clearly wants a whole family
    of roles hidden (e.g. company='' and title='senior' hides all senior remote roles).
    """
    code, out = _run("remote", _clean(company), _clean(title))
    return {"ok": code == 0, "outcome": "rejected" if code == 0 else "error", "message": out}


@mcp.tool()
def reject_all_remote(confirm: bool = False) -> dict:
    """Hide every job from the LAST remote digest email from future remote digests.

    Safety: with confirm=False (default) nothing changes; it lists the last digest's jobs and
    which are new. Call again with confirm=True to apply.
    """
    code, out = _run("remote", "--all" if confirm else "--last")
    return {"ok": code == 0, "outcome": ("rejected" if confirm else "preview") if code == 0 else "error",
            "message": out}


if __name__ == "__main__":
    mcp.run()

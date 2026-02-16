"""
Remote Job Search — fetches remote-only listings from free APIs,
filters for EMEA-compatible roles matching user profile,
and sends a styled HTML email every 2 days.
"""

import sys
import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Add parent directory to path so we can import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from config import EMAIL_CONFIG
except ImportError:
    print("ERROR: config.py not found!")
    print("Please copy config.template.py to config.py and fill in your details.")
    exit(1)

# ============= FILTERING CONFIG =============

ROLE_KEYWORDS = [
    'java', 'backend', 'software engineer', 'senior software',
    'full stack', 'fullstack', 'devops', 'python', 'cloud engineer',
]

EMEA_INCLUDE = [
    'worldwide', 'anywhere', 'emea', 'europe', 'eu', 'france',
    'paris', 'remote', 'global', 'uk', 'germany', 'netherlands',
]

EMEA_EXCLUDE = [
    'us only', 'us timezone', 'americas only', 'usa only',
    'us-based', 'est/pst',
]

# ============= API FETCHERS =============

def fetch_remoteok():
    """Fetch jobs from RemoteOK API."""
    jobs = []
    try:
        resp = requests.get(
            'https://remoteok.com/api',
            headers={'User-Agent': 'RemoteJobSearch/1.0'},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        # First element is metadata, skip it
        for item in data[1:]:
            jobs.append({
                'company': item.get('company', ''),
                'title': item.get('position', ''),
                'url': item.get('url', ''),
                'source': 'RemoteOK',
                'location': item.get('location', 'Remote'),
                'tags': ', '.join(item.get('tags', [])),
                'posted_date': item.get('date', '')[:10],
            })
        print(f"  RemoteOK: {len(jobs)} jobs fetched")
    except Exception as e:
        print(f"  RemoteOK error: {e}")
    return jobs


def fetch_remotive():
    """Fetch jobs from Remotive API."""
    jobs = []
    try:
        resp = requests.get(
            'https://remotive.com/api/remote-jobs',
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        for item in data.get('jobs', []):
            jobs.append({
                'company': item.get('company_name', ''),
                'title': item.get('title', ''),
                'url': item.get('url', ''),
                'source': 'Remotive',
                'location': item.get('candidate_required_location', 'Remote'),
                'tags': item.get('category', ''),
                'posted_date': item.get('publication_date', '')[:10],
            })
        print(f"  Remotive: {len(jobs)} jobs fetched")
    except Exception as e:
        print(f"  Remotive error: {e}")
    return jobs


def fetch_arbeitnow():
    """Fetch jobs from Arbeitnow API (EU-focused)."""
    jobs = []
    try:
        resp = requests.get(
            'https://www.arbeitnow.com/api/job-board-api',
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        for item in data.get('data', []):
            if not item.get('remote', False):
                continue
            created_at = item.get('created_at', '')
            if isinstance(created_at, int):
                posted = datetime.fromtimestamp(created_at).strftime('%Y-%m-%d')
            else:
                posted = str(created_at)[:10]
            jobs.append({
                'company': item.get('company_name', ''),
                'title': item.get('title', ''),
                'url': item.get('url', ''),
                'source': 'Arbeitnow',
                'location': item.get('location', 'Remote'),
                'tags': ', '.join(item.get('tags', [])),
                'posted_date': posted,
            })
        print(f"  Arbeitnow: {len(jobs)} remote jobs fetched")
    except Exception as e:
        print(f"  Arbeitnow error: {e}")
    return jobs


# ============= FILTER & DEDUP =============

def filter_jobs(jobs):
    """Filter jobs by role keywords and EMEA-compatible location."""
    filtered = []
    for job in jobs:
        title_lower = job['title'].lower()
        location_lower = job['location'].lower()
        tags_lower = job['tags'].lower()
        search_text = f"{title_lower} {tags_lower}"

        # Must match at least one role keyword
        if not any(kw in search_text for kw in ROLE_KEYWORDS):
            continue

        # Exclude US-only jobs
        loc_tags = f"{location_lower} {tags_lower}"
        if any(ex in loc_tags for ex in EMEA_EXCLUDE):
            continue

        # Must have an EMEA-compatible location (or be broadly remote)
        if not any(inc in loc_tags for inc in EMEA_INCLUDE):
            continue

        filtered.append(job)

    return filtered


def dedup_jobs(jobs):
    """Remove duplicates by (company, title) pair."""
    seen = set()
    unique = []
    for job in jobs:
        key = (job['company'].lower().strip(), job['title'].lower().strip())
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


# ============= HTML EMAIL =============

def build_html(jobs):
    """Build styled HTML email with job listings."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    date_str = datetime.now().strftime('%Y-%m-%d')

    rows_html = ''
    for job in jobs:
        rows_html += f"""                <tr>
                    <td><strong>{job['company']}</strong></td>
                    <td><a href="{job['url']}" style="color: #3498db; text-decoration: underline;">{job['title']}</a></td>
                    <td>{job['source']}</td>
                    <td>{job['location']}<br><span style="font-size:9px;color:#7f8c8d;">{job['tags']}</span></td>
                    <td>{job['posted_date']}</td>
                </tr>
"""

    if not jobs:
        rows_html = '<tr><td colspan="5" style="text-align:center;padding:20px;color:#7f8c8d;">No matching remote roles found this run.</td></tr>\n'

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 11px; line-height: 1.2; color: #2c3e50; max-width: 1600px; margin: 0; padding: 8px; background: #f8f9fa; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px; margin: 5px 0; font-size: 18px; }}
            .header-info {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 6px 10px; border-radius: 4px; margin-bottom: 8px; font-size: 11px; }}
            .header-info p {{ margin: 2px 0; }}
            table {{ border-collapse: collapse; width: 100%; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.08); font-size: 11px; margin: 5px 0; }}
            th {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-weight: bold; padding: 5px 6px; text-align: left; font-size: 10px; }}
            td {{ padding: 4px 6px; border-bottom: 1px solid #ecf0f1; vertical-align: top; }}
            tr:hover {{ background-color: #f8f9fa; }}
            .footer {{ text-align: center; color: #7f8c8d; font-size: 10px; margin-top: 12px; padding-top: 8px; border-top: 2px solid #ecf0f1; }}
        </style>
    </head>
    <body>
        <h1>🌍 Remote Roles — {date_str}</h1>

        <div class="header-info">
            <p>📅 {now} | 📊 {len(jobs)} matching roles | 🔍 EMEA-compatible remote positions | Sources: RemoteOK, Remotive, Arbeitnow</p>
        </div>

        <table>
            <thead>
                <tr>
                    <th width="18%">Company</th>
                    <th width="30%">Role</th>
                    <th width="10%">Source</th>
                    <th width="27%">Location / Tags</th>
                    <th width="15%">Posted</th>
                </tr>
            </thead>
            <tbody>
{rows_html}            </tbody>
        </table>

        <div class="footer">
            <p>📊 {len(jobs)} remote roles | Sources: RemoteOK, Remotive, Arbeitnow | 🔄 Next: in 2 days at 12:00 CET</p>
        </div>
    </body>
    </html>
    """
    return html


def send_email(html_content):
    """Send the HTML email using config."""
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = f"Remote Roles — {datetime.now().strftime('%Y-%m-%d')}"
        message["From"] = EMAIL_CONFIG['sender_email']
        message["To"] = EMAIL_CONFIG['recipient_email']

        message.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(message)

        print("SUCCESS: Remote jobs email sent")
        return True
    except Exception as e:
        print(f"ERROR sending email: {e}")
        return False


# ============= MAIN =============

def main():
    print("=== Remote Job Search ===")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Fetch from all sources
    print("Fetching jobs...")
    all_jobs = []
    all_jobs.extend(fetch_remoteok())
    all_jobs.extend(fetch_remotive())
    all_jobs.extend(fetch_arbeitnow())
    print(f"Total fetched: {len(all_jobs)}")

    # Filter and dedup
    filtered = filter_jobs(all_jobs)
    print(f"After role/EMEA filter: {len(filtered)}")

    deduped = dedup_jobs(filtered)
    print(f"After dedup: {len(deduped)}")

    # Sort by posted_date descending
    deduped.sort(key=lambda j: j['posted_date'], reverse=True)

    # Build HTML and send
    html = build_html(deduped)
    send_email(html)


if __name__ == "__main__":
    main()

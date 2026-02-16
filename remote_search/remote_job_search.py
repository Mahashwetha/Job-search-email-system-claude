"""
Remote Job Search — fetches remote-only listings from free APIs/feeds,
filters for EMEA-compatible roles matching user profile,
and sends a styled HTML email every 2 days.

Sources: RemoteOK, Remotive, Arbeitnow, We Work Remotely
"""

import sys
import os
import re
import smtplib
import requests
import xml.etree.ElementTree as ET
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from email.utils import parsedate_to_datetime

# Add parent directory to path so we can import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from config import EMAIL_CONFIG
except ImportError:
    print("ERROR: config.py not found!")
    print("Please copy config.template.py to config.py and fill in your details.")
    exit(1)

# Import optional remote search config from config.py, with defaults
try:
    from config import REMOTE_ROLE_KEYWORDS, REMOTE_LOCATION_INCLUDE, REMOTE_LOCATION_EXCLUDE
except ImportError:
    REMOTE_ROLE_KEYWORDS = None
    REMOTE_LOCATION_INCLUDE = None
    REMOTE_LOCATION_EXCLUDE = None

# ============= FILTERING CONFIG =============
# Override these in config.py to customize for your profile and location

ROLE_KEYWORDS = REMOTE_ROLE_KEYWORDS or [
    # Primary: Java/backend (highest relevance)
    'java', 'backend', 'back-end', 'back end',
    'software engineer', 'senior software', 'tech lead',
    'api engineer',
    # Secondary: Python roles (user has Python skills)
    'python',
    # AI roles (not ML/data science prerequisite)
    'ai engineer', 'genai', 'llm engineer',
]

# Roles to exclude even if they match keywords above
ROLE_EXCLUDE = [
    'data scientist', 'machine learning engineer', 'ml engineer',
    'data engineer', 'analytics engineer', 'research scientist',
    'frontend', 'front-end', 'front end', 'ios ', 'android ',
    'react native', 'flutter',
    'web developer', 'wordpress', 'php developer', 'ruby',
    'salesforce', '.net', 'dotnet', 'c# ', 'node.js',
    'hubspot', 'webflow', 'figma', 'shopify',
    'account executive', 'sales ', 'marketing',
    'full stack', 'full-stack', 'fullstack',
    'network engineer', 'voip', 'linux admin',
    'consultant', 'werkstudent', 'intern ',
    'guatemala', 'latin america', 'latam',
    'ror ', 'rails developer', 'ruby on rails',
    'web development manager', 'manager, web',
    'freelance', 'dataops', 'data ops',
    'network automation',
    'devops', 'dev ops', 'cloud engineer', 'sre',
    'site reliability', 'infrastructure engineer',
    'platform engineer', 'systems engineer',
    'prompt engineer', 'c++',
]

# Location priority tiers for sorting (lower = shown first)
LOCATION_PRIORITY = [
    # Tier 0: Paris
    (['paris'], 0),
    # Tier 1: France
    (['france'], 1),
    # Tier 2: EMEA / CET timezone countries
    (['emea', 'europe', 'eu', 'germany', 'netherlands', 'belgium',
      'spain', 'italy', 'switzerland', 'austria', 'poland', 'czech',
      'sweden', 'norway', 'denmark', 'portugal', 'ireland',
      'cet', 'cest', 'central european'], 2),
    # Tier 3: UK (GMT+0/+1, close to CET)
    (['uk', 'united kingdom', 'london', 'britain'], 3),
    # Tier 4: Worldwide/anywhere/global
    (['worldwide', 'anywhere', 'global'], 4),
]

LOCATION_INCLUDE = REMOTE_LOCATION_INCLUDE or [
    'worldwide', 'anywhere', 'emea', 'europe', 'eu', 'france',
    'paris', 'global', 'uk', 'germany', 'netherlands',
    'belgium', 'spain', 'italy', 'switzerland', 'austria',
    'sweden', 'norway', 'denmark', 'portugal', 'ireland',
    'poland', 'czech', 'united kingdom', 'london',
    # Note: bare 'remote' excluded to avoid US-default listings
]

LOCATION_EXCLUDE = REMOTE_LOCATION_EXCLUDE or [
    'us only', 'us timezone', 'americas only', 'usa only',
    'us-based', 'est/pst', 'canada only', 'canada', 'north america',
    'us or canada', 'usa/canada', 'na only',
    'new york', 'san francisco', 'los angeles', 'seattle', 'chicago',
    'austin', 'boston', 'denver', 'miami', 'toronto', 'vancouver',
    'asia only', 'apac only', 'india only', 'latam only',
    'united states', 'seattle, wa', 'washington, dc',
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


def fetch_jobicy():
    """Fetch jobs from Jobicy RSS feed (remote tech jobs)."""
    jobs = []
    try:
        resp = requests.get(
            'https://jobicy.com/feed/newjobs',
            headers={'User-Agent': 'RemoteJobSearch/1.0'},
            timeout=15,
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.text)

        for item in root.findall('./jobs/job'):
            pub_date = item.findtext('pubdate', '')
            posted = ''
            if pub_date:
                try:
                    # Jobicy uses DD.MM.YYYY format
                    posted = datetime.strptime(pub_date.strip(), '%d.%m.%Y').strftime('%Y-%m-%d')
                except Exception:
                    posted = pub_date[:10]

            jobs.append({
                'company': item.findtext('company', ''),
                'title': item.findtext('name', ''),
                'url': item.findtext('link', ''),
                'source': 'Jobicy',
                'location': item.findtext('region', 'Remote'),
                'tags': item.findtext('jobtype', ''),
                'posted_date': posted,
            })
        print(f"  Jobicy: {len(jobs)} jobs fetched")
    except Exception as e:
        print(f"  Jobicy error: {e}")
    return jobs


def fetch_weworkremotely():
    """Fetch jobs from We Work Remotely RSS feeds (programming + devops)."""
    jobs = []
    feeds = [
        'https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss',
        'https://weworkremotely.com/categories/remote-programming-jobs.rss',
    ]
    seen_guids = set()
    for feed_url in feeds:
        try:
            resp = requests.get(
                feed_url,
                headers={'User-Agent': 'RemoteJobSearch/1.0'},
                timeout=15,
            )
            resp.raise_for_status()
            root = ET.fromstring(resp.text)

            for item in root.findall('.//item'):
                guid = item.findtext('guid', '')
                if guid in seen_guids:
                    continue
                seen_guids.add(guid)

                # Title format: "Company: Job Title"
                raw_title = item.findtext('title', '')
                if ':' in raw_title:
                    company, title = raw_title.split(':', 1)
                    company = company.strip()
                    title = title.strip()
                else:
                    company = ''
                    title = raw_title.strip()

                region = item.findtext('region', 'Remote')
                country = item.findtext('country', '')
                location = region
                if country and country not in region:
                    location = f"{region}, {country}"

                pub_date = item.findtext('pubDate', '')
                posted = ''
                if pub_date:
                    try:
                        posted = parsedate_to_datetime(pub_date).strftime('%Y-%m-%d')
                    except Exception:
                        posted = pub_date[:10]

                jobs.append({
                    'company': company,
                    'title': title,
                    'url': guid or item.findtext('link', ''),
                    'source': 'WWR',
                    'location': location,
                    'tags': item.findtext('category', ''),
                    'posted_date': posted,
                })
        except Exception as e:
            print(f"  WWR error ({feed_url.split('/')[-1]}): {e}")

    print(f"  WeWorkRemotely: {len(jobs)} jobs fetched")
    return jobs


# ============= FILTER, SORT & DEDUP =============

# US indicators in location text
US_INDICATORS = [
    'united states', 'usa', 'us ', 'u.s.', 'america',
    'new york', 'san francisco', 'los angeles', 'seattle', 'chicago',
    'austin', 'boston', 'denver', 'miami', 'washington',
    'california', 'texas', ', ny', ', ca', ', wa',
    'toronto', 'vancouver', 'canada',
]

# EMEA indicators that allow a job to pass even if US is also mentioned
EMEA_SIGNALS = [
    'anywhere', 'worldwide', 'global', 'emea', 'europe', 'eu',
    'france', 'paris', 'uk', 'germany', 'netherlands',
    'belgium', 'spain', 'italy', 'switzerland', 'austria',
    'sweden', 'norway', 'denmark', 'portugal', 'ireland',
    'poland', 'czech', 'united kingdom', 'london',
]


def filter_jobs(jobs):
    """Filter jobs by role keywords, exclude irrelevant roles, and check location."""
    filtered = []
    for job in jobs:
        title_lower = job['title'].lower()
        location_lower = job['location'].lower()
        tags_lower = job['tags'].lower()
        search_text = f"{title_lower} {tags_lower}"

        # Exclude roles that need ML/data science, are frontend, devops, etc.
        if any(ex in search_text for ex in ROLE_EXCLUDE):
            continue

        # Must match at least one role keyword
        if not any(kw in search_text for kw in ROLE_KEYWORDS):
            continue

        # Strictly exclude jobs only targeting excluded regions
        loc_tags = f"{location_lower} {tags_lower}"
        if any(ex in loc_tags for ex in LOCATION_EXCLUDE):
            continue

        # Exclude US flag emoji
        if '\U0001f1fa\U0001f1f8' in job['location']:
            continue

        # Check for US/Canada mentions in location OR title
        loc_title = f"{location_lower} {title_lower}"
        has_us = any(us in loc_title for us in US_INDICATORS)

        if has_us:
            # Only keep if ALSO mentions an EMEA-compatible location
            has_emea = any(emea in loc_tags for emea in EMEA_SIGNALS)
            if not has_emea:
                continue

        # Must have an EMEA-compatible location signal
        if not any(inc in loc_tags for inc in LOCATION_INCLUDE):
            continue

        filtered.append(job)

    return filtered


def get_location_tier(job):
    """Return location priority tier (0=Paris, 1=France, 2=EMEA/CET, 3=UK, 4=global)."""
    loc = job['location'].lower()
    for keywords, tier in LOCATION_PRIORITY:
        if any(kw in loc for kw in keywords):
            return tier
    return 5  # Unknown location goes last


def sort_jobs(jobs):
    """Sort by location tier (Paris→France→EMEA→UK→Global), then by date descending."""
    return sorted(jobs, key=lambda j: (get_location_tier(j), j['posted_date'][::-1]))


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

TIER_LABELS = {0: 'Paris', 1: 'France', 2: 'EMEA / CET', 3: 'UK', 4: 'Global / Remote'}

def build_html(jobs):
    """Build styled HTML email with job listings grouped by location tier."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    date_str = datetime.now().strftime('%Y-%m-%d')

    rows_html = ''
    current_tier = None
    for job in jobs:
        tier = get_location_tier(job)
        if tier != current_tier:
            current_tier = tier
            label = TIER_LABELS.get(tier, 'Other')
            rows_html += f'                <tr style="background:#e8f5e9;font-weight:bold;"><td colspan="5" style="padding:4px 6px;font-size:11px;color:#2c3e50;">📍 {label}</td></tr>\n'

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

    sources = 'RemoteOK, Remotive, Arbeitnow, WWR, Jobicy'
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
            <p>📅 {now} | 📊 {len(jobs)} matching roles | 🔍 Sorted: Paris → France → EMEA/CET → UK → Global | Sources: {sources}</p>
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
            <p>📊 {len(jobs)} remote roles | Sources: {sources} | 🔄 Next: in 2 days at 12:00 CET</p>
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
    all_jobs.extend(fetch_weworkremotely())
    all_jobs.extend(fetch_jobicy())
    print(f"Total fetched: {len(all_jobs)}")

    # Filter and dedup
    filtered = filter_jobs(all_jobs)
    print(f"After role/location filter: {len(filtered)}")

    deduped = dedup_jobs(filtered)
    print(f"After dedup: {len(deduped)}")

    # Sort: Paris → France → EMEA/CET → UK → Global, then by date
    sorted_jobs = sort_jobs(deduped)

    # Build HTML and send
    html = build_html(sorted_jobs)
    send_email(html)


if __name__ == "__main__":
    main()

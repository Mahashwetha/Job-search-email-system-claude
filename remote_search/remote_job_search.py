"""
Remote Job Search — fetches remote-only listings from free APIs/feeds,
filters for EMEA-compatible roles matching user profile,
and sends a styled HTML email every 2 days.

Sources: RemoteOK, Remotive, Arbeitnow, We Work Remotely, Jobicy, LinkedIn (France)
"""

import sys
import os
import re
import json
import smtplib
import requests
import xml.etree.ElementTree as ET
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape

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
    # AI roles (not ML/data science prerequisite)
    'ai engineer', 'genai', 'llm engineer',
]

# Python is secondary — only include Python roles if they ALSO mention Java/backend
PYTHON_SECONDARY_KEYWORDS = ['python']
JAVA_BACKEND_SIGNALS = ['java', 'backend', 'back-end', 'back end', 'jvm', 'spring', 'microservices']

# Sources that are inherently EU-focused (jobs from these pass without explicit EMEA location)
EU_FOCUSED_SOURCES = ['Arbeitnow']

# Sources where "Remote" without region is common — allow if no US indicators found
RELAXED_LOCATION_SOURCES = ['Jobicy']

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
    'new grad', 'graduate engineer', 'entry level', 'junior ',
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
    'romania', 'hungary', 'greece', 'finland', 'croatia',
    'luxembourg', 'berlin', 'amsterdam', 'barcelona', 'munich',
    'dublin', 'lisbon', 'warsaw', 'prague', 'vienna', 'brussels',
    'gmt', 'cet', 'cest', 'central european', 'utc+1', 'utc+2',
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
    """Fetch jobs from Arbeitnow API (EU-focused), multiple pages."""
    jobs = []
    try:
        for page in range(1, 4):  # Fetch up to 3 pages
            resp = requests.get(
                f'https://www.arbeitnow.com/api/job-board-api?page={page}',
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            page_data = data.get('data', [])
            if not page_data:
                break
            for item in page_data:
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
                'company': unescape(item.findtext('company', '')),
                'title': unescape(item.findtext('name', '')),
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


def fetch_linkedin_france():
    """Fetch backend/Java jobs in France from LinkedIn's public guest API."""
    jobs = []
    queries = [
        'java+backend',
        'backend+engineer',
        'senior+software+engineer+java',
    ]
    seen_urls = set()
    for query in queries:
        try:
            # f_WT=2 filters to remote-only positions
            url = f'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={query}&location=France&f_WT=2&start=0'
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            if resp.status_code != 200:
                continue

            titles = re.findall(r'base-search-card__title[^>]*>([^<]+)<', resp.text)
            companies = re.findall(r'base-search-card__subtitle[^>]*>[^<]*<a[^>]*>([^<]+)<', resp.text)
            locations = re.findall(r'job-search-card__location[^>]*>([^<]+)<', resp.text)
            links = re.findall(r'href="(https://fr\.linkedin\.com/jobs/view/[^"]+)"', resp.text)

            for i in range(min(len(titles), len(companies), len(locations), len(links))):
                clean_url = unescape(links[i]).split('?')[0]
                if clean_url in seen_urls:
                    continue
                seen_urls.add(clean_url)

                title_text = titles[i].strip()

                jobs.append({
                    'company': companies[i].strip(),
                    'title': title_text,
                    'url': clean_url,
                    'source': 'LinkedIn FR',
                    'location': locations[i].strip(),
                    'tags': '',
                    'posted_date': datetime.now().strftime('%Y-%m-%d'),
                })
        except Exception as e:
            print(f"  LinkedIn FR error ({query}): {e}")

    print(f"  LinkedIn France: {len(jobs)} jobs fetched")
    return jobs


# Known EMEA tech companies → country (for enriching "Remote" listings)
KNOWN_COMPANY_COUNTRIES = {
    'tines': 'Ireland', 'intercom': 'Ireland', 'stripe': 'Ireland/US',
    'personio': 'Germany', 'celonis': 'Germany', 'contentful': 'Germany',
    'sap': 'Germany', 'delivery hero': 'Germany', 'zalando': 'Germany',
    'trustpilot': 'Denmark', 'unity': 'Denmark', 'pleo': 'Denmark',
    'klarna': 'Sweden', 'spotify': 'Sweden', 'king': 'Sweden',
    'adyen': 'Netherlands', 'booking.com': 'Netherlands', 'elastic': 'Netherlands',
    'revolut': 'UK', 'monzo': 'UK', 'wise': 'UK', 'deliveroo': 'UK',
    'datadog': 'France/US', 'criteo': 'France', 'doctolib': 'France',
    'alan': 'France', 'sorare': 'France', 'ledger': 'France',
    'veriff': 'Estonia', 'pipedrive': 'Estonia',
    'grafana labs': 'Sweden/Global', 'canonical': 'UK/Global',
    'gitlab': 'Global', 'automattic': 'Global',
    'meta': 'US', 'google': 'US', 'amazon': 'US', 'apple': 'US',
    'microsoft': 'US', 'netflix': 'US', 'uber': 'US', 'airbnb': 'US',
    'coinbase': 'US', 'robinhood': 'US', 'figma': 'US',
    'upstart': 'US', 'akamai': 'US', 'pnc': 'US', 'chainguard': 'US',
    'hashicorp': 'US', 'cloudflare': 'US', 'twilio': 'US',
}


def enrich_job_location(job):
    """Add company country info to jobs with vague 'Remote' location."""
    if job['location'].strip().lower() in ('remote', '', 'worldwide'):
        company_lower = job['company'].lower().strip()
        # Check known company lookup
        for known, country in KNOWN_COMPANY_COUNTRIES.items():
            if known in company_lower or company_lower in known:
                job['tags'] = f"{country}" + (f" | {job['tags']}" if job['tags'] else '')
                break
        # Check salary currency in tags/description for hints
        if '$' in job.get('tags', '') and '€' not in job.get('tags', ''):
            if not any(c in job.get('tags', '').lower() for c in ['ireland', 'uk', 'germany', 'france', 'global']):
                job['tags'] = (job['tags'] + ' | Likely US' if job['tags'] else 'Likely US')
    return job


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
    'romania', 'hungary', 'greece', 'finland', 'croatia',
    'luxembourg', 'berlin', 'amsterdam', 'barcelona', 'munich',
    'dublin', 'lisbon', 'warsaw', 'prague', 'vienna', 'brussels',
    'gmt', 'cet', 'cest', 'utc+1', 'utc+2',
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

        # Check primary role keywords
        matches_primary = any(kw in search_text for kw in ROLE_KEYWORDS)

        # Check secondary Python keyword
        matches_python = any(kw in search_text for kw in PYTHON_SECONDARY_KEYWORDS)

        if matches_python and not matches_primary:
            # Python-only role: only allow if it ALSO mentions Java/backend
            has_java_backend = any(sig in search_text for sig in JAVA_BACKEND_SIGNALS)
            if not has_java_backend:
                continue
        elif not matches_primary:
            # No keyword match at all
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

        # EU-focused sources (e.g., Arbeitnow) pass without explicit EMEA location
        if job.get('source') in EU_FOCUSED_SOURCES:
            filtered.append(job)
            continue

        # Must have an EMEA-compatible location signal
        has_emea_loc = any(inc in loc_tags for inc in LOCATION_INCLUDE)
        if has_emea_loc:
            filtered.append(job)
            continue

        # Relaxed sources: allow "Remote" with no region if no US indicators
        # Also exclude if enrichment tagged it as US company
        enriched_us = 'likely us' in tags_lower or tags_lower.startswith('us ')
        if job.get('source') in RELAXED_LOCATION_SOURCES and not has_us and not enriched_us:
            filtered.append(job)
            continue

    return filtered


def get_location_tier(job):
    """Return location priority tier (0=Paris, 1=France, 2=EMEA/CET, 3=UK, 4=global)."""
    loc = job['location'].lower()
    for keywords, tier in LOCATION_PRIORITY:
        if any(kw in loc for kw in keywords):
            return tier
    return 5  # Unknown location goes last


def is_explicitly_remote(job):
    """Check if a job explicitly mentions remote in title or location."""
    text = f"{job['title'].lower()} {job['location'].lower()}"
    return 'remote' in text or 'full remote' in text or 'télétravail' in text


def sort_jobs(jobs):
    """Sort by location tier, then remote-first within tier, then by date descending."""
    return sorted(jobs, key=lambda j: (
        get_location_tier(j),
        0 if is_explicitly_remote(j) else 1,  # remote first within tier
        j['posted_date'][::-1],
    ))


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


# ============= JOB HISTORY TRACKING =============

HISTORY_FILE = os.path.join(os.path.dirname(__file__), 'previous_jobs.json')


def load_previous_jobs():
    """Load previous job keys from history file."""
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return set(tuple(k) for k in json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_current_jobs(jobs):
    """Save current job keys to history file for next run comparison."""
    keys = [(j['company'].lower().strip(), j['title'].lower().strip()) for j in jobs]
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(keys, f)


def mark_new_jobs(jobs, previous_keys):
    """Mark each job as new or existing based on previous run."""
    for job in jobs:
        key = (job['company'].lower().strip(), job['title'].lower().strip())
        job['is_new'] = key not in previous_keys
    return jobs


# ============= HTML EMAIL =============

TIER_LABELS = {0: 'Paris', 1: 'France', 2: 'EMEA / CET', 3: 'UK', 4: 'Global / Remote', 5: 'Remote (Region Unspecified)'}

def build_html(jobs, new_count=0, total_unchanged=False):
    """Build styled HTML email with job listings grouped by location tier."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    date_str = datetime.now().strftime('%Y-%m-%d')

    # Banner for no-change or new jobs count
    banner_html = ''
    if total_unchanged:
        banner_html = '<div style="background:#fff3cd;color:#856404;padding:8px 12px;border-radius:4px;margin-bottom:8px;font-size:12px;font-weight:bold;text-align:center;">No new jobs since last run — all listings unchanged.</div>'
    elif new_count > 0:
        banner_html = f'<div style="background:#d4edda;color:#155724;padding:8px 12px;border-radius:4px;margin-bottom:8px;font-size:12px;font-weight:bold;text-align:center;">🆕 {new_count} new job(s) since last run — highlighted in green below.</div>'

    rows_html = ''
    current_tier = None
    for job in jobs:
        tier = get_location_tier(job)
        if tier != current_tier:
            current_tier = tier
            label = TIER_LABELS.get(tier, 'Other')
            rows_html += f'                <tr style="background:#e8f5e9;font-weight:bold;"><td colspan="5" style="padding:4px 6px;font-size:11px;color:#2c3e50;">📍 {label}</td></tr>\n'

        is_new = job.get('is_new', False)
        row_style = ' style="background:#d4edda;"' if is_new else ''
        new_badge = ' <span style="background:#28a745;color:white;padding:1px 4px;border-radius:3px;font-size:9px;font-weight:bold;">NEW</span>' if is_new else ''

        rows_html += f"""                <tr{row_style}>
                    <td><strong>{job['company']}</strong>{new_badge}</td>
                    <td><a href="{job['url']}" style="color: #3498db; text-decoration: underline;">{job['title']}</a></td>
                    <td>{job['source']}</td>
                    <td>{job['location']}<br><span style="font-size:9px;color:#7f8c8d;">{job['tags']}</span></td>
                    <td>{job['posted_date']}</td>
                </tr>
"""

    if not jobs:
        rows_html = '<tr><td colspan="5" style="text-align:center;padding:20px;color:#7f8c8d;">No matching remote roles found this run.</td></tr>\n'

    sources = 'RemoteOK, Remotive, Arbeitnow, WWR, Jobicy, LinkedIn FR'
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

        {banner_html}

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
    all_jobs.extend(fetch_linkedin_france())
    print(f"Total fetched: {len(all_jobs)}")

    # Enrich location info for vague "Remote" listings
    all_jobs = [enrich_job_location(job) for job in all_jobs]

    # Filter and dedup
    filtered = filter_jobs(all_jobs)
    print(f"After role/location filter: {len(filtered)}")

    deduped = dedup_jobs(filtered)
    print(f"After dedup: {len(deduped)}")

    # Sort: Paris → France → EMEA/CET → UK → Global, remote-first within tier
    sorted_jobs = sort_jobs(deduped)

    # Compare with previous run to detect new jobs
    previous_keys = load_previous_jobs()
    sorted_jobs = mark_new_jobs(sorted_jobs, previous_keys)
    new_count = sum(1 for j in sorted_jobs if j.get('is_new'))
    total_unchanged = len(previous_keys) > 0 and new_count == 0

    if total_unchanged:
        print(f"No new jobs since last run (all {len(sorted_jobs)} unchanged)")
    else:
        print(f"New jobs: {new_count} / {len(sorted_jobs)} total")

    # Save current jobs for next run comparison
    save_current_jobs(sorted_jobs)

    # Build HTML and send
    html = build_html(sorted_jobs, new_count=new_count, total_unchanged=total_unchanged)
    send_email(html)


if __name__ == "__main__":
    main()

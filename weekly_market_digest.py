"""
Weekly Job Market Intelligence Digest
Platform quality comparison (ghost %, response %, Q trend) for tech roles
in Paris / France / Remote-Europe. Uses Gemini knowledge — no job count scraping.
"""
import json
import re
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

from config import EMAIL_CONFIG, GOOGLE_API_KEY

GEMINI_MODEL = 'gemini-2.5-flash-lite'
GEMINI_URL = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent'

SEARCH_LINKS = {
    'LinkedIn':  'https://www.linkedin.com/jobs/search/?keywords=senior+java+developer&location=Paris%2C+France',
    'WTTJ':      'https://www.welcometothejungle.com/en/jobs?query=java+developer&refinementList%5Boffice_country_codes%5D%5B%5D=FR',
    'BuiltIn':   'https://builtin.com/jobs/eu/france/dev-engineering/search/java',
    'Remotive':  'https://remotive.com/remote-jobs/software-dev/java',
    'RemoteOK':  'https://remoteok.com/remote-backend+java-jobs',
    'Jobicy':    'https://jobicy.com/?feed=job_feed&job_categories=engineering&job_types=full-time&search_region=europe',
}

# ── Gemini call ───────────────────────────────────────────────────────────────

def _call_gemini(prompt):
    payload = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {
            'temperature': 0.2,
            'maxOutputTokens': 1000,
            'thinkingConfig': {'thinkingBudget': 0},
        },
    }
    for attempt in range(3):
        try:
            resp = requests.post(
                GEMINI_URL,
                headers={'Content-Type': 'application/json'},
                params={'key': GOOGLE_API_KEY},
                json=payload, timeout=30,
            )
            if resp.status_code in (429, 500, 503) and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            if resp.status_code == 200:
                return resp.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception:
            pass
    return None


# ── Generate structured digest via Gemini ────────────────────────────────────

def _generate_digest():
    today = datetime.now().strftime('%B %d, %Y')
    q_label = f'Q{(datetime.now().month - 1) // 3 + 1} {datetime.now().year}'
    prev_q = f'Q{((datetime.now().month - 1) // 3) or 4} {datetime.now().year if (datetime.now().month - 1) // 3 > 0 else datetime.now().year - 1}'

    prompt = f"""You are a job market analyst. Today is {today}.

A Senior Java Backend Tech Lead (11 years, Paris-based) wants a weekly snapshot of job platform QUALITY — not volume.
Focus: ghost job rate, response/callback rate, listing freshness, and how each platform has trended from {prev_q} to {q_label}.
Scope: Java backend / tech lead / AI engineering roles in Paris/France/Remote-Europe.

Platforms to cover: LinkedIn, WTTJ (Welcome to the Jungle), BuiltIn, Remotive, RemoteOK, Jobicy.

Use your training knowledge and known research about:
- LinkedIn ghost job / reposted listing rates in Europe (rising trend in 2025-2026)
- WTTJ curated model (companies pay to post, lower ghost rate, higher quality)
- BuiltIn EU freshness and sector focus
- Remotive / RemoteOK remote-first quality signals
- Jobicy niche positioning for remote Europe

Return ONLY valid JSON, no markdown, no explanation. Schema:

{{
  "platforms": [
    {{
      "name": "LinkedIn",
      "ghost_pct": "~X%",
      "response_pct": "~X%",
      "freshness": "X days avg",
      "q_vs_prev": "↑ worse / ↓ better / → stable",
      "one_line": "one honest sentence about quality for this profile"
    }}
  ],
  "verdict": "2-sentence overall verdict: which platform(s) to prioritise and why",
  "normalization": "one sentence: when does Paris/France/Europe tech hiring meaningfully pick up",
  "watch": "one concrete action for this week"
}}

All 6 platforms must appear in the array, in this order: LinkedIn, WTTJ, BuiltIn, Remotive, RemoteOK, Jobicy.
Use specific % estimates from published research where available; otherwise best-informed estimate labeled with ~.
"""
    raw = _call_gemini(prompt)
    if not raw:
        return None
    # Strip any accidental markdown code fences
    raw = re.sub(r'^```[a-z]*\n?', '', raw.strip(), flags=re.MULTILINE)
    raw = re.sub(r'\n?```$', '', raw.strip())
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON object from the text
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
    return None


# ── Email builder ─────────────────────────────────────────────────────────────

TREND_COLOR = {
    '↑': '#d93025',  # red = getting worse
    '↓': '#1e8e3e',  # green = getting better
    '→': '#888888',  # grey = stable
}

def _trend_cell(val):
    arrow = val[0] if val else '→'
    color = TREND_COLOR.get(arrow, '#888')
    label = val[2:] if len(val) > 2 else val
    return f'<span style="color:{color};font-weight:600">{arrow}</span> <span style="color:#555;font-size:11px">{label}</span>'


def _build_email(data, run_date):
    if not data:
        body = '<p style="color:#c00">Digest unavailable this week.</p>'
        table_html = ''
        verdict_html = ''
        norm_html = ''
        watch_html = ''
    else:
        platforms = data.get('platforms', [])

        # Platform comparison table
        rows = ''
        for p in platforms:
            name = p.get('name', '')
            link = SEARCH_LINKS.get(name, '#')
            ghost = p.get('ghost_pct', '?')
            reply = p.get('response_pct', '?')
            fresh = p.get('freshness', '?')
            trend = _trend_cell(p.get('q_vs_prev', '→ stable'))
            note = p.get('one_line', '')
            rows += f"""
            <tr>
              <td style="padding:7px 10px;font-weight:600;white-space:nowrap">
                <a href="{link}" style="color:#1a73e8;text-decoration:none">{name}</a>
              </td>
              <td style="padding:7px 10px;text-align:center;color:#c00">{ghost}</td>
              <td style="padding:7px 10px;text-align:center;color:#1e8e3e">{reply}</td>
              <td style="padding:7px 10px;text-align:center;color:#555">{fresh}</td>
              <td style="padding:7px 10px;text-align:center">{trend}</td>
              <td style="padding:7px 10px;color:#555;font-size:11.5px">{note}</td>
            </tr>"""

        table_html = f"""
        <table style="width:100%;border-collapse:collapse;font-size:12.5px;margin-bottom:14px">
          <thead>
            <tr style="background:#f8f9fa;color:#444;font-size:11px">
              <th style="padding:6px 10px;text-align:left;font-weight:600">Platform</th>
              <th style="padding:6px 10px;text-align:center;font-weight:600" title="Ghost / reposted listing rate">Ghost%</th>
              <th style="padding:6px 10px;text-align:center;font-weight:600" title="Callback / response rate">Reply%</th>
              <th style="padding:6px 10px;text-align:center;font-weight:600">Freshness</th>
              <th style="padding:6px 10px;text-align:center;font-weight:600">Q trend</th>
              <th style="padding:6px 10px;text-align:left;font-weight:600">Signal</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>"""

        verdict = data.get('verdict', '')
        norm = data.get('normalization', '')
        watch = data.get('watch', '')

        verdict_html = f'<div style="background:#e8f0fe;border-radius:6px;padding:10px 14px;font-size:13px;color:#1a1a1a;margin-bottom:10px"><strong>Verdict</strong><br>{verdict}</div>'
        norm_html = f'<div style="font-size:12px;color:#555;margin-bottom:10px"><strong>Hiring normalisation:</strong> {norm}</div>'
        watch_html = f'<div style="background:#e6f4ea;border-radius:6px;padding:10px 14px;font-size:12.5px;color:#1a1a1a"><strong>Watch this week:</strong> {watch}</div>'
        body = ''

    source_links = ' &nbsp;|&nbsp; '.join(
        f'<a href="{url}" style="color:#1a73e8;font-size:11.5px;text-decoration:none">{name}</a>'
        for name, url in SEARCH_LINKS.items()
    )

    q_label = f'Q{(datetime.now().month - 1) // 3 + 1} {datetime.now().year}'

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
  tr:nth-child(even){{background:#fafafa}}
  tr:hover{{background:#f0f4ff}}
  th{{border-bottom:2px solid #e0e0e0}}
  td{{border-bottom:1px solid #f0f0f0}}
</style>
</head>
<body style="font-family:Arial,sans-serif;background:#f5f5f5;margin:0;padding:16px">
<div style="max-width:760px;margin:0 auto;background:#fff;border-radius:8px;padding:20px 24px">

  <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:14px">
    <div>
      <span style="font-size:16px;font-weight:700;color:#1a1a1a">Job Market Pulse</span>
      <span style="font-size:12px;color:#888;margin-left:10px">{run_date} &bull; {q_label} &bull; Paris / France / Remote-Europe</span>
    </div>
    <span style="font-size:11px;color:#bbb">Java Backend &bull; Tech Lead &bull; AI Eng</span>
  </div>

  {table_html}
  {verdict_html}
  {norm_html}
  {watch_html}
  {body}

  <div style="margin-top:14px;padding-top:10px;border-top:1px solid #eee;font-size:11px;color:#aaa;text-align:center">
    {source_links}
  </div>

</div>
</body></html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    print('=== Weekly Job Market Intelligence ===')
    print(f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}')

    print('\nGenerating platform comparison via Gemini...')
    data = _generate_digest()
    if data:
        print('Platforms received:', [p.get('name') for p in data.get('platforms', [])])
        print('Verdict:', data.get('verdict', '')[:80])
    else:
        print('WARNING: Gemini returned no structured data.')

    run_date = datetime.now().strftime('%B %d, %Y')
    html = _build_email(data, run_date)

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f'Job Market Pulse — {run_date}'
    msg['From'] = EMAIL_CONFIG['sender_email']
    msg['To'] = EMAIL_CONFIG['recipient_email']
    msg.attach(MIMEText(html, 'html'))

    with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
        server.starttls()
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        server.send_message(msg)

    print('SUCCESS: Market intelligence email sent.')


if __name__ == '__main__':
    run()

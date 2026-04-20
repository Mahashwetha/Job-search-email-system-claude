"""
Outreach Email Sender
Sends a personalised outreach email to an HR contact using a template.

Usage:
    python send_outreach_emails.py \\
        --name   "Andrea Hallery" \\
        --email  "andrea.hallery@natixis.com" \\
        --cc     "clemence.pedral@natixis.com" \\
        --company "Natixis CIB" \\
        --role   "Tech Lead Pricing Pre Trade" \\
        --template followup

    Templates (in emailoutreach/):
        followup  → followup_template.txt   (for roles already applied to)
        cold      → cold_outreach_template.txt  (spontaneous / cold outreach)

    Always previews first.
    Add --send to actually send the email.

Examples:
    # Preview only
    python send_outreach_emails.py --name "Lucie Delavay" --email "lucie.delavay@filigran.io" --company "Filigran" --role "Staff Tech Lead OpenCTI" --template followup

    # Send
    python send_outreach_emails.py --name "Lucie Delavay" --email "lucie.delavay@filigran.io" --company "Filigran" --role "Staff Tech Lead OpenCTI" --template followup --send
"""

import argparse
import os
import re
import smtplib
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

# ============= PATHS (no personal data — safe for GitHub) =============

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
RESUME_DIR    = os.path.join(BASE_DIR, 'resume')
TEMPLATE_DIR  = os.path.join(BASE_DIR, 'emailoutreach')

ATTACHMENTS = [
    os.path.join(RESUME_DIR, 'mahashwetharao_resume_2026_English.pdf'),
    os.path.join(RESUME_DIR, 'portfolio_personal_projects_mahashwetha.pdf'),
]

TEMPLATES = {
    'followup': 'followup_template.txt',
    'cold':     'cold_outreach_template.txt',
}

# ============= CONFIG =============

try:
    from config import EMAIL_CONFIG
except ImportError:
    print("ERROR: config.py not found. Copy config.template.py to config.py.")
    raise SystemExit(1)


# ============= HELPERS =============

def load_template(name):
    filename = TEMPLATES.get(name)
    if not filename:
        print(f"ERROR: Unknown template '{name}'. Choose from: {list(TEMPLATES)}")
        raise SystemExit(1)
    path = os.path.join(TEMPLATE_DIR, filename)
    with open(path, encoding='utf-8') as f:
        return f.read()


def fill_template(template, first_name, company, role):
    return template.replace('{first_name}', first_name) \
                   .replace('{company}', company) \
                   .replace('{role}', role)


def extract_subject(filled):
    """Extract subject line from template (first line after SUBJECT:)."""
    match = re.search(r'SUBJECT:\s*(.+)', filled)
    if match:
        return match.group(1).strip()
    return "Application Follow-up"


def extract_body(filled):
    """Extract body — everything after the --- separator."""
    parts = filled.split('---', 1)
    if len(parts) > 1:
        return parts[1].strip()
    return filled.strip()


def preview(to, cc, subject, body):
    print("\n" + "=" * 60)
    print(f"TO:      {to}")
    if cc:
        print(f"CC:      {cc}")
    print(f"SUBJECT: {subject}")
    print("-" * 60)
    print(body)
    print("=" * 60)
    missing = [p for p in ATTACHMENTS if not os.path.exists(p)]
    found   = [os.path.basename(p) for p in ATTACHMENTS if os.path.exists(p)]
    print(f"ATTACHMENTS: {', '.join(found)}")
    if missing:
        print(f"WARNING — missing: {', '.join(missing)}")
    print()


def send(to, cc, subject, body):
    msg = MIMEMultipart()
    msg['From']    = EMAIL_CONFIG['sender_email']
    msg['To']      = to
    if cc:
        msg['Cc']  = cc
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    for path in ATTACHMENTS:
        if not os.path.exists(path):
            print(f"  WARNING: attachment not found: {path}")
            continue
        with open(path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition',
                        f'attachment; filename="{os.path.basename(path)}"')
        msg.attach(part)

    recipients = [to] + ([cc] if cc else [])
    server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
    server.starttls()
    server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
    server.sendmail(EMAIL_CONFIG['sender_email'], recipients, msg.as_string())
    server.quit()
    print(f"  SENT to {to}" + (f" (CC: {cc})" if cc else ""))


# ============= MAIN =============

def main():
    parser = argparse.ArgumentParser(description='Send outreach email to HR contact.')
    parser.add_argument('--name',     required=True,  help='HR contact full name, e.g. "Andrea Hallery"')
    parser.add_argument('--email',    required=True,  help='HR contact email')
    parser.add_argument('--cc',       default='',     help='CC email (optional)')
    parser.add_argument('--company',  required=True,  help='Company name')
    parser.add_argument('--role',     required=True,  help='Role title')
    parser.add_argument('--template', required=True,  choices=list(TEMPLATES), help='Template: followup | cold')
    parser.add_argument('--send',     action='store_true', help='Actually send (omit for dry-run preview)')
    args = parser.parse_args()

    first_name = args.name.split()[0]
    template   = load_template(args.template)
    filled     = fill_template(template, first_name, args.company, args.role)
    subject    = extract_subject(filled)
    body       = extract_body(filled)

    preview(args.email, args.cc, subject, body)

    if not args.send:
        print("DRY RUN — add --send to actually send this email.")
        return

    confirm = input("Send this email? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Cancelled.")
        return

    send(args.email, args.cc, subject, body)


if __name__ == '__main__':
    main()

"""
Outreach Email Sender

Usage:
    python send_outreach_emails.py --name "Andrea Hallery" --email "andrea.hallery@natixis.com" --company "Natixis CIB"

The script will:
  1. Look up the role from your tracker automatically
  2. Always use the cold outreach (Jinka-style) template
  3. Show you a preview
  4. Ask yes/no before sending

Optional:
  --cc "someone@company.com"   Add a CC recipient

-------------------------------------------------------------------
USER CONFIG — update these paths to match your local setup
-------------------------------------------------------------------
"""

import argparse
import os
import re
import smtplib
import openpyxl
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

# ---------------------------------------------------------------
# PATHS — edit these to point to your local folders
# ---------------------------------------------------------------

# Folder containing your resume and portfolio PDFs
# Example: r"C:\Users\yourname\Documents\Resume" or "/home/yourname/resume"
RESUME_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resume')

# Folder containing your email templates (cold_outreach_template.txt, followup_template.txt)
# Example: r"C:\Users\yourname\Documents\EmailTemplates"
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'emailoutreach')

# PDF files to attach — update filenames to match your actual files
ATTACHMENTS = [
    os.path.join(RESUME_DIR, 'mahashwetharao_resume_2026_English.pdf'),       # <-- your resume PDF
    os.path.join(RESUME_DIR, 'portfolio_personal_projects_mahashwetha.pdf'),   # <-- your portfolio PDF
]

# ---------------------------------------------------------------

try:
    from config import EMAIL_CONFIG, TRACKER_FILE
except ImportError:
    print("ERROR: config.py not found.")
    raise SystemExit(1)


def find_role_in_tracker(company):
    """Look up the most recent active role for a company in the tracker."""
    try:
        wb = openpyxl.load_workbook(TRACKER_FILE, data_only=True)
        ws = wb.active
        for row in reversed(list(ws.iter_rows(min_row=2, values_only=True))):
            co = str(row[0]).strip() if row[0] else ""
            role = str(row[1]).strip() if row[1] else ""
            status = str(row[3]).strip().lower() if row[3] else ""
            if company.lower() in co.lower() and status == 'done':
                return role
    except Exception:
        pass
    return None


def load_template(name):
    path = os.path.join(TEMPLATE_DIR, name)
    with open(path, encoding='utf-8') as f:
        return f.read()


def fill_template(template, first_name, company, role):
    return template.replace('{first_name}', first_name) \
                   .replace('{company}', company) \
                   .replace('{role}', role)


def extract_subject(filled):
    match = re.search(r'SUBJECT:\s*(.+)', filled)
    return match.group(1).strip() if match else "Application Follow-up"


def extract_body(filled):
    parts = filled.split('---', 1)
    return parts[1].strip() if len(parts) > 1 else filled.strip()


def send_email(to, cc, subject, body):
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name',    required=True, help='HR contact full name')
    parser.add_argument('--email',   required=True, help='HR contact email')
    parser.add_argument('--company', required=True, help='Company name')
    parser.add_argument('--cc',      default='',    help='CC email (optional)')
    args = parser.parse_args()

    first_name = args.name.split()[0]

    # Auto-detect role; always use cold outreach (Jinka-style) for first HR contact
    role = find_role_in_tracker(args.company)
    if role:
        print(f"Found in tracker: {args.company} | {role}")
    else:
        role = args.company + ' opportunities'
        print(f"Not in tracker: {args.company} -> role set to '{role}'")
    template_file = 'cold_outreach_template.txt'
    print(f"Using cold outreach template")

    template = load_template(template_file)
    filled   = fill_template(template, first_name, args.company, role)
    subject  = extract_subject(filled)
    body     = extract_body(filled)

    # Preview
    print("\n" + "=" * 60)
    print(f"TO:      {args.email}")
    if args.cc:
        print(f"CC:      {args.cc}")
    print(f"SUBJECT: {subject}")
    print("-" * 60)
    print(body)
    print("=" * 60)
    found = [os.path.basename(p) for p in ATTACHMENTS if os.path.exists(p)]
    print(f"ATTACHMENTS: {', '.join(found)}\n")

    confirm = input("Send this email? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Cancelled.")
        return

    send_email(args.email, args.cc, subject, body)
    print(f"Sent to {args.email}")


if __name__ == '__main__':
    main()

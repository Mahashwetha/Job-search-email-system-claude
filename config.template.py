"""
Configuration Template for Claude Job Search Agent

INSTRUCTIONS:
1. Copy this file and rename it to 'config.py'
2. Fill in your actual email credentials
3. Set the path to your Excel application tracker
4. Update USER_PROFILE with your details
5. NEVER commit config.py to GitHub (it's in .gitignore)
"""

# Email Configuration
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'your_email@gmail.com',        # ← Your Gmail address
    'sender_password': 'your_app_password_here',    # ← Your Gmail App Password (16 chars)
    'recipient_email': 'your_email@gmail.com',      # ← Where to receive job emails
}

# Excel Tracker Path
# Set this to the absolute path of your application tracker Excel file
# Example: r'C:\Users\YourName\Documents\Applications\Tracker.xlsx'
TRACKER_FILE = r'C:\Path\To\Your\Application\Tracker.xlsx'

# LinkedIn Profile URL (used in outreach drafts)
LINKEDIN_URL = 'https://www.linkedin.com/in/your-profile/'

# User Profile (used by outreach drafter templates)
USER_PROFILE = {
    'name': 'Your Name',                           # Full name for outreach messages
    'background': 'a software engineer',            # Short background for short messages
    'origin_country': 'Your Country',               # Country of origin for long template
    'experience_years': 5,                          # Years of experience
    'location': 'City, Country',                    # Current location
    'domain_expertise': 'software development',     # Short domain, e.g. "Java/fintech"
}

# Gemini API Key (free tier) — used by resume_tailor.py
# Get yours at: https://aistudio.google.com/apikey
GOOGLE_API_KEY = 'your_gemini_api_key_here'

# Base resume DOCX path — the master copy that gets tailored per company
BASE_RESUME_PATH = r'C:\Path\To\Your\base_resume.docx'

# Output directory for tailored resumes
RESUME_OUTPUT_DIR = r'C:\Path\To\Your\resume_adjusted'

# How to get Gmail App Password:
# 1. Go to Google Account → Security → 2-Step Verification
# 2. Scroll to "App passwords" at the bottom
# 3. Select "Mail" and your device
# 4. Copy the 16-character password (no spaces)
# 5. Paste it in 'sender_password' above

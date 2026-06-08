"""
fit-check — quick job fit analysis from the command line.

Usage:
  python fit_check.py <job_url>
  python fit_check.py <job_url> --title "Senior Java Developer" --company "Acme"

If --title is omitted, it is guessed from the URL slug.
"""

import argparse
import re
import sys


def main():
    parser = argparse.ArgumentParser(description='Score a job\'s fit against your resume')
    parser.add_argument('url', help='Job posting URL')
    parser.add_argument('--title',   default='', help='Job title (optional, inferred from URL if omitted)')
    parser.add_argument('--company', default='', help='Company name (optional)')
    args = parser.parse_args()

    try:
        from fit_scorer import score_fit_single, FIT_SCORE_ENABLED, _FIT_SCORER_AVAILABLE
    except ImportError:
        print('ERROR: fit_scorer.py not found. Make sure you run this from the claude-job-agent directory.')
        sys.exit(1)

    if not _FIT_SCORER_AVAILABLE:
        print('ERROR: Gemini API key not configured. Set GOOGLE_API_KEY in config.py.')
        sys.exit(1)

    if not FIT_SCORE_ENABLED:
        print('ERROR: FIT_SCORE_ENABLED is False in config.py. Set it to True to use fit-check.')
        sys.exit(1)

    # Infer title from URL if not provided
    title = args.title
    if not title:
        # e.g. /jobs/senior-backend-go-engineer-trust-tools_paris → "Senior Backend Go Engineer Trust Tools"
        slug = re.sub(r'[-_]', ' ', args.url.rstrip('/').split('/')[-1].split('?')[0])
        slug = re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z\s]', ' ', slug)).strip()
        title = slug.title() if slug else 'Unknown Role'
        print(f'  Title inferred from URL: "{title}"')

    company = args.company

    print(f'\n{"="*55}')
    print(f'  Job Fit Analysis')
    print(f'{"="*55}')
    print(f'  Role:    {title}')
    if company:
        print(f'  Company: {company}')
    print(f'  URL:     {args.url}')
    print()

    result = score_fit_single(args.url, title, company)

    if not result:
        print('ERROR: Could not get fit score. Check your API key and network.')
        sys.exit(1)

    score = result.get('score', 0)
    verdict = result.get('verdict', '')
    has_desc = result.get('description_used', False)

    # Colour verdict for terminal
    _colours = {
        'Strong':   '\033[92m',   # bright green
        'Good':     '\033[32m',   # green
        'Moderate': '\033[33m',   # yellow
        'Weak':     '\033[91m',   # bright red
    }
    reset = '\033[0m'
    colour = _colours.get(verdict, '')

    print(f'  Score:          {colour}{score}% — {verdict}{reset}')
    print(f'  Description:    {"fetched ✓" if has_desc else "not available — title-only estimate"}')
    print()
    print(f'  Strengths:')
    for line in result.get('strengths', '').split('. '):
        if line.strip():
            print(f'    • {line.strip().rstrip(".")}')
    print()
    print(f'  Gaps:')
    for line in result.get('gaps', '').split('. '):
        if line.strip():
            print(f'    • {line.strip().rstrip(".")}')
    print()
    print(f'  Recommendation: {colour}{result.get("recommendation", "")}{reset}')
    print(f'{"="*55}\n')


if __name__ == '__main__':
    main()

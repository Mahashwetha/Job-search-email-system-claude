---
name: fit-check
description: Score a job posting's fit against your resume using Gemini. Fetches the full job description and returns a score, strengths, gaps, and recommendation. Triggers on phrases like "fit-check <url>", "is this a good fit <url>", "check fit for <url>", "score this job <url>".
---

# Fit Check

Run a job fit analysis against the user's resume using `fit_check.py`.

## Trigger

User says `fit-check <url>` or pastes a job URL asking "is this a good fit" / "check fit".

## Steps

1. Extract the URL from the user's message.
2. Optionally extract `--title` and `--company` if the user mentioned them.
3. Run from the project root:

```
cd C:\Users\mahas\Learnings\claude-job-agent
python fit_check.py "<url>" [--title "..."] [--company "..."]
```

4. Show the output to the user.
5. If the score is **Weak or Moderate**, offer a brief 1-line note on whether it's still worth applying (e.g. if it's a stretch role they want to aim for).

## Notes

- `fit_scorer.py` must be in the same directory (it is).
- `FIT_SCORE_ENABLED = True` must be set in `config.py` (default is True).
- WTTJ and BuiltIn URLs are supported. LinkedIn guest API is also supported.
- If description fetch fails, the score is title-only — the output will say so.

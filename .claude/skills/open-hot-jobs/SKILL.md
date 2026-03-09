---
name: open-hot-jobs
description: This skill should be used when the user wants to open hot job listings in Chrome. Triggers on phrases like "open hot jobs", "open [category] hot jobs in chrome", "open all backend jobs", "open jobs in browser", "open [category] jobs chrome".
---

# Open Hot Jobs in Chrome

Opens job URLs from `daily_hot_jobs.json` in Chrome tabs.

## Categories (exact keys in JSON)
- `Senior Java`
- `Backend Java`
- `Product Owner`
- `Assistant Project Manager`
- `Tech Lead / Lead Developer`
- `AI / GenAI Engineer`

## Steps

1. Read `daily_hot_jobs.json`.
2. Identify which category the user wants (or all categories if unspecified).
3. Extract the `url` field from each job in `current_jobs[category]`.
4. Open all URLs at once using: `start chrome "url1" "url2" ...`
5. Confirm how many tabs were opened and for which category.

## Notes
- If no category is specified, ask the user which one (or confirm if they want all).
- If a category has no jobs (`[]`), tell the user it's empty.
- Use Comet browser (Perplexity): `"/c/Users/YOU/AppData/Local/Perplexity/Comet/Application/comet.exe" --new-window "url1" "url2" ... &`
- Always open in a new window using `--new-window`.

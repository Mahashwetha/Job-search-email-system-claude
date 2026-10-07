---
name: resume-tailor
description: This skill should be used when the user wants to tailor or customize their resume for a specific job or company. Triggers on phrases like "tailor resume for [company]", "customize resume for [job]", "generate resume for [company]", "adapt resume to this job posting", "create resume for [company] role".
---

# Resume Tailor (evidence-only, with skill confirmation)

Tailors the current CV DOCX for one job using `cv_tailor.py`. Claude does the comparison and asks
the user which missing skills they really have; the script applies the edits and exports DOCX + PDF.
No Gemini call, so it uses none of the 20/day free quota.

## Steps

1. **Get the job description.** Run `python cv_tailor.py jd "<url>"`. Any job link works: LinkedIn,
   Welcome to the Jungle, Ashby and Greenhouse use the site's own data for a clean description;
   other sites (company career pages, Workday, etc.) fall back to reading the page. If it fails
   (login walls, closed jobs), ask the user to paste the description.
2. **Read the CV.** Run `python cv_tailor.py cv` (prints each paragraph of the base CV DOCX).
3. **Compare.** List the JD's skills/requirements, in English even if the JD is French. Split them into:
   - already on the CV (nothing to do, or surface better wording if the evidence is there)
   - missing from the CV
4. **Ask with multi-select.** Use AskUserQuestion with `multiSelect: true`: up to 4 questions of up
   to 4 missing skills each, mandatory JD skills first. Question text like "Which of these have you
   used in real work?". The user can type extra detail in "Other" (e.g. the tool they used).
   If a confirmed skill needs context to be described honestly (where/how), ask a short follow-up.
5. **Draft edits** (rules below) and write them to a JSON file in the scratchpad:
   `{"replace": [{"old": "...", "new": "..."}], "add_skills": ["..."]}`.
   Each `old` must sit inside ONE run of the DOCX. Bold highlights are separate runs, so keep each
   edit within a plain or a bold segment of the paragraph text from step 2.
6. **Apply.** Run `python cv_tailor.py apply "<Company>" <edits.json>`.
7. **Report** the "Words changed" output from `apply` (shown as removed -> added), the confirmed skills added, the page count,
   the JD skills still missing, and the output paths.

## Edit rules

- Only facts on the CV or confirmed by the user in step 4. Never invent tools, numbers or domains.
- Keep content intact: never delete Projects, the NDS acquisition note, education details or the
  word "fintech" in the SMARTS bullet. No "| Fintech" in the title line.
- Confirmed skills go into the `Frameworks & Tools:` line via `add_skills`, not into a specific
  job's bullet, unless the user said where they used it.
- Never write "learning / deepening / upskilling in X" for a gap.
- English only. Do not switch to the JD's language.
- Going over 1 page is acceptable. Prefer edits that don't add lines, and say when the CV grows.

## Output

`resume_adjusted\resume_<company>.docx` and `.pdf` (folder from `RESUME_OUTPUT_DIR` in `config.py`).
An existing file with the same name is overwritten.

Base CV: `Resume2026\SingleBlockResume- 2026augnew\Mahashwetha_resume_2026_centurygothic_aug.docx`
(override with `BASE_CV_DOCX` in `config.py`). PDF export needs Microsoft Word.

## Legacy

`resume_tailor.py` (Gemini, batch from tracker) targets the OLD CV layout (fixed paragraph
numbers) and a PDF base path, so it does not work with the current CV. Use the steps above.

# Instructions for AI agents working with this resume Markdown

This file defines the rules an AI agent must follow when working with
`curriculo_base_PT.md` / `curriculo_base_EN.md` in this project, for two
distinct use cases:

1. **Creating a new base resume from scratch**, when the candidate does not
   have `curriculo_base_PT.md` / `curriculo_base_EN.md` yet and instead
   provides raw information about themselves.
2. **Adapting an existing base resume to a specific job posting**, producing
   `_adapted.md` versions without touching the base files.

Both use cases must follow the same structural rules below, so the result
stays parseable by the project's Markdown-to-PDF script.

## Structural rules (required to keep the resume parseable)

The Markdown-to-PDF script uses a simple positional parser, not a general
Markdown renderer, so it depends on the exact structural shape below being
followed precisely. In short:

- Exactly one `# Name` line (H1).
- One loose line right below the name (subtitle/target role). This is
  self-description, not a factual claim, so it can be freely written or
  rewritten to match the candidate's target role.
- The **first** `##` section of the file must be the contact block: only
  `- Label: value` bullet lines, nothing else added there.
- Every other `##` section is a normal section (Experience, Education,
  Skills, Languages, Cover Letter, etc.). Sections may be reordered, but
  keep them as `##` headings, no special names required, the script parses
  by position/shape, not by section name.
- Inside a section, an entry is `### Job title/Degree` followed by a line
  `**Company/Institution** | Period`, followed by `-` bullets. Keep this
  exact 3-part shape for every entry (heading line, bold company/period
  line, bullets).
- Bullets always start with `-` (not `*`, not a bullet character).
- No tables, no images, no multi-column tricks, no raw HTML.

## Use case 1: Creating a new base resume from scratch

### When this applies

The candidate has no `curriculo_base_PT.md` / `curriculo_base_EN.md` yet and
provides raw information about themselves (an old resume in any format,
LinkedIn export, free-text notes, etc.) instead.

### Rules

1. **Never invent facts.** Only use information the candidate explicitly
   provided. Do not add employers, job titles, dates, degrees,
   certifications, tools, or skills that weren't stated or clearly implied
   by what was given.
2. **Ask about missing information instead of guessing.** Before producing
   the final files, check whether you have enough to fill in:
   - Full name and contact info (phone, email, LinkedIn, location, and
     optionally GitHub/portfolio).
   - A target role or area of interest (used for the subtitle and the
     summary).
   - At least one experience or education entry with company/institution
     name and period.
   - Relevant skills.
   If something is missing or ambiguous (e.g. a period with no end date,
   an unclear job title, no explicit target role), explicitly list what is
   missing and ask the candidate before finishing, instead of leaving
   placeholders or making assumptions.
3. **Write both language files in parallel.** Produce `curriculo_base_PT.md`
   (100% Portuguese) and `curriculo_base_EN.md` (100% English) as full,
   independent translations of the same facts, not a mechanical
   word-for-word translation, each should read naturally in its own
   language.
4. **Follow the structural rules above** for both files.
5. **Do not overwrite an existing base file without asking.** If
   `curriculo_base_PT.md` or `curriculo_base_EN.md` already exists in the
   target location, confirm with the candidate before replacing it, this
   use case is meant for candidates who don't have one yet.

### Writing the Summary/Objective section

The `## Objetivo` / `## Objective` section (right after the contact block)
is the resume's summary. Since it's self-presentation rather than a factual
claim, it can be freely composed, but it must stay consistent with the
Experience/Education sections that follow it.

- Length: 2 to 4 lines, one paragraph, no bullets.
- Content: state the target role or area, the candidate's current stage
  (e.g. student, recent graduate, N years of experience), one or two
  standout strengths backed by the Experience/Education/Skills sections,
  and what the candidate is looking for.
- Tone: professional and factual. Do not use superlatives or claims that
  aren't backed by the rest of the resume (no "expert", "top performer",
  etc. unless the candidate's own information supports it).
- Avoid buzzword stuffing and generic filler ("proactive team player
  passionate about excellence") that carries no real information.
- Keyword relevance: naturally include the terms that describe the
  candidate's target role/area, since this section is read early by both
  ATS and human/AI reviewers.

### Self-check before finishing

- [ ] No fact was invented, everything traces back to what the candidate
      provided.
- [ ] All missing/ambiguous information was flagged and asked about, not
      guessed.
- [ ] `curriculo_base_PT.md` and `curriculo_base_EN.md` describe the exact
      same facts, each written naturally in its own language.
- [ ] The structural shape (H1 / contact section / `##` sections / `###` +
      bold dateline + bullets / `-` bullets) matches the rules above.
- [ ] The Summary/Objective section follows the guidance above and is
      consistent with the rest of the resume.
- [ ] No existing base file was overwritten without confirmation.

## Use case 2: Adapting an existing resume for a specific job posting

The goal is to maximize relevance and ATS keyword match for a specific job
**without ever inventing or misrepresenting anything** about the candidate.
This use case is given to an AI agent together with: the current resume
Markdown file(s) and the job posting text.

### Hard rules (never break these)

1. **Never invent facts.** Do not add employers, job titles, dates, degrees,
   certifications, tools, or skills that are not already present in the base
   Markdown file. If the job posting asks for a skill the candidate doesn't
   have evidence of in the base file, do not add it.
2. **Never change facts.** Company names, job titles, dates/periods,
   institution names, and degree names must stay exactly as in the base
   file.
3. **Rephrasing and reordering are allowed, fabrication is not.** You may:
   - Reorder bullets within an experience/education entry to put the most
     job-relevant ones first.
   - Reorder skills in the Skills/Habilidades section to prioritize the ones
     the job posting asks for.
   - Rephrase a bullet using the job posting's terminology, as long as the
     underlying fact/achievement is the same (e.g. "aprendizado de máquina"
     to "machine learning" is fine; turning a LiDAR-processing bullet into a
     claim about a technology never mentioned in the base file is not).
   - Condense less relevant bullets/entries to save space for more relevant
     ones. Prefer condensing over deleting entirely.
   - Fully rewrite the Objective/Summary and Cover Letter sections to speak
     directly to the job posting, following the same summary guidance from
     Use case 1 above, as long as they stay consistent with the real
     background in the Experience/Education sections.
4. **Only remove an entire experience/education entry** if it is clearly
   irrelevant to the target job AND removing it does not create a
   misleading gap or inaccurate impression of the candidate's background.
   When in doubt, condense instead of removing.
5. **Keep language consistent per file.** `curriculo_base_PT*.md` stays
   100% in Portuguese, `curriculo_base_EN*.md` stays 100% in English. Do not
   mix languages within a file, even when copying a term from the job
   posting (translate it).
6. Apply the same set of changes to **both** the PT and EN files so they
   stay equivalent translations of each other.

### Keyword-matching guidance (for ATS relevance)

1. Extract the key requirements, technologies, tools, and role-specific
   terms from the job posting.
2. For each one that the candidate's base file already demonstrates
   (anywhere: experience, education, or skills), make sure the exact
   wording/acronym used in the job posting also appears in the adapted file
   (e.g. if the base file says "aprendizado de máquina" and the job posting
   says "Machine Learning", make sure "Machine Learning"/"aprendizado de
   máquina" (matching the file's language) is explicitly present, not just
   a synonym).
3. Do not keyword-stuff: do not repeat a term many times or list irrelevant
   tools just because the job posting mentions them. Every keyword you add
   must correspond to something real in the base file.
4. Prioritize: put the most relevant experience entry first if reordering
   sections is reasonable, and put the most relevant bullets first within
   each entry.

### Output

- Never overwrite the base files (`curriculo_base_PT.md`,
  `curriculo_base_EN.md`).
- Write the result to `<original filename without extension>_adapted.md`,
  e.g. `curriculo_base_PT_adapted.md` and `curriculo_base_EN_adapted.md`.
- If `_adapted.md` files already exist from a previous job application,
  overwrite them (they represent "the current tailored version", not a
  history).

### Self-check before finishing

- [ ] No new employer/school/degree/certification/date was invented.
- [ ] No date, company name, or institution name was changed.
- [ ] Every fact-bearing claim in the adapted bullets is traceable to
      something in the base file.
- [ ] The PT and EN adapted files describe the same set of facts.
- [ ] The structural shape (H1 / contact section / `##` sections / `###` +
      bold dateline + bullets / `-` bullets) still matches the base file.
- [ ] Output file names follow the `_adapted.md` convention and the
      originals were not modified.

# Instructions — Adapting the resume Markdown to a specific job posting

These are the rules an AI agent must follow when adapting
`curriculo_base_PT.md` / `curriculo_base_EN.md` (or their `_adapted`
versions) to a specific job description. The goal is to maximize relevance
and ATS keyword match for that job **without ever inventing or
misrepresenting anything** about the candidate.

This file is meant to be given to an AI agent together with: the current
resume Markdown file(s) and the job posting text. See the README section
"How to adapt your Markdown for a specific job" for the exact prompt to use.

## Hard rules (never break these)

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
     → "machine learning" is fine; turning a LiDAR-processing bullet into a
     claim about a technology never mentioned in the base file is not).
   - Condense less relevant bullets/entries to save space for more relevant
     ones. Prefer condensing over deleting entirely.
   - Fully rewrite the Objective/Summary and Cover Letter sections to speak
     directly to the job posting — these are self-presentation, not factual
     claims, as long as they stay consistent with the real background in the
     Experience/Education sections.
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

## Structural rules (required for `gerar_pdf.py` to keep working)

The output must remain parseable by `gerar_pdf.py` — see `CLAUDE.md` for the
full parser details. In short:

- Exactly one `# Name` line (H1), unchanged.
- One loose line right below the name (subtitle/target role) — this MAY be
  rewritten to better match the job title, since it's self-description, not
  a factual claim.
- The **first** `##` section of the file must remain the contact block:
  only `- Label: value` bullet lines, nothing else added there.
- Every other `##` section stays a normal section. You may reorder which
  `##` sections appear, but do not rename them into something the script
  wouldn't recognize as a section (they don't need special names — any `##`
  works — just keep them as `##` headings).
- Inside a section, an entry is `### Job title/Degree` followed by a line
  `**Company/Institution** | Period`, followed by `-` bullets. Keep this
  exact 3-part shape for every entry (heading line, bold company/period
  line, bullets).
- Bullets always start with `-` (not `*`, not `•`).
- No tables, no images, no multi-column tricks, no raw HTML.

## Keyword-matching guidance (for ATS relevance)

1. Extract the key requirements, technologies, tools, and role-specific
   terms from the job posting.
2. For each one that the candidate's base file already demonstrates
   (anywhere — experience, education, or skills), make sure the exact
   wording/acronym used in the job posting also appears in the adapted file
   (e.g. if the base file says "aprendizado de máquina" and the job posting
   says "Machine Learning", make sure "Machine Learning"/"aprendizado de
   máquina" — matching the file's language — is explicitly present, not just
   a synonym).
3. Do not keyword-stuff: do not repeat a term many times or list irrelevant
   tools just because the job posting mentions them. Every keyword you add
   must correspond to something real in the base file.
4. Prioritize: put the most relevant experience entry first if reordering
   sections is reasonable, and put the most relevant bullets first within
   each entry.

## Output

- Never overwrite the base files (`curriculo_base_PT.md`,
  `curriculo_base_EN.md`).
- Write the result to `<original filename without extension>_adapted.md`,
  e.g. `curriculo_base_PT_adapted.md` and `curriculo_base_EN_adapted.md`.
- If `_adapted.md` files already exist from a previous job application,
  overwrite them (they represent "the current tailored version", not a
  history).

## Self-check before finishing

Before returning the adapted files, verify:

- [ ] No new employer/school/degree/certification/date was invented.
- [ ] No date, company name, or institution name was changed.
- [ ] Every fact-bearing claim in the adapted bullets is traceable to
      something in the base file.
- [ ] The PT and EN adapted files describe the same set of facts.
- [ ] The structural shape (H1 / contact section / `##` sections / `###` +
      bold dateline + bullets / `-` bullets) still matches the base file.
- [ ] Output file names follow the `_adapted.md` convention and the
      originals were not modified.

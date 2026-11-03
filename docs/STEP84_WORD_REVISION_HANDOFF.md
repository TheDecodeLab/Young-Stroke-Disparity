# Step84: Local Word revision handoff

**Status (2026-10-25):** Source-based v1.6 **text-only** redlined manuscript and supplement were built and visually checked in the private conversation artifact workflow. The unmodified v1.5 Word sources were preserved. A standalone `step84_build_redlined_docx.py` builder plus four fabricated-data tests was delivered to the investigator as a conversation file/ZIP, **not committed to this public repository**. The two source Word documents and the restricted Step83 candidate JSON were **not** uploaded to GitHub.

The review package includes:
- Granular Word tracked insertions/deletions for Methods and Supplementary Methods, clarifying that Step82/83 patient-level selection starts at **retained, date-valid I63-coded inpatient encounter keys**, not a full-export prelinkage STROBE flow.
- A birth-year age-band explanation that keeps boundary-spanning categories separate.
- Local punctuation/clarity corrections, without changing any numerically reported outcome.
- Preservation of five active Zotero citation fields and one bibliography field in the original manuscript. The supplement contains no existing Zotero fields.
- A local **restricted** mode that reads only the already prepared Step83 reporting-candidate aggregate JSON and inserts Supplementary **Table S9** (mutually exclusive patient flow) and **Table S10** (baseline characteristics). Source-P-specific sex distributions remain withheld as prescribed by Step83. The previous limitations heading becomes S11.
- Actual-data DOCX generation occurs **only on the authorized investigator workstation**, using the original v1.5 DOCX files and the restricted Step83 JSON. A synthetic table build validated layout and table pagination. The v1.6 text-review copies do not include invented or placeholder source-derived table numbers.

**Validation done in the artifact environment:** four synthetic unit tests passed, tracked-change structure was inspected, the original Zotero field counts were unchanged, both text-only files rendered to page images, a synthetic complete supplement rendered across eight pages with a repeated Table S10 header, and the accepted-text QA copies passed the zero-running-prose-semicolon audit. **Workstation tests of the full private Step83 integration remain pending.**

This manuscript may undergo further internal editing under the investigator's **already approved** TriNetX Research Network access application. Do not require a duplicate data-access request or contact CTSI by default. External release must follow the approved application's actual dissemination conditions, including any required cumulative/complementary disclosure review.

**Open author checks before submission:** exact Research Network export/download date, specific publication/dissemination conditions of the approved application, final ethics and data-availability text, completeness of the whole manuscript's Zotero field linking, and target-journal specifications.

The supplied standalone builder refuses unexpected Step83 policies, changed cohort totals, unsafe source-P sex display, inconsistent patient-flow or demographic partitions, and overwriting existing outputs. The builder does not read the source ZIP, patient IDs, or checkpoint SQLite database.

The original Word sources and their new locally generated results should remain in approved private storage. Do not commit the v1.6 Word files or restricted table outputs.

# Step84: Submission disclosure and reporting gate (counts-free checklist)

**Status (2026-10-25):** Investigator reconfirmed an **existing approved application for access to this Research Network dataset for this study**. Do not request duplicate access approval or send the superseded CTSI inquiry. The precise external-publication and aggregate-output conditions in that approved application have not been inspected here. This counts-free checklist is for internal manuscript preparation and compliance with the existing authorization, not an assertion that another institutional application is mandatory.

## Confirmed Step83 workstation result

- Step83 targeted tests: **9 passed**.
- Entire repository suite: **795 passed**, three established nonblocking warnings.
- Step83 completed using only the previously frozen, local Step82 restricted aggregate JSON.
- Independently verified one Step82 flagged small-cell/complement condition.
- Sex display policy: **overall_only**, so no source-P-specific sex counts or proportions appear in Step83's candidate.
- Patient selection display policy: **three_groups**. Displayed patient groups are mutually exclusive and reconcile to the retained-indexed cohort.
- All displayed category and denominator totals reconcile with Step82.
- The outputs remain local at `results/phase1/full_reconstruction_private/step83_reporting_candidate_private/`. They have **not** been cleared for external sharing, journal use, or GitHub.

These checks assess numerical consistency and one conservative suppression design. They **do not** demonstrate cumulative disclosure safety for the entire proposed publication.

## Release scope to review together

When the already approved application's terms require aggregate disclosure review, submit one frozen **complete candidate publication package** through its specified process rather than submitting isolated tables. Even if no separate review is required, examine cumulative/complementary disclosure across the complete intended package. Include, as applicable:

1. The current Young Stroke manuscript and supplement (working version v1.5), including every abstract number, Results sentence, table and footnote.
2. Both main figures and their captions, and any figure panels or plotted point labels.
3. The Step83 baseline characteristics candidate and the limited patient-flow table.
4. Any retained modality, P-stratified, demographic, or sensitivity table in the manuscript or supplement, including the previously withheld Step78 Table4 if authors propose restoring it.
5. Cumulative interactions between totals, overlapping outcomes, sex/race/ethnicity strata, source-P flags, calendar-year categories and the three-group selection flow, plus comparisons with previously disclosed outputs from the same study.

**Never assume** that a threshold of 11 guarantees release safety. Check both positive and complementary cells and whether suppressed counts can be derived from visible margins, percentages or adjacent figures. Any new publication-table revision requires a new cumulative check.

Do not move Step83 tables, Step82 JSON, patient-level SQLite, or source ZIPs into this public repository, public files, or an external email. Handle any restricted candidate outputs under the terms of the **existing approved application** and an authorized private channel if further review is required.

## Methodological reporting still required

- **STROBE 13 / RECORD 13.1:** Explain that the three-group patient flow begins with **retained date-valid I63/IMP encounter keys** after upstream diagnosis-to-encounter matching. It is not the full export-to-final-cohort selection flow. The source-wide initial unique-patient count and every upstream exclusion are not recoverable from the frozen Step82 summary. Do not invent them.
- **STROBE 14:** Show only release-cleared baseline categories and explicit unknown/unmapped distributions. Source-mapped race and ethnicity categories are not confirmed clinical identities.
- **RECORD 6.1, 7.1:** Describe the frozen ICD-10-CM I63 eligibility, year-of-birth uncertainty, index-selection rules, source P flag and CPT14 imaging-code algorithms precisely.
- The primary endpoint measures **recorded CPT code presence** under encounter attribution rules. It does not establish a completed imaging examination or inequity in care. Other same-day encounters were not proven to represent the same institution or stroke episode.
- Retain the lack of HCO-level clustering, chart/PACS validation, and adjusted causal interpretation among key limitations.

Reporting guidelines: [STROBE](https://www.strobe-statement.org/) and [RECORD](https://pmc.ncbi.nlm.nih.gov/articles/PMC4595218/).

## TriNetX and institutional conditions (not verified for this specific export)

Current official [TriNetX publication guidance](https://trinetx.com/publication/trinetx-publication-guidelines/) requests the specific network name and data analysis/download date in Methods and recommends relevant source-size and HCO-count context when available. It cautions that HCO agreements may limit publication even when use for research is permitted. Publications generally must not display HCO-specific data or platform screenshots without applicable permissions. TriNetX also requires disclosure and an order form for third-party-funded uses under its published guidelines. **Check the existing approved application's publication and output conditions first.** Seek clarification from an authorized representative only if the agreement does not resolve a material question. Do not require another general access application.

Record what the existing approved application and export provenance actually establish, and do not infer:

- The actual Research Network dataset extraction/download date from export or job records, distinct from the index-admission year range.
- Any permissible network-size / HCO-count description applicable to that export, without naming HCOs or publishing site-specific results.
- The applicable terms of the **already approved access application**, any linked protocol/IRB or institutional determination, and whether it specifies restrictions on external aggregate publication or third-party-funded use. Do not characterize these as missing approvals without reviewing the existing records.
- Privacy review of any previously identified source-derived files in the public GitHub history, independent of this Step83 table check.
- The final journal and its manuscript, disclosure, reporting checklist, figure and data-availability requirements.

Do not copy generic TriNetX IRB exemption wording as an institutional approval statement without confirming the actual study determination.

## Handoff

1. Preserve the original restricted Step82 and Step83 artifacts locally; **do not rerun them**.
2. Assemble one immutable, locally stored candidate publication collection and its version manifest. Leave the full private tables under the already approved storage location.
3. Check the existing approved agreement for dissemination terms and any required aggregate-output review. Assess cross-table derivability across the whole candidate publication. Initiate **only a review expressly required by the existing terms**, or a focused clarification for a genuine unresolved issue. No email has been sent.
4. Proceed now with **restricted internal** DOCX manuscript/supplement revisions, using granular tracked changes and intact Zotero citation fields. Incorporate the local Step83 tables only into an appropriately restricted local working copy. Before external release, meet the existing agreement's actual dissemination and disclosure requirements.
5. Complete the final STROBE/RECORD checklist and target-journal submission package. Submission readiness depends on scientific review and compliance with the **existing approved terms**, not an invented new application gate.

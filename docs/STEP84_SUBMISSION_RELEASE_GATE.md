# Step84: Submission disclosure and reporting gate (counts-free checklist)

**Status (2026-10-25):** Prepared for investigator and institutional review. No release or publication authorization obtained. This document contains no TriNetX source-derived table cells.

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

The authorized data steward or disclosure reviewer should evaluate one frozen **complete candidate publication package** rather than isolated tables. Include, as applicable:

1. The current Young Stroke manuscript and supplement (working version v1.5), including every abstract number, Results sentence, table and footnote.
2. Both main figures and their captions, and any figure panels or plotted point labels.
3. The Step83 baseline characteristics candidate and the limited patient-flow table.
4. Any retained modality, P-stratified, demographic, or sensitivity table in the manuscript or supplement, including the previously withheld Step78 Table4 if authors propose restoring it.
5. Cumulative interactions between totals, overlapping outcomes, sex/race/ethnicity strata, source-P flags, calendar-year categories and the three-group selection flow, plus comparisons with previously disclosed outputs from the same study.

**Never assume** that a threshold of 11 guarantees release safety. Check both positive and complementary cells and whether suppressed counts can be derived from visible margins, percentages or adjacent figures. Any new publication-table revision requires a new cumulative check.

Do not move Step83 tables, Step82 JSON, patient-level SQLite, or source ZIPs into this public repository, public files, or an external email. Use only the institutional approved private review channel for the candidate outputs.

## Methodological reporting still required

- **STROBE 13 / RECORD 13.1:** Explain that the three-group patient flow begins with **retained date-valid I63/IMP encounter keys** after upstream diagnosis-to-encounter matching. It is not the full export-to-final-cohort selection flow. The source-wide initial unique-patient count and every upstream exclusion are not recoverable from the frozen Step82 summary. Do not invent them.
- **STROBE 14:** Show only release-cleared baseline categories and explicit unknown/unmapped distributions. Source-mapped race and ethnicity categories are not confirmed clinical identities.
- **RECORD 6.1, 7.1:** Describe the frozen ICD-10-CM I63 eligibility, year-of-birth uncertainty, index-selection rules, source P flag and CPT14 imaging-code algorithms precisely.
- The primary endpoint measures **recorded CPT code presence** under encounter attribution rules. It does not establish a completed imaging examination or inequity in care. Other same-day encounters were not proven to represent the same institution or stroke episode.
- Retain the lack of HCO-level clustering, chart/PACS validation, and adjusted causal interpretation among key limitations.

Reporting guidelines: [STROBE](https://www.strobe-statement.org/) and [RECORD](https://pmc.ncbi.nlm.nih.gov/articles/PMC4595218/).

## TriNetX and institutional conditions (not verified for this specific export)

Current official [TriNetX publication guidance](https://trinetx.com/publication/trinetx-publication-guidelines/) requests the specific network name and data analysis/download date in Methods and recommends relevant source-size and HCO-count context when available. It cautions that HCO agreements may limit publication even when use for research is permitted. Publications generally must not display HCO-specific data or platform screenshots without applicable permissions. TriNetX also requires disclosure and an order form for third-party-funded uses under its published guidelines. **Confirm applicability through the authorized institutional/TriNetX representative before submission.**

The investigator must confirm, not infer:

- The actual Research Network dataset extraction/download date from export or job records, distinct from the index-admission year range.
- Any permissible network-size / HCO-count description applicable to that export, without naming HCOs or publishing site-specific results.
- The relevant current protocol/IRB or institutional human-subjects determination, data-use and output-release permissions, and whether the work counts as third-party-funded TriNetX use.
- Privacy review of any previously identified source-derived files in the public GitHub history, independent of this Step83 table check.
- The final journal and its manuscript, disclosure, reporting checklist, figure and data-availability requirements.

Do not copy generic TriNetX IRB exemption wording as an institutional approval statement without confirming the actual study determination.

## Handoff

1. Preserve the original restricted Step82 and Step83 artifacts locally; **do not rerun them**.
2. Assemble one immutable, locally stored candidate publication collection and its version manifest. Leave the full private tables under the already approved storage location.
3. Seek institutional/TriNetX data-owner review of the **whole proposed release**, including cross-table derivability and publication permission. No office has been contacted and no request has been sent by this step.
4. Once the required clearance is documented, incorporate approved tables and bounded cohort-flow language into the current DOCX manuscript/supplement with granular tracked changes and intact Zotero citation fields.
5. Complete final STROBE/RECORD checklist and target-journal submission package. Do not label the article submission-ready until the data-owner and scientific review gates are closed.

# Step82: Patient-level cohort flow and baseline reporting from frozen checkpoints

**Status:** Prepared, nine fabricated-data tests passed in isolated local testing. Investigator workstation execution and full repository suite are **not yet verified**. No source-derived cohort-flow or baseline numbers have been released or inserted into the manuscript.

## Purpose

Complete two missing observational reporting components for the Research Network study of encounter-dependent neuroimaging CPT-code ascertainment:

1. A patient-level selection flow ending in the frozen 64,721-person definite-age 18-50 cohort.
2. A descriptive baseline table showing mapped sex, race, ethnicity, defensible birth-year-derived age bands, index calendar year, and the P=0/P=1 source principal-I63 flag.

The present manuscript's Table 1 describes coded imaging capture, not baseline characteristics. The report from this step could support a **new supplementary cohort-selection table and baseline Table S9**, or a main-text reorganization once the journal has been chosen. Do not add placeholders or unverified numbers to the Word manuscript.

## What the script uses

`scripts/step82_submission_reporting.py` reads only the existing Step62 private SQLite checkpoint and its frozen aggregate report:

`results/phase1/full_reconstruction_private/step62_cohort_private/`

It never opens the ~993-million-row `procedure.csv` source, other source ZIP tables, or patient-level files outside that SQLite checkpoint. It never publishes raw patient/encounter identifiers or raw demographic source labels. It imports the **existing Step62 age-eligibility rule** and **Step71 conservative demographic category mapping**, so reported groups remain consistent with previous analysis.

This is intentionally *not* a full-export STROBE flow. Its starting point is the retained, date-valid I63-coded qualifying inpatient encounter keys, after diagnosis/encounter joins and exclusion of conflicting keys. The earlier pipeline does not retain patient-level disposition for all invalid, unmatched, or rejected source rows. We must disclose this limited starting point, not claim to have traced every source diagnosis.

## Scientific safeguards

- **Two denominator types remain separate.** The existing age audit counts candidate *admissions*, not excluded unique patients. The new flow partitions unique people into mutually exclusive statuses: included index, held same-day competing indexes, and no definite-age-eligible candidate due to missing birth year, missing sex where relevant, uncertain age boundary, or age outside the cohort range. Missingness categories are assigned by explicit priority if multiple ineligible candidate admissions occur for one person.
- The 64 quarantined conflicting qualifying IMP keys in the historical Step62 report are an **encounter-key QA count**, not automatically 64 excluded patients. The script preserves that count separately from the patient flow.
- A person may have an age-uncertain admission before the selected definitely eligible index. The flow prioritizes **any definitely eligible admission**, consistent with the frozen index algorithm; it does not infer that the selected index is the person's first-ever stroke.
- Index age is available as **year of birth only**. Report age bands only if both possible integer ages fall inside the same band; report a separate boundary-spanning band otherwise. These are not validated exact clinical ages.
- P is an **unvalidated principal I63 source-recording flag**, not a hospital or stroke-severity category. P=0 includes unmarked and secondary I63-coded records.
- Unknown and other/unmapped race or ethnicity remain different rows. Neither proves clinical demographic missingness.
- Internal counts are not approved for publication. Small events/complements are flagged for *preliminary* review. An institutionally authorized reviewer must assess **all displayed tables and figures together** for cumulative or complementary disclosure, not only each individual cell.

The script fails closed on a missing/incomplete Step62 checkpoint; mismatched selection, age-audit, baseline, or frozen report counts; unmapped output category identifiers; and attempted overwrite of the private results file.

## Exact workstation command

From the repository root, after the new code is available on `analysis-rebuild-phase1-audit`:

```bash
(
  set -e
  git pull --ff-only origin analysis-rebuild-phase1-audit
  python -m py_compile scripts/step82_submission_reporting.py
  python -m pytest -q tests/test_step82_submission_reporting.py
  python -m pytest -q
  python scripts/step82_submission_reporting.py \
    --acknowledge I_CONFIRM_INTERNAL_REVIEW_ONLY
)
```

The default private output is:

`results/phase1/full_reconstruction_private/step82_submission_reporting_private/cohort_flow_baseline_INTERNAL_ONLY.json`

The file is owner-only and **must not be committed, emailed, or uploaded** without the applicable output permissions. The terminal summary contains the indexed cohort size, P strata, reconciliation flags, and number of small-cell alerts. It does not print the detailed flow or baseline tables. Inspect those locally for scientific QC and seek disclosure review before using them outside the approved environment. The script refuses an existing output file instead of silently overwriting it.

## What this does not solve

- It cannot establish the total number of all candidate patients before valid diagnosis/encounter matching. A complete source-level flow would need preserved upstream counters or an additional approved source audit, not invented subtraction.
- It cannot determine the actual dataset extraction/download date from clinical encounter dates or an undated export name. Record the date from the TriNetX export/job metadata or obtain it from the data custodian.
- It does not establish the network's contemporaneous participating-HCO count or that network-wide statistics can be disclosed. The source is TriNetX **Research Network** (not the old Diamond export), but network size and release conditions require separate verification.
- It does not supply IRB/exemption determination, data-sharing permission, journal-specific formatting, or a completed STROBE/RECORD checklist.
- It does not provide actual imaging-examination validation or HCO-clustered inference. The paper remains a measurement-sensitivity analysis.

## Next decision after the workstation run

First check whether all patient and demographic partitions reconcile with Step62. Then obtain approval for the specific set of proposed tables. Once these outputs can be used for manuscript drafting, insert a cohort-selection summary and baseline table into the v1.5 Word files while preserving Zotero citation fields and using granular tracked changes. Finally confirm the TriNetX extraction date, ethics/data permissions, and the selected journal's reporting package.

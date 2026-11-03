# Step 60: Private interpretation of existing Step59 aggregate reports

**Workstation status (2026-10-18, investigator confirmed):** Step58 succeeded, and Step59's **encounter, diagnosis and procedure** stages each completed successfully. Their private derived reports exist only on the Penn State workstation. Their contents have **not** been shared or inspected in ChatGPT or GitHub.

Step60 is a **local-only read of the three pre-existing private Step59 JSON reports**. It does **not** read the original source ZIP, touch patient-level records, repeat any large-table scan, reconstruct index admissions, generate statistical comparisons, verify HCO/site identity, or grant approval to publish.

## What Step60 assesses

The [Python implementation](../scripts/step60_local_aggregate_review.py) checks each Step59 report's provenance and completion flags; reconciles total rows to per-year buckets and to each required label grouping; and checks that CPT14/70471/perfusion code-row counts are not larger than all CPT procedure rows in the same year. If an inconsistency exists, it **stops without writing a result**.

A private combined report organizes **source rows** by observed calendar year for each table, along with fixed groupings for `IMP`/`EMER` encounter labels, diagnosis principal `P` labels, procedure code systems, missing/invalid dates and CPT14/70471/perfusion code-row groupings. Its diagnostic flags draw attention to non-CPT procedure rows, missing/invalid dates, 70471's 2026 change and year-presence differences among source tables.

**These categories have different denominators.** They are not unique patients, hospitalizations, stroke episodes, imaging exams or validated completed studies. `CPT14_CODE_ROWS_NOT_EXAMS` is explicitly a raw row count. **Do not divide code rows by encounter rows and call the result imaging utilization.**

## What Step60 cannot establish

- **Final Research Network period**: the last calendar year with rows is **not necessarily the last complete year**. HCO/site participation and year-end capture are still unknown. Even a smooth time series is not sufficient to choose the manuscript's year endpoint. Proposed start remains 2016; Diamond alone retains 2018–2019.
- **Imaging capture completeness**: non-CPT recorded procedure rows are a *warning about heterogeneity*, not proof of missing imaging. The 14 CPT core and 2026 changes have official code-meaning references, but this does not establish performed vs ordered procedures.
- **Encounter linkage**: a valid `IMP` label/ID does not validate its inpatient meaning or give a hospital/episode key. The study's A same-index-IMP primary remains the design; B provisional ED-inclusive date-only remains a sensitivity, not a verified same-hospital transfer.
- **Clinical outcomes or disparities**: no patient cohort, codebook approval, sex/race analysis, adjusted model, or manuscript results are produced.

## Run once, locally

First, pull the public branch and validate the **new synthetic tests**. The previous workstation run was **581 passed, 3 existing nonblocking warnings**; Step60 adds new tests, so do not assume the count until they run.

```bash
git pull --ff-only origin analysis-rebuild-phase1-audit
python -m py_compile scripts/step60_local_aggregate_review.py
python -m pytest -q
```

If all tests pass, run:

```bash
python scripts/step60_local_aggregate_review.py \
  --acknowledge I_CONFIRM_LOCAL_PRIVATE_AGGREGATE_REVIEW
```

The script reads exactly these **private local files** (no further source ZIP access):

- `results/phase1/full_reconstruction_private/source_wide_qa/step59_encounter_LOCAL_ONLY.json`
- `results/phase1/full_reconstruction_private/source_wide_qa/step59_diagnosis_LOCAL_ONLY.json`
- `results/phase1/full_reconstruction_private/source_wide_qa/step59_procedure_LOCAL_ONLY.json`

It creates exactly one mode-0600, no-overwrite report:

`results/phase1/full_reconstruction_private/source_wide_qa/step60_local_aggregate_review_LOCAL_ONLY.json`

**Keep the Step59 and Step60 JSON reports on the approved Penn State workstation. Do not paste, upload, email, or commit clinical-derived aggregate data to GitHub/ChatGPT without the required disclosure review.** Share only the completion status or a reviewed non-identifying exception message.

## How to review Step60's conclusions locally

Check the `automated_review_flags_NOT_CLINICAL_SIGNOFF` and `private_year_by_table_NOT_SITE_ADJUSTED` sections locally. Identify which years appear in all three tables and whether their source-row counts show abrupt shifts, which coding systems the actual procedure table uses, whether `IMP`/`EMER` rows are present, and whether the late-period 70471 candidate occurs. Keep interpretations provisional. Quantify patient-based imaging ascertainment only after an approved clinical phenotype builder and code-system adjudication are implemented.

**Do not finalize any calendar cutoff or mark source coverage as acceptable automatically.** The combined file explicitly sets `final_study_end_year: null`, leaves Step45 disabled and requires separate source/HCO coverage, procedure-event meaning and demographic missingness review.

The resulting review can guide whether the **next computational work** should prioritize (a) patient and encounter-identifier integrity, (b) version-aware non-CPT imaging mapping or (c) site/period coverage documentation, without repeating previous whole-table QA passes.

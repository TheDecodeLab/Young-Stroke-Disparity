# Corrected Research Network date parsing (Step59/60 DATEFIX_V2)

**Investigator's direct finding (2026-10-18):** In bounded local prefixes
of encounter, diagnosis and procedure source tables, date values all have
the **eight-digit shape** `99999999`. The old Step59 code accepted only
hyphenated `YYYY-MM-DD`, so its three full-table reports incorrectly
bucketed **all rows as INVALID**. Consequently original Step60 showed
`calendar_years_present_NOT_APPROVED: []` and Step61's annual disclosure
candidate was also empty. This is **our parser bug, not evidence that the
Research Network has no usable calendar years**.

The new Step59 parser accepts (a) validated `YYYYMMDD` calendar dates and
(b) previously supported ISO `YYYY-MM-DD[...]`. It validates real months,
days and leap years. **The eight-digit pattern alone does not prove
YYYYMMDD ordering**; the bounded date probes below must be reviewed before
another expensive scan. If a probe produces primarily INVALID dates,
STOP and investigate the source's date schema.

**Existing full-source aggregate totals and overall CPT/non-CPT procedure
counts did not depend on valid dates**; they may remain useful as global
record-row counts, not year-specific data-quality evidence.

## Do this in order (no raw clinical dates leave the workstation)

1. Pull and run full synthetic suite. The last workstation-confirmed full suite was **599 passed**. Step61
   added 11 synthetic tests verified locally, and this date-fix adds 23
   test cases. The expected current full test count is **633**, pending
   your workstation run. Require zero failing tests and valid Python syntax:

```bash
git pull --ff-only origin analysis-rebuild-phase1-audit
python -m py_compile scripts/step59_full_source_aggregate_qa.py scripts/step60_local_aggregate_review.py
python -m pytest -q
```

2. Probe **at most 1,000 local source rows** from each table. The output is
   a small count by parser-success/invalid/missing/boundary category only,
   with no original source dates, patient or encounter values:

```bash
for stage in encounter diagnosis procedure; do
  python scripts/step59_full_source_aggregate_qa.py \
    --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip" \
    --stage "$stage" \
    --probe-dates \
    --acknowledge I_CONFIRM_EXISTING_PROTOCOL_PERMITS_LOCAL_FULL_SOURCE_AGGREGATE_QA
done
```

3. **Only if the probes validate YYYYMMDD**, re-run **one table at a time**
   with a versioned file destination (do not start all together):

```bash
python scripts/step59_full_source_aggregate_qa.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip" \
  --stage encounter \
  --datefix-v2 \
  --acknowledge I_CONFIRM_EXISTING_PROTOCOL_PERMITS_LOCAL_FULL_SOURCE_AGGREGATE_QA
```

Then repeat with `--stage diagnosis` and later `--stage procedure`.
Each stage again requires a **full sequential pass** (up to billions of
source rows). A pass may take hours/days and cannot resume after interruption.
No source clinical records are uploaded, printed, or saved outside the
approved local environment.

These commands create **new** files:

- `step59_encounter_DATEFIX_V2_LOCAL_ONLY.json`
- `step59_diagnosis_DATEFIX_V2_LOCAL_ONLY.json`
- `step59_procedure_DATEFIX_V2_LOCAL_ONLY.json`

All reside in the existing ignored private
`results/phase1/full_reconstruction_private/source_wide_qa/`
directory with no overwrite. Old Step59 reports remain as audit records and
**must not be interpreted by year**.

4. **After all three corrected full passes succeed**, reconcile only the
new versioned reports with the revised Step60:

```bash
python scripts/step60_local_aggregate_review.py \
  --datefix-v2 \
  --acknowledge I_CONFIRM_LOCAL_PRIVATE_AGGREGATE_REVIEW
```

Output: `step60_local_aggregate_review_DATEFIX_V2_LOCAL_ONLY.json`.
The reviewer refuses to mix old and new date-parser reports and requires
each corrected table to show at least one parseable calendar year.

The updated Step60 report may be reviewed as an aggregate QA artifact under
the existing research sharing terms. **Year presence is not year completeness,
hospital/HCO participation, stroke cohort validation, imaging completion
or final protocol year-signoff**. Clinical cohort reconstruction in obsolete
Step45 remains hard disabled. Draft PR #1 remains unmerged pending the
separate repository-history governance question.

**Do not repeat the old Step61 coarse export.** Its empty result was a
consequence of the date-parser bug. Interpret the corrected Step60 source-row
aggregates directly once available.

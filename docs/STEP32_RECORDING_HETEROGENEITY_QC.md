# Step 32: local read-only recording-pattern audit

**Status:** Proposed internal data-quality analysis. Not a clinical
disparities test, utilization estimate or permission to release results.

## Why this is the next step

The study-team Step 31 aggregate output confirmed **all
reconciliation checks passed**. With the denominator fixed at
86,902 people, the 14-CPT expansion found only 175 additional people
with any matched code at +/-1 day (0.201 percentage points). Even with
the expanded definition, 46,953 (54.03%) had no matching included
code at +/-1 day, and 44,602 (51.32%) at +/-7 days.

The next scientific question is not whether these people *received*
imaging; the source cannot resolve that. We can instead examine if
the recorded-code pattern and extent of missing matching codes vary
across broad patient groups in the source.

## What the program reads

The Step 32 script reuses the existing **complete PRIVATE local SQLite**
files:

- Demographic cohort:
  demographics/step19_age_cohort.sqlite
  (table eligible: patient_id, index_date, sex, age)
- Code-specific procedure table:
  imaging_expanded/step28_imaging_events.sqlite
  (table event: patient_id, modality, code_system, code,
  procedure_date, offset_days)
- The versioned 14-CPT evidence-reviewed codebook.
- The local aggregate step30_literature_imaging_audit.json for
  source, count, codebook and window reconciliation.

The script reads both SQLite DBs **read-only**. It checks stage
completion, cohort age limits 19-50, original ZIP fingerprint
recorded in the private directory, reviewed codebook checksum,
unique events and valid date offsets. It recomputes head-only
and head+neck patient matches across same-day, +/-1, +/-3 and
+/-7 days and **must exactly reconcile with the completed Step 30
report** before returning any subgroup counts.

**It does NOT open or scan original ZIP members.** No billion-row
reprocessing. IDs are used in private process memory only and never
written into aggregate JSON.

## Stratification

- Recorded sex: Female/Male as represented in the source cohort.
- Index calendar year: 2018/2019.
- Approximate age: 19-29, 30-39, 40-50.

Each dimension is tabulated separately (no sex-by-year-by-age
intersection) against the same imaging-independent denominator,
for both head-only and head/neck included-code recording.

These are descriptive **recording heterogeneity / data-quality
checks**, not adjusted associations, treatment disparities, or
hospital utilization rates.

## Privacy safeguards

- Any nonzero count below 11 suppresses the **entire dimension**.
- If a nonzero difference between adjacent time windows or nested
  head/neck definitions is below 11, the **entire dimension** is
  withheld, rather than leaving reconstructable complements.
- No patient-level records, diagnosis IDs or provider IDs appear
  in the JSON.
- Different marginal tables and previously generated reports can
  STILL permit complementary reconstruction. The report is marked
  publication_disclosure_review_required=true. Keep it in
  authorized local research storage until an institutional
  disclosure assessment confirms it can be shared.

The report explicitly sets clinical_inference_allowed=false and
race_ethnicity_inference_allowed=false. No p-values or regressions.

## Run locally without touching the original ZIP

From the same Git branch and workstation:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q && \
python scripts/step32_recording_heterogeneity_qc.py \
  --private-dir ../../../../datasets/TriNetX/young_stroke_private/chained_v1 \
  --compare-expanded results/phase1/step30_literature_imaging_audit.json \
  --output results/phase1/step32_recording_heterogeneity_qc.json
```

The script is new, and its tests require execution on the study-team
workstation. Do not share unreviewed counts. Please share only a
disclosure-reviewed aggregate report, or the traceback if a run fails;
do not upload the SQLite or original data.

## What would change the publication decision?

A systematic variation in *recorded codes* across years or demographic
groups would demonstrate potential **measurement heterogeneity**, not
differences in actual imaging access. A lack of variation would NOT
prove complete imaging capture. The already high unknown race and
ethnicity rates severely restrict meaningful social-disparity
conclusions.

The stronger candidate remains an observational **methods/data-quality**
paper analyzing selection on MRI/CTA/MRA codes, imaging-code definitions,
temporal-window sensitivity and demographic missingness. Avoid asserting
a biased original effect *size* until age criteria and denominators
are genuinely comparable and reanalysis supports that comparison.

**PR remains draft and scientific inference stays blocked.**

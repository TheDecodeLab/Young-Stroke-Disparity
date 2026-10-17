# Step 12 findings: stop exploratory re-analysis and locate source exports

The aggregate `index_definition_audit.json` confirms the clinical index
may change depending on whether imaging precedes diagnosis selection.

## Quantitative audit (all ages; imaging-linked source only)

- 385,823 people have at least one imaging-linked principal ischemic
  diagnosis in the pre-exclusion intermediate.
- 300,495 have CT linked to at least one such diagnosis.
- 208,867 have CT and MRI/CTA/MRA somewhere in the linked records.
- Within those 208,867, the first CT-linked and first advanced-linked
  diagnosis dates disagree in 9,584 (4.59%) patients.
- The first advanced-linked date occurs later in 5,279, earlier in
  4,305, and falls in another calendar year in 2,435.
- At the first CT-linked diagnosis, 98,781 have no MRI/CTA/MRA linked.
  Across all linked dates, 91,628 CT patients never have additional
  imaging. These are different questions and denominators.

The above are **not young-stroke population estimates**. The input has
already been selected for imaging-linked diagnoses, may omit earlier
strokes without linked imaging, and lacks validated encounter IDs.
The original notebook also removed ambiguous procedure-to-diagnosis
matches before saving the intermediate. We cannot recover lost rows.

## What this means for the manuscript

The apparent agreement of the CT-retaining table with the earliest
imaging-linked record does not validate it as the first hospitalized
stroke. The old denominator omitted CT-only cases and shifted index
dates for some patients. Do NOT reuse old or preliminary regression
coefficients as estimates for the intended stroke population.

## Step 13: original-source readiness

The next milestone is locating approved original exports. The
historical notebook refers to `tabs[5]` for diagnosis events,
`tabs[14]` for procedure events, and `tabs[12]` for demographics,
but the definitions of those file paths are not present in the code
we inspected.

Use `scripts/step13_source_inventory.py` on the original files,
**not** on `df_merged_age.parquet` or any derived patient cohort.

Example using placeholders (replace paths with actual local exports):

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step13_source_inventory.py \
  --diagnoses /secure/local/path/diagnoses.parquet \
  --procedures /secure/local/path/procedures.parquet \
  --demographics /secure/local/path/demographics.parquet
```

The source arguments may be individual Parquet files, directories of
Parquet fragments, or CSV files. You can supply one source at a time
if others are not yet located.

Large Parquet inputs with more than 5 million rows are inspected in
**metadata-only** mode by default. Increase `--max-rows` cautiously
on a machine with enough memory; unique-patient counts are accumulated
in memory. CSV inputs stream in chunks.

Output: `results/phase1/source_readiness.json`, an ignored aggregate
and schema-only report. It contains field names and aggregate counts,
not patient identifiers, actual dates or individual records.

The audit checks the necessary fields, encounter/visit identifier
candidates, dates and provisional 2018-19 principal I63 diagnoses.
It also tabulates candidate brain CT, CTA head/neck, brain MRI and
MRA head/neck codes. It **does not** establish that these codes are
clinically complete or that a qualifying diagnosis is a true
hospitalization. We must approve code lists and encounter definitions
with the study team before a formal reconstruction.

**Next decision:** Once we know the actual source schemas and stable
event-linking keys, build the 2018-19 principal ischemic index cohort
*before* imaging selection; then link CT and non-CT imaging to the
selected encounter/time window, preserving eligible CT-only cases.
Reassess standard age cutoffs, risks, clinical severity and missingness.

## Privacy and governance

Use only authorized local clinical exports. The public repository
already includes an older patient-level dataset, which should undergo
institutional and TriNetX redistribution and Git history review.
Do not upload/push raw source tables, record excerpts, geo details,
or unsuppressed granular summaries.

# Step 9 findings and Step 10 reconciliation plan

## What the local Step 9 audit found

Input: aggregate-only `recovery_candidate_audit.json` from the study
team. No row-level patient records were transferred.

| File | Size | Key aggregate finding |
| --- | ---: | --- |
| `df_merged_age.parquet` | 1,025,641 imaging-diagnosis rows | 326,450 patients with a recorded CT, including 101,366 CT-only patients **across all observed dates** |
| `df_trinetx_total_young_wCT.parquet` | 52,893 unique patients | 40,188 CT-positive; 11,084 CT-only; 29,104 CT-positive with MRI/CTA/MRA |
| `df_trinetx_total.parquet` | 432,057 rows | Earlier named imaging columns; needs separate provenance review |
| `df_trinetx_total_young.parquet` | 30,619 unique patients | Zero patients with none of MRI, CTA and MRA |

**Critical reconciliation mismatch:** the original paper's young cohort has
30,619 patients, but the recovered `_wCT` candidate has only 29,104
patients who have CT **and** at least one MRI/CTA/MRA. Their difference
is 1,515 patients. They cannot simply be treated as the same extraction,
cohort rules, or index-event definition.

Within the `_wCT` candidate, 52,893 - 40,188 = **12,705 rows
without CT recorded**, despite its file name. They may have an advanced
modality, or there could be records with none. Step 10 explicitly
checks which explanation fits and how those patients overlap the legacy
cohort.

## Step 10: inspect overlap before reconstructing

```bash
git fetch origin
git switch analysis-rebuild-phase1-audit
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step10_reconcile_cohorts.py
```

The script reads the approved, locally stored files:

- `../df_trinetx_total_young_wCT.parquet` (candidate)
- `../df_trinetx_total_young.parquet` (original)

It validates unique patient IDs and nonnegative integer procedure counts,
then compares both files by patient ID **in memory**. It reports
aggregate-only overlap, missing members, mismatched MRI/CTA/MRA counts,
age, sex, diagnosis year and stroke type. It also reports broad counts
with original age restrictions versus common age <=45 and <=50.
No patient IDs, actual dates, or row-level observations are written.

Output: `results/phase1/cohort_reconciliation.json` (gitignored).
This is a diagnostic. Inspect the JSON before sharing it.

## Interpretation

A low number of mismatches among shared patients would suggest that
the candidate might be a useful upstream representation, but it still
does not establish correct stroke-admission linkage. A large number
of unmatched IDs or imaging-count mismatches suggests an extraction
version or construction-rule mismatch requiring further investigation.

Even an exact match does not prove that the patient has a specific
non-CT modality within +/-7 days **of their selected stroke admission**,
nor that CT was performed for the same event. Diagnosis-date pairs in
`df_merged_age.parquet` are provisional event keys, not confirmed
encounter IDs, and the original notebook may have multiplied imaging
events across diagnosis dates before deduplicating.

## Decision after Step 10

- If candidate and legacy tables reconcile well, use the CT-retaining
  candidate as a *starting point* for an index-date/linkage audit.
- Otherwise, reconstruct from diagnosis and procedure events, preserving
  CT-only patients after selecting the first eligible stroke index event.
- **Do not run population imaging rates, disparities models, or revised
  manuscript analyses until source cohort validity is established.**
- Keep the existing NIS comparison blocked until its age-stratum,
  procedure coding and survey design are confirmed.

## Data protection

Never commit or upload row-level TriNetX extracts or geo fields. The
public repository already contains prior patient-level files whose
redistribution authorization and Git history need review by the
institutional data governance team.

# Phase 1 output review: 2026-10-16

## Input provenance

The collaborator ran Phase 1 locally and supplied four aggregate summaries
plus an age <=50 cohort parquet for examination. This document records
only aggregated results and previously public manuscript data.
**Patient-level derived cohorts must remain local, even without IDs.**

## TriNetX audit

- Original derived cohort: 30,619 distinct patients; no duplicate IDs.
- Diagnosis years: 2018 and 2019; age range 19-54 with original
  sex-specific age caps.
- Valid nonnegative integer counts for MRI, CTA, MRA.
- MRI receipt 25,580 / 30,619; CTA receipt 16,068 / 30,619;
  MRA receipt 7,620 / 30,619.
- Race missing/unknown 23,405 (76.44%); ethnicity missing/unknown
  22,626 (73.90%). Interpretation of race estimates is fragile.

## Common age <=50 descriptive cohort

23,232 patients: 9,674 men and 13,558 women. Counts reflect receipt,
not mean imaging procedure counts.

| Outcome | Men | Women |
| --- | --- | --- |
| MRI | 7,867 / 9,674 (81.32%) | 11,454 / 13,558 (84.48%) |
| CTA | 5,321 / 9,674 (55.00%) | 7,001 / 13,558 (51.64%) |
| MRA | 2,264 / 9,674 (23.40%) | 3,484 / 13,558 (25.70%) |
| Any vascular | 7,156 / 9,674 (73.97%) | 9,806 / 13,558 (72.33%) |

These are **unadjusted descriptive findings**, not causal effects or
measures of quality of care. The vascular-receipt pattern requires
modality-specific and clinical adjustment before interpretation.

## NIS manuscript discrepancy

A stratum matching the v7 values White MRI 0.80 and Black MRI 0.74
in the checked-in NIS summary returns p=0.070823917 rather than the
manuscript's p<0.05. This is NOT proof of an analysis error: the
published values may have come from different inputs or age mappings.
But source strata, weighting and manuscript provenance are not
documented, and the existing NIS summary does not establish
replication. STOP NIS inference until source scripts and HCUP
survey design information are available.

## Decision and next step

- The user-supplied Phase 1 outputs support continuing cohort
  descriptive validation.
- Missing race data remain a major selection concern.
- The saved parquet does **not** contain individual vascular risk
  factors, stroke severity, hospital ID, MRI contraindications, or
  treatment outcomes. These cannot be conjured from the notebook.
- Before fitting a publishable adjusted model, identify the original
  diagnosis and procedure extracts and obtain authorization for
  analysis and public sharing.
- Run `scripts/step05_missingness.py` to characterize observed
  variation associated with known versus unknown race/ethnicity.
- The study team must approve the revised estimands and available
  adjustment variables before implementing final regression analysis.

## Security

The original public repository already includes row-level derived
TriNetX data and a notebook with pseudonymous IDs/geographic details.
Review sharing permissions urgently. A private repository does not
retroactively erase public Git history.

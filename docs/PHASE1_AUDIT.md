# Phase 1: reproducibility and provenance audit

## Scope

The original `disparity_young-claen.ipynb` is **reference only**. It was not
modified. Phase 1 deliberately does not fit new inferential models or
claim validation of the original analysis. Original data access,
clinical provenance, code definitions, and NIS survey handling must be reviewed.

## Why this audit is needed

1. **Cohort**: the original extracted table has already been restricted
   to ages <=52 for men and <=54 for women. A common <=50 cutoff can
   be reconstructed, but <=55 and unrestricted adult analyses require
   extraction from the source tables. Minimum age is >18 in legacy code.
2. **Confounding**: the notebook creates a CHA2DS2-VASc-like score by
   adding a female-sex point. Conditioning on it in a sex model is difficult
   to interpret. Several condition code sets are exact-match lists, with
   incomplete ICD prefix coverage. Phase 2 must build and validate
   individual covariates from source diagnosis records.
3. **Outcomes**: binary any-MRI, any-CTA, any-MRA and any-vascular
   imaging are different from the number of procedures. The latter
   cannot establish equality of care.
4. **Sample**: the original notebook has 30,619 unique patients, but
   explicit checks for repeat patient-years, diagnosis selection, the
   date window and the CT-only eligibility restriction need raw source.
5. **Missingness**: the notebook output reports 76.4395% missing/unknown
   race and 73.8953% missing/unknown ethnicity.
6. **NIS**: the checked-in CSVs are already-aggregated results; they
   do not contain the source sampling, strata, clusters, or procedure
   code logic. In the checked-in race CSV, stratum 6 is White MRI
   0.800000072, Black MRI 0.740000746, with p=0.070823917. Manuscript
   v7 instead states 0.80 vs 0.74 with p<0.05. The notebook also
   explicitly selects age stratum 1 in the NIS plotting code. Thus
   the current code and CSVs do not substantiate manuscript v7's NIS
   comparison. The provenance of age bins and manuscript versions
   needs review before publication.
7. **Public repository**: a patient-level parquet file is currently
   tracked in this public GitHub repo, as well as notebook output
   examples showing pseudonymous patient IDs and postal codes.
   Confirm TriNetX redistribution authorization and institutional
   privacy clearance. Do not add patient-level files, secrets,
   or data excerpts in pull requests/issues. Git history may need
   separate remediation if the file is unauthorized.

## Execution

Install dependencies from `requirements.txt`. Run from the repository root:

```bash
python -m pytest -q
python scripts/step01_audit.py
python scripts/step02_prepare.py --max-age 50
python scripts/step03_describe.py
python scripts/step04_audit_nis.py
```

Outputs go to ignored `results/phase1/`. Check warnings and
reconcile differences with the submitted manuscript. The derived
cohort remains record-level data despite removing patient_id and
postal_code. Keep `results/` secure and do not distribute it.

## Stop conditions

- Any missing columns, invalid imaging counts, or unexpected
  duplicate patient IDs: stop the pipeline and inspect upstream.
- NIS age-stratum definition or survey design unverified:
  do not claim cross-database replication.
- Original CT-only eligibility, first admission, or +/-7-day
  imaging linkage unverified: label as unverified and retrieve
  original extracts/queries.
- Unsuitable permissions for source data in the public repo:
  resolve institutional and provider data-sharing permissions
  before distributing further records or derived tables.

## Next stages (not yet implemented)

- Document diagnosis/procedure provenance and validate ICD/CPT codes,
  particularly neck CTA and MRA and encounters/timestamps.
- Define and approve primary outcomes and study age range.
- Re-extract individual vascular risk factors from pre-index events.
- Define separate sex and race adjustment strategies, with clear
  missingness analyses. Avoid interpreting model coefficients as
  treatment-quality disparities.
- Fit GLM models, standardized adjusted risks/risk differences with
  CIs; conduct sensitivity analyses and validate figure code.
- Reconcile NIS survey-weighted models using original source code
  and tables; otherwise remove replication claims.

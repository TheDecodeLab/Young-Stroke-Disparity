# Young Stroke Neuroimaging: Reproducibility and Re-analysis

This repository supports an observational study of brain MRI and vascular
imaging selection among adults hospitalized with early-onset ischemic stroke.
The prior notebook `disparity_young-claen.ipynb` remains **unchanged as the
legacy reference**. New work uses documented, tested Python scripts.

## Status

**CRITICAL SCIENTIFIC STOP: The current derived cohort omits CT-only
stroke patients.** The Step 7 results show that all 23,232 age 19-50
patients received MRI, CTA or MRA. Review of the historical notebook
shows CT rows are removed before aggregating patient imaging.
Therefore Steps 2-7 currently describe an imaging-selected subset
and MUST NOT be used to estimate population MRI/vascular imaging rates
or clinical disparities. Reconstruct the index stroke cohort using the
upstream diagnosis, encounter and procedure data while retaining CT-only
patients. See [cohort selection audit](docs/COHORT_SELECTION_FINDING.md) [Step 9 recovery instructions](docs/STEP09_RECOVERY_PLAN.md), and [Step 10 reconciliation](docs/STEP10_RECONCILIATION.md), and [Step 11 event-linkage findings](docs/STEP11_EVENT_LINKAGE.md), and [Step 12 index-sensitivity audit](docs/STEP12_INDEX_SENSITIVITY.md).


**Phase 1: data provenance and baseline audit (in progress).**
No new adjusted association or manuscript finding has been validated.
Do not interpret imaging frequency as quality or equity of clinical care.

## Requirements

Python >=3.10. In the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

## Step-by-step execution

```bash
python scripts/step01_audit.py
python scripts/step02_prepare.py --max-age 50
python scripts/step03_describe.py
python scripts/step04_audit_nis.py
python scripts/step05_missingness.py
python scripts/step06_minimal_models.py
python scripts/step07_modality_patterns.py
python scripts/step08_cohort_integrity.py
# Local recovery audit; source files are stored one directory above repo:
python scripts/step09_audit_recovery.py --files ../df_merged_age.parquet ../df_trinetx_total_young_wCT.parquet
# Reconcile the CT-retaining and legacy young-stroke tables:
python scripts/step10_reconcile_cohorts.py
# Audit original linked imaging/diagnosis dates before reconstruction:
python scripts/step11_event_linkage.py
# Compare provisional CT-index and advanced-imaging-index dates:
python scripts/step12_index_sensitivity.py
```

### What each script does

| Script | Purpose | Local output |
| --- | --- | --- |
| `step01_audit.py` | Validate schema, missingness, imaging counts and patient uniqueness | `results/phase1/trinetx_audit.json` |
| `step02_prepare.py` | Restrict to common ages 19-50; derive **binary receipt**, procedure counts and vascular modality combinations | `results/phase1/cohort_age50.parquet` |
| `step03_describe.py` | Aggregate denominators and percentages by sex, race and ethnicity | `results/phase1/descriptive_age50.csv` |
| `step04_audit_nis.py` | Inspect previously published NIS summary CSV strata against manuscript values | `results/phase1/nis_stratum_audit.csv` and `.json` |
| `step05_missingness.py` | Evaluate selection associated with known/unknown race and ethnicity by sex/year | `results/phase1/missingness_age50.csv` |
| `step06_minimal_models.py` | **Preliminary** age/year-only binomial GLM and standardized sex risk differences | `results/phase1/minimal_models_age50.csv` |
| `step07_modality_patterns.py` | Descriptive, mutually exclusive CTA/MRA pathways by sex, year, and age bands | `results/phase1/modality_patterns_age50.csv` |
| `step08_cohort_integrity.py` | Critical selection check: detect absence of CT-only patients | `results/phase1/cohort_integrity_age50.json` |
| `step09_audit_recovery.py` | Audit local pre-exclusion Parquet candidates without sharing record-level data | `results/phase1/recovery_candidate_audit.json` |
| `step10_reconcile_cohorts.py` | Reconcile CT-inclusive and legacy derived young-stroke tables by aggregate patient overlap and imaging-count concordance | `results/phase1/cohort_reconciliation.json` |
| `step11_event_linkage.py` | Check event-date linkage, first imaging-linked diagnosis and discordance with saved tables (audit only) | `results/phase1/event_linkage_audit.json` |
| `step12_index_sensitivity.py` | Compare earliest any-imaging, CT-linked, and advanced-imaging-linked diagnosis dates (audit only) | `results/phase1/index_definition_audit.json` |

### How to interpret

These steps provide descriptive checks only. They **do not**
verify the original diagnosis date linkage, principal-diagnosis
eligibility, CT restriction, CPT code completeness, hospitalization
structure or NIS survey design. See [the Phase 1 audit guide](docs/PHASE1_AUDIT.md), [the initial results review](docs/PHASE1_RESULTS.md), [the missingness review](docs/MISSINGNESS_RESULTS.md), and [the preliminary model review](docs/STEP06_RESULTS.md) for discrepancies, unresolved questions and stop conditions.

The original sample used sex-specific <=52/<=54 age limits.
This saved derived dataset cannot support a true common <=55 analysis
or analysis of younger patients previously excluded. New source
extraction would be needed.

## Data governance

**Warning:** This repository is public and already includes a tracked
patient-level derived parquet file and notebook outputs with
pseudonymous identifiers and geography. TriNetX data may have
contractual distribution restrictions. Confirm institutional and
provider permissions promptly and assess whether tracked files
and Git history require remediation. The analysis scripts do not
write patient identifiers into audit summaries. Nevertheless, any
row-level derived output remains sensitive and is locally ignored
via `results/`; do not push it, publish it or attach it to issues.

## Development principles

- Preserve the original notebook and data unchanged for traceability.
- Do not hardcode manuscript values as replacement results.
- Validate schemas, inclusion criteria and missingness before modeling.
- Distinguish procedure **receipt** from procedure **counts**.
- Run scripts and tests before interpreting estimates.
- Produce all tables and figures with code acting on actual authorized data.
- Use pull requests to review methodological and code changes.

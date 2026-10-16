# Young Stroke Neuroimaging: Reproducibility and Re-analysis

This repository supports an observational study of brain MRI and vascular
imaging selection among adults hospitalized with early-onset ischemic stroke.
The prior notebook `disparity_young-claen.ipynb` remains **unchanged as the
legacy reference**. New work uses documented, tested Python scripts.

## Status

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
```

### What each script does

| Script | Purpose | Local output |
| --- | --- | --- |
| `step01_audit.py` | Validate schema, missingness, imaging counts and patient uniqueness | `results/phase1/trinetx_audit.json` |
| `step02_prepare.py` | Restrict to common ages 19-50; derive **binary receipt**, procedure counts and vascular modality combinations | `results/phase1/cohort_age50.parquet` |
| `step03_describe.py` | Aggregate denominators and percentages by sex, race and ethnicity | `results/phase1/descriptive_age50.csv` |
| `step04_audit_nis.py` | Inspect previously published NIS summary CSV strata against manuscript values | `results/phase1/nis_stratum_audit.csv` and `.json` |

### How to interpret

These steps provide descriptive checks only. They **do not**
verify the original diagnosis date linkage, principal-diagnosis
eligibility, CT restriction, CPT code completeness, hospitalization
structure or NIS survey design. See [the Phase 1 audit guide](docs/PHASE1_AUDIT.md)
for discrepancies, unresolved questions and stop conditions.

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

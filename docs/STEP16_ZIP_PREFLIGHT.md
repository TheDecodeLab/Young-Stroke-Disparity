# Step 15 findings and Step 16 bounded ZIP preflight

## Results of the locally generated ZIP inventory

The approved TriNetX ZIP includes 20 members (19 CSV and one TXT).
Three original source members have all of the required columns
identified by header inspection:

| ZIP member | Uncompressed size | Columns relevant to reconstruction |
| --- | ---: | --- |
| `diagnosis.csv` | ~82.7 GB | patient_id, code_system, code, principal_diagnosis_indicator, date |
| `procedure.csv` | ~54.9 GB | patient_id, code_system, code, date |
| `patient.csv` | ~311 MB | patient_id, sex, race, ethnicity, year_of_birth |

The whole archive is approximately 398 GB uncompressed, compared
with about 32.7 GB in compressed members. We should NOT expand the
entire ZIP to disk just to inspect or read these sources.

**Critical linkage finding:** The diagnosis and procedure headers
do not contain a clear encounter/admission identifier. They have
patient IDs and event dates. A patient/date-based link cannot be
assumed to identify the same admission. A comparison with other
ZIP tables and institutional provenance information is necessary.

The Step 15 schema ranking is heuristic: labs and vitals can resemble
procedure tables because they share `patient_id, code, date`.
They should not be substituted for `procedure.csv`.

## Step 16: bounded format and linkage preflight

This is a rapid, read-only check before designing the full
streaming source extraction. It does not decompress the entire
diagnosis or procedure table.

First set the ZIP path in your **local shell only**:

```bash
export TRINETX_ZIP="/path/to/approved/local/trinetx_source.zip"
```

From the repository root:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step16_zip_preflight.py --zip "$TRINETX_ZIP" --sample-rows 10000
```

The script reads headers for all CSV/TSV archive members and scans
only the **first 10,000 records** of each of `diagnosis.csv`,
`procedure.csv`, and `patient.csv` directly from the ZIP.
It never reads patient IDs or postal/geographic columns into the
sampled data frames. No ZIP members are extracted.

Output: `results/phase1/zip_preflight.json`, gitignored.
Inspect locally before sharing, because filenames and headers may
still include sensitive institutional information.

The JSON reports:
- Header column names and potential admission/encounter fields
  across **all** archive tables, including non-imaging tables.
- Examples of common *code system categories* (aggregate counts only),
  principal-diagnosis indicators and date formats.
- Whether MRI, CT and a provisional I63 code family can be parsed
  as expected within the **first-row sample**.
- Race/ethnicity missingness among sampled first rows, for data
  format validation only.

**These samples are not representative.** If the archive is sorted
by patient, date, site, or code, there may be few or no 2018-19 stroke
cases in the first rows. Do not use Step 16 sample percentages or
counts to estimate prevalence, eligibility, coverage, or modality
utilization. A zero count is not absence of that code in the archive.

## Next milestone

After checking ZIP column formats and whether any encounter-linked
tables exist, design a full **chunked, sequential scan** of original
diagnoses to define first qualifying principal ischemic-stroke
index events independently of imaging. Cross-check diagnosis coding,
date, first event, lookback and hospitalization logic.

Only then scan original procedures, associate modalities with that
index using explicitly validated patient/time/encounter rules,
retain patients who received CT alone, and produce secure local
derived outputs. If no encounter linkage exists, state the
resulting limitation and consider requesting source encounter data.

All codebooks (including CTA neck, MRA neck, brain MRI, stroke ICD-10
and historical ICD-9 codes) require clinical review before defining
the study cohort. Source tables may be very large; avoid holding
all patient rows in memory and do not materialize full source tables
to disk. Any persistent intermediate containing patient IDs must
remain in access-controlled institutional storage, never GitHub.

Previous imaging rates and effect estimates are still blocked for
population-level inference. IHME-GBD is not part of this clinical
record-linkage repair.

## Data governance

The repository is public and already tracks an older patient-level
derived table with pseudonymized identifiers/geographic information.
Review contractual and institutional permissions and repository
history remediation. Do not upload the original ZIP or rows,
and review aggregate reports for disclosure before sending them.

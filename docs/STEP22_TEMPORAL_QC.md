# Step 22: validate the completed provisional reconstructed cohort without rereading the ZIP

## Review of local full reconstruction

The study team's `chained_reconstruction_audit.json` confirms that
all three original source tables were completely scanned and reconciled
against their manifest row counts:

| Source | Scanned source rows |
| --- | ---: |
| diagnosis.csv | 1,425,659,024 |
| patient.csv | 4,285,214 |
| procedure.csv | 1,166,493,611 |

**Diagnosis-first index:** 962,351 unique patients with an earliest
principal (P) ICD-10-CM I63-family diagnosis in 2018–2019; the source
contains 3,872,074 principal I63 diagnosis rows in those years.
These records are **not** independently verified admissions or first-ever
stroke events. No encounter ID is available in the source.

**Demographic eligibility:** Among the 962,351 indexed patients,
86,902 have a recognized binary sex and approximate age 19–50.
Missing birth year was reported for 100,654 indexed records; age
and representativeness need careful review.

**Imaging, historical nine CPT codes, ±7 days:**

| Non-overlapping class | Patients |
| --- | ---: |
| CT only | 8,713 |
| CT + MRI/CTA/MRA | 24,074 |
| MRI/CTA/MRA without CT | 9,355 |
| No matching CT/MRI/CTA/MRA code | 44,760 |
| Total age-eligible I63 diagnosis index | 86,902 |

The source-linked counts match the partition identity and retain
CT-only records. They **are not valid hospitalized-stroke imaging
utilization rates**. In particular, the no-listed-imaging group
comprises 51.5% of the index; the cohort is diagnosis-based rather
than encounter-validated, and the historical nine-code CPT list
does not cover all imaging modalities/coding systems and neck imaging.

## Step 22: inexpensive post-scan diagnostics

Run on the study workstation using the **same private directory**
used by the successful full chained scan. This step opens the completed
diagnosis, demographic and imaging SQLite files in **read-only mode**
and does not open, decompress or rescan the source ZIP.

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q

python scripts/step22_temporal_qc.py \
  --private-dir "$TRINETX_PRIVATE" \
  --compare-audit results/phase1/chained_reconstruction_audit.json \
  --output results/phase1/step22_temporal_qc.json
```

If the shell variable `TRINETX_PRIVATE` is not set, export it first
to the existing owner-only `chained_v1` directory on the approved
local workstation. Do **not** create another directory or rerun the
large ZIP scans. The script rejects incomplete SQLite stage files,
inconsistent diagnosis/index links, dates outside the original
±7-day window and incorrect aggregate counts.

The JSON output contains only totals and disclosure-checked
strata. It compares matching the index date alone (0 days)
versus ±1, ±3 and ±7 days, plus broad year/sex/age-band summaries.
Small subgroup results are suppressed rather than exposed.
It also reports unknown/missing race and ethnicity and the
number of patients at age cutoffs 19 and 50, where birth-year-only
age is uncertain.

## Scientific decisions needed after this check

1. **Study denominator:** Whether the intended study is a
   diagnosis-based sample, a CT-imaged stroke pathway, or
   verified hospitalized ischemic-stroke admissions. These
   populations have different definitions and denominators.
2. **Encounter attribution:** No encounter key is available
   from this Diamond export. Temporal proximity is **not**
   encounter linkage. Consider sourcing visit/admission-linked
   records for a hospital utilization study.
3. **Code coverage:** The nine historical CPT codes omit
   CTA neck (`70498`), MRA head with/without contrast
   (`70546`), MRA neck (`70547`–`70549`) and potential
   other relevant procedures and coding systems. This audit
   cannot recover omitted code-specific events from the
   existing `step20_imaging_events.sqlite`; re-extraction
   would be needed after protocol approval.
4. **Index incidentness:** A patient's earliest principal I63
   diagnosis *in 2018–2019* is not the earliest lifetime
   ischemic stroke; prior history and encounter type
   require source validation.
5. **Missingness and model covariates:** Determine how missing
   birth year (100,654 indexed patients), race/ethnicity
   and clinical severity/indications affect interpretation
   before demographic disparity modeling.

**Status: exploratory cohort QC only.** Do not use this reconstruction
to replace manuscript population imaging rates or adjusted
demographic coefficients yet. The public repository still requires
review of pre-existing sensitive files and redistribution permissions.

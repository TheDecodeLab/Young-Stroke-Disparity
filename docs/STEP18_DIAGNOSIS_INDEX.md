# Step 17 result and Step 18 diagnosis-first reconstruction

## Original source and scale

The study team's `zip_provenance.json` verifies the full **TriNetX
Diamond** source export created **2023-08-01**, with **4,285,214**
unique patients from **92 HCOs**. The manifest reports:

| Original ZIP member | Source records | Unique patients |
| --- | ---: | ---: |
| `diagnosis.csv` | 1,425,659,024 | 4,285,214 |
| `procedure.csv` | 1,166,493,611 | 4,231,033 |
| `patient.csv` | 4,285,214 | 4,285,214 |
| `patient_cohort.csv` | 4,285,214 | 4,285,214 |

`cohort_details.csv` labels the whole export `Diamond Data`.
This is **not** a narrow extraction of the 2018–2019
ischemic-stroke population. The metadata show no evidence of a
patient encounter key. Existence of a principal diagnosis in
TriNetX is not sufficient to verify an index hospitalization.

## Why Step 18

The old notebook joined selected imaging to diagnoses by patient ID
and a ±7-day window, dropped CT events, and then chose the earliest
remaining diagnosis. Thus, the original young cohort excluded CT-only
patients and could select a later index associated with advanced
imaging.

The correction must start with the **diagnosis file**, entirely
independent of CT/MRI/CTA/MRA, then apply demographic eligibility and
imaging linkage downstream. A single full diagnosis scan is large:
~82.7 GB uncompressed, 1.43 billion rows. Do not load it all
into pandas or extract the full ZIP.

## Step 18 contract

`scripts/step18_diagnosis_index.py` streams
`diagnosis.csv` directly from the original ZIP in bounded chunks.
It writes a **private, local SQLite** index with the earliest
**2018–2019 principal ICD-10-CM I63-family DIAGNOSIS** for
each patient. It does not load any procedure records, select on
imaging, or yet restrict age/sex. It reads the original manifest
to verify the complete scan row count.

This rule is **provisional**:
- Principal indicator must be `P`. `S` and `Unknown` are
  counted or excluded, not assumed eligible.
- Code system must be `ICD-10-CM`; family `I63` and subcodes
  are initially included. `H34.1` (retinal artery occlusion)
  and old ICD-9 stroke codes are not silently imported.
- The first qualifying record *within 2018–2019* is not necessarily
  a **first-ever stroke**: diagnoses before 2018 require a separate
  lookback/sensitivity analysis.
- A date-based principal diagnosis does not prove an **inpatient
  admission**; no encounter ID has been found.
- No age restriction or CT eligibility is evaluated in Step 18.
- Source code lists and study design require clinical investigator
  review before manuscript inference.

## Safe execution (two explicit modes)

Run from the repository root. Set the local ZIP path and a private
work directory in **approved local storage** (never inside this
public repo):

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q

export TRINETX_ZIP="/path/to/approved/source.zip"
export TRINETX_PRIVATE="/path/to/approved/private_young_stroke"

# First do a fast, deliberately NONREPRESENTATIVE smoke test.
python scripts/step18_diagnosis_index.py \
  --zip "$TRINETX_ZIP" \
  --private-dir "$TRINETX_PRIVATE/smoke18" \
  --limit-rows 100000 \
  --output results/phase1/step18_smoke_audit.json
```

Inspect the aggregate smoke report and the test summary.
The smoke SQLite is `step18_diagnosis_index.partial.sqlite`, and its
`scan_complete` flag is 0. **Never use its records for downstream
analysis.** The script also refuses to overwrite any existing
partial or completed SQLite database.

After reviewing the codebook and resource use, run a new
full source scan separately:

```bash
python scripts/step18_diagnosis_index.py \
  --zip "$TRINETX_ZIP" \
  --private-dir "$TRINETX_PRIVATE/full18" \
  --full-scan \
  --output results/phase1/step18_diagnosis_index_audit.json
```

The full scan may take **hours** depending on CPU, ZIP compression,
filesystem and disk performance. Progress within a compressed ZIP
cannot be resumed at arbitrary row positions without decompressing
earlier data. An interrupted run leaves a `.partial.sqlite` database
that must NOT be treated as complete. The full SQLite index is only
renamed `step18_diagnosis_index.sqlite` after successful completion
and manifest row-count verification.

The sensitive SQLite file includes pseudonymous patient IDs and
diagnosis dates. It must remain in a directory with owner-only
permissions in approved storage and never enter Git. The script
rejects workdirs located inside the Git repository. Only the
aggregate JSON reports under ignored `results/phase1` may be
considered for disclosure, after reviewing them.

## Subsequent work, **not yet implemented**

1. Scan original `patient.csv` and link demographics to the
   complete diagnosis-first index, without putting age eligibility
   in the source diagnosis selection.
2. Agree an age and sex threshold (e.g., a uniform age 19–50 for a
   fully observable comparison; prior sex-specific thresholds require
   separate review). Calculate age as approximate
   `diagnosis year - year of birth` and document its uncertainty.
3. Stream relevant original `procedure.csv` codes and associate
   CT, MRI, CTA and MRA to index dates using a specified ±7-day
   temporal proxy, retaining zero non-CT imaging outcomes.
   Review code systems and head/neck imaging coverage.
4. Audit multiple strokes/procedures, ambiguous time windows,
   missingness, attrition and the fraction of people with no CT.
   Never label temporally linked events as encounter-verified
   admissions.
5. Only after this evaluate clinical covariates, missingness,
   sensitivity analyses and suitably qualified models. The
   NIS analysis remains an independent unresolved issue.

## Data governance

The public repository already contains legacy row-level TriNetX
derived data, potentially including geographic fields. Verify
redistribution approval and whether Git history needs remediation;
do not commit the new SQLite index, private directories or
original ZIP. Patient identities/linked dates are never put in
the Step 18 aggregate JSON.

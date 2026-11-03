# Steps 18–21: chained reconstruction from the original Diamond ZIP

## Status: provisional temporal cohort, NOT publication results

The local provenance metadata confirmed that the original ZIP is a
TriNetX Diamond export from 2023-08-01 with 4,285,214 patients,
1,425,659,024 diagnosis records, 1,166,493,611 procedure records,
and 92 participating HCOs. The archive's source tables do not include
an identifiable encounter/admission key.

The legacy young-stroke analysis was conditioned on receipt of MRI,
CTA or MRA, excluding CT-only patients. Its denominator and adjusted
estimates are not suitable for the intended clinical population.

The new sequence deliberately chooses a qualifying **diagnosis first**,
then demographics, then imaging. It uses original source CSV records
inside the ZIP and **never extracts the whole archive**. Only the
small relevant SQLite indexes are retained in approved private
storage. Even after a successful full scan, a `patient_id + date`
match is **not encounter validation**.

## One-stop workflow

Set the source archive path in the LOCAL shell. Keep the actual path,
patient records and institution-specific workdir out of public GitHub.

```bash
git pull origin analysis-rebuild-phase1-audit

export TRINETX_ZIP="/path/to/approved/diamond_source.zip"
export TRINETX_PRIVATE="/path/to/approved/private_storage/young_stroke_reconstruction"

# Tests must succeed before any clinical source scan.
python -m pytest -q && \
python scripts/step19_21_reconstruct.py \
  --zip "$TRINETX_ZIP" \
  --private-dir "$TRINETX_PRIVATE" \
  --smoke \
  --output results/phase1/chained_smoke_audit.json && \
python scripts/step19_21_reconstruct.py \
  --zip "$TRINETX_ZIP" \
  --private-dir "$TRINETX_PRIVATE" \
  --full --min-age 19 --max-age 50 \
  --output results/phase1/chained_reconstruction_audit.json
```

**Warning:** This single command will trigger **both** a brief
smoke test and the FULL scans of 1.43 billion diagnosis rows and
1.17 billion procedure rows if the tests and smoke test pass.
It could take many hours and use substantial local compute and
SQLite space. Start only when your workstation is ready to run for
a sustained period. Consider a persistent SSH/tmux session and
confirm local CPU, RAM, and disk quota beforehand. If you only
want the short check, omit the final `--full` command and
stop after `--smoke`.

The smoke test reads the FIRST 100,000 diagnosis rows only,
stores an explicitly **INCOMPLETE** private SQLite file and
must NOT be used as a cohort. The full run uses independent
stage folders under `$TRINETX_PRIVATE`; it cannot accidentally
consume the smoke database.

### Stages performed by the full run

1. **Step 18, principal ischemic-stroke diagnosis index.**
   Scan the entire original `diagnosis.csv` directly inside ZIP,
   restrict to 2018–19 `ICD-10-CM` `I63` and principal indicator
   `P`, and save earliest qualifying diagnosis per patient in
   the private `diagnosis/step18_diagnosis_index.sqlite`.
   Verify total source rows against `manifest.csv`.
2. **Step 19, demographic eligibility.** Read the original
   `patient.csv` once, join to the completed diagnosis-first
   index, require recognized binary sex and approximate
   `index year - year_of_birth` between 19 and 50 inclusive,
   and write eligible records to private
   `demographics/step19_age_cohort.sqlite`. No CT/MRI/CTA/MRA
   condition is applied in this stage.
3. **Step 20, imaging receipt.** Stream all original
   `procedure.csv` records. Search the nine historical
   CPT imaging codes from `dataset/df_tot_CPT_codes.csv` in a
   `±7 day` window around each selected diagnosis date.
   Deduplicate **patient + modality + procedure date** across
   CSV chunks. Save only matched events to private
   `imaging/step20_imaging_events.sqlite`.
4. **Step 21, aggregate integrity checks.** Count CT, MRI, CTA
   and MRA receipt. Most importantly, distinguish **CT-only**
   patients, CT plus additional imaging, additional imaging without
   CT, and no identified imaging, with a complete partition of
   the age-eligible diagnosis index cohort.

Each complete stage is checkpointed. Rerunning the **same**
command with the **same source and age rules** skips completed
stages. Missing, mismatched or incomplete stages stop rather
than silently proceeding. The workflow stores a source-archive
fingerprint and validates age and imaging-rule compatibility
on restart. Interrupted compressed ZIP scanning is not random
access/resumable: a partial stage must be inspected before
performing any intentional reset, and rerunning that stage
would decompress the source from the beginning.

Periodic progress output reports only total source rows scanned,
never patient data.

## Output and privacy

Only the **aggregate** reports in ignored
`results/phase1/chained_smoke_audit.json` and
`results/phase1/chained_reconstruction_audit.json`
should be reviewed for sharing. They contain counts and
limitations, not individual patient identifiers, diagnosis
dates, or geo fields.

Sensitive patient-level SQLite files remain in an approved
local owner-only directory **outside Git**. They must not be
uploaded to ChatGPT, GitHub, PR comments, public artifacts or
unapproved file sharing services. The script rejects paths
within the Git repository.

## Scientific limitations that still block manuscript inference

- **No encounter key:** first principal I63 diagnosis in 2018–19
  is not necessarily the first-ever ischemic stroke or a true
  inpatient admission. A `±7 day` patient/time window could
  associate imaging from another encounter.
- **Provisional codebook:** the original notebook included
  historical ICD-9 stroke codes and `H34.1`; the new primary
  audit intentionally starts with principal ICD-10-CM `I63`
  only. The original nine CPT codes omit `70498` (CTA neck),
  `70546` (MRA head with/without contrast), and neck MRA
  codes. Do NOT silently treat this as complete vascular imaging.
- **Uncertain age:** only birth year is available; age
  from calendar years is approximate at the threshold.
- **Clinical selection:** imaging indication, severity,
  hospital/provider clustering, encounter verification,
  comorbidities and data missingness still need validation.
- **No original replacement claims:** numerical consistency
  with the legacy 30,619-patient table is not expected because
  the definitions and selection order have changed.

**A successful complete scan is an engineering milestone, not
permission to use reconstructed imaging rates for publication.**
Next, compare inclusion/attrition, review coding with Ramin
and Vida, verify administrative encounter linkage availability,
then design covariate-rich sensitivity analyses and an
appropriately qualified manuscript. NIS remains a separate
unresolved data-provenance task.

## Public repository data governance

Earlier repository history already tracks a patient-level TriNetX
Parquet file and pseudonymous IDs/geography. Review institutional
and vendor redistribution permissions and any necessary Git
history cleanup. Never add new clinical rows or SQLite artifacts
to this public repository.

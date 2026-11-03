# Step 16 results and Step 17 provenance gate

## Direct ZIP preflight findings

The study team inspected all 20 source archive headers and the first
10,000 records of diagnosis, procedure and patient files (a **bounded,
nonrepresentative format check**, not a cohort analysis).

- `diagnosis.csv`: diagnosis code systems include ICD-9-CM and
  ICD-10-CM in the sample; date values use `YYYYMMDD`.
- `procedure.csv`: CPT, HCPCS and ICD-10-PCS code systems occur;
  dates use `YYYYMMDD`.
- `patient.csv`: sex, race, ethnicity and birth year are present.
- Diagnosis `principal_diagnosis_indicator`: sample categories include
  `P`, `S`, and `Unknown`. Treat unknown principal status
  separately; a code for stroke is not by itself a confirmed
  hospitalization.
- **None of the 20 member headers contains an explicit encounter or
  admission ID**. The initial Step 16 string-search flagged
  `reason_for_visit` but this is a descriptive field, NOT an
  encounter identifier. The scanner has been corrected.
- The larger original export is 398 GB when uncompressed; an in-ZIP
  sequential scan will use substantially less disk than extraction,
  but may be time-consuming and needs memory bounds.

The original notebook used a patient-only join plus a +/-7-day window
and then excluded CT-only patients by dropping CT rows before
aggregation. We cannot call a date-window match a hospital encounter.

## Step 17: confirm export and cohort provenance

Before scanning the ~82.7 GB uncompressed diagnosis table and ~54.9 GB
uncompressed procedure table, check the small export metadata:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step17_zip_provenance.py --zip "$TRINETX_ZIP"
```

Set `TRINETX_ZIP` in your local shell to the original approved ZIP path
first, if it is not already set.

Output: `results/phase1/zip_provenance.json` (gitignored).

This step reads only four small metadata files:
`manifest.csv`, `cohort_details.csv`, `dataset_details.csv`,
and `readme.txt`. It never reads any patient, diagnosis, procedure
or patient-cohort records. It reports the manifest row counts,
cohort descriptions, total patients and healthcare organizations,
metadata-readme keyword flags, and a hash of the README.
The raw README text and dataset network name are withheld.

**Review cohort labels and metadata before sharing** the aggregate
JSON. A cohort name such as "stroke" does not establish that the
export includes every eligible 2018-2019 stroke admission or
that hospital encounters are identifiable.

## After Step 17

We can design a bounded streaming read of source diagnoses and
procedures directly from ZIP. The analysis will need two separate
and explicit decisions:

1. Define the first qualifying principal ischemic-stroke *diagnosis*
   independently of any imaging receipt, using approved ICD codes,
   sex/age restrictions, year and lookback rules.
2. Define **temporal imaging linkage**, including CT-only patients,
   while stating that the source lacks encounter identifiers. If
   true index admissions are essential to the intended research
   question, obtain an encounter-linked export from the provider
   rather than claiming the patient/date proxy represents admission.

Before modeling, review ischemic stroke code inclusions (particularly
historical retinal artery occlusion, ICD-9, and I63 subcodes),
CPT/HCPCS/ICD-10-PCS modality coverage, head-versus-neck imaging,
the +/-7-day time window and possible early strokes without
principal-diagnosis flags.

No previous imaging utilization or sex/race model result is currently
supported for the intended population. The public Git repository
already contains older patient-level data, so verify TriNetX and
institutional redistribution permissions and assess history cleanup.

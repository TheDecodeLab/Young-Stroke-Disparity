# Steps 23–24: explain eligibility attrition and missing-imaging patterns

## Findings from Step 22

The complete local SQLite reconstruction agreed exactly with the prior
chained aggregate JSON. No original ZIP rows were reprocessed.

- Provisional diagnosis index: **962,351** patients with first principal
  2018–19 ICD-10-CM I63 diagnosis in the export.
- Age 19–50 with recognized binary sex: **86,902**.
- At ±7 days, historical nine CPT codes linked 8,713 CT-only,
  24,074 CT + MRI/CTA/MRA, 9,355 non-CT imaging without CT, and
  44,760 with none of the listed imaging codes.
- **77.9%** of the age-eligible cohort has unknown/missing race
  (67,700); **75.4%** has unknown/missing ethnicity (65,517).
- Imaging receipt depends strongly on the time window:
  CT 24,826 same-day versus 32,787 at ±7 days;
  MRI 17,080 same-day versus 27,459 at ±7 days.
- All counts remain **provisional**: temporal linking is not
  verified admission-level linking.

## Next audit without rescanning billion-row sources

`scripts/step23_24_eligibility_qc.py` combines two steps:

**Step 23: Diagnose why the 962,351 indexed patients shrink to
86,902 eligible patients.** It reads only `patient.csv` from the
original authorized ZIP (~311 MB uncompressed) once, and the existing
completed diagnosis and demographics SQLite files read-only.
It assigns each indexed patient to one mutually exclusive reason:
missing/invalid birth year, unsupported sex, below age 19, age 19–50,
or above age 50. It verifies the original CSV row count from the
ZIP manifest, confirms every index patient is represented, and
reconciles the saved 86,902-person age-eligible cohort.

**Step 24: Investigate missing matching imaging.** Without reading
any original procedure or diagnosis CSV rows, it links the completed
private diagnosis and imaging SQLite tables and reports a coarse
I63 first-decimal-digit classification against the four mutually
exclusive imaging groups. It also counts unknown/missing race and
ethnicity separately within each imaging group.

These are *diagnostic comparisons*, not stroke subtypes, quality
metrics, representative utilization rates, or disparity tests.
Small diagnostic groups are withheld. Inspect all outputs for
secondary disclosure risk before sharing.

## Run both steps with one command

Use the SAME original ZIP and private directory where the previous
full run saved its completed stages:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q && \
python scripts/step23_24_eligibility_qc.py \
  --private-dir "$TRINETX_PRIVATE" \
  --zip "$TRINETX_ZIP" \
  --compare-step22 results/phase1/step22_temporal_qc.json \
  --output results/phase1/step23_24_eligibility_qc.json
```

Set `TRINETX_ZIP` and `TRINETX_PRIVATE` locally if not already set.
The selected private directory must be the completed
`young_stroke_private/chained_v1` directory, stored outside Git in
owner-only authorized storage.

**This step is much cheaper than the prior 2.6 billion-row scans**:
it reads the completed private SQLite indexes plus the small
demographic source member, and does not revisit
`diagnosis.csv` or `procedure.csv`.

Only upload the reviewed aggregate JSON
`results/phase1/step23_24_eligibility_qc.json`, not the ZIP, original
CSV rows, private SQLite, logs containing patient IDs, or any
individual-level Parquet data.

## Next scientific decision

The study design still needs a defensible answer to the following:
is the target population *patients with a principal stroke diagnosis*,
*patients with CT-imaged stroke pathways*, or *confirmed hospitalized
ischemic-stroke patients*? These are different denominators. The
source lacks encounter/admission IDs, and current CPT coverage omits
CTA neck, MRA neck and other procedure coding systems.

Do not interpret a lack of one of the historical nine CPT codes
as proof that a patient had no brain imaging. If the study aims to
characterize hospital utilization, obtain encounter-linked events
or predefine and evaluate the limitations of temporal attribution.
Obtain clinical sign-off on codebook and outcome eligibility rules
before costly expanded-code rescans or regression modeling.

Existing public repo patient-level data and Git history still require
institutional/TriNetX redistribution compliance review. Keep PR draft.

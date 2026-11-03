# Step81: Decision gate for a demographic-plus-measurement manuscript

**Status:** Committed, workstation tests and local run PENDING.

## Reviewer feedback considered (2026-10-20)

Before rewriting the manuscript as a combined sex/race and
encounter-recording study, first confirm whether the source
demographics are sufficiently captured and whether the
modality-specific results are informative. Treat the
unvalidated principal-I63 P flag as a source-recording
stratum, not as a clinician-interpretable primary exposure.

**Study design remains:** Candidate I63-coded indexed
inpatient records at ages definitely 18–50, with binary
recorded CPT14 imaging capture. This does **not** establish
performed imaging, validated ischemic stroke diagnosis or
disparities in appropriate care.

## Frozen checkpoints: what is and is not available

Source member sets processed by Step62:
`diagnosis.csv`, `encounter.csv`, `patient.csv`, and
`procedure.csv`. **There is no medication.csv** in the
verified source archive contract.

- Step62 keeps indexed I63 encounters, patient demographic
  fields, and only the **14 imaging CPT codes** as
  indexed-IMP patient-level imaging categories.
- Step63 keeps the index encounter, selected EMER/IMP
  encounter metadata and conservative preceding ED links.
- Step68 `capture.flags` stores one patient/cohort/
  modality bitmask for **CT_HEAD, CTA_HEAD, CTA_NECK,
  MRI_BRAIN, MRA_HEAD, MRA_NECK** under fixed temporal
  /encounter definitions. These have no treatment flags.
- Step68 `code_profile` stores **source-row frequencies**
  for procedure codes by system, exact code, rough scope,
  service year and P. It does not retain patient-level
  non-CPT14 diagnosis/procedure flags, nor a treatment
  marker or CPT overlap at the patient level.
  A candidate thrombolysis/thrombectomy code may
  be represented in the private source code frequency
  inventory, but counts are not treatment patients.
- Step71 patient-level-recorded demographic categories
  and Step69 modality/encounter grouped aggregations can
  be recomputed from frozen checkpoint SQLite without
  reopening the raw 993,025,015 procedure-source rows.
  Step72/73 also contain grouped exploratory demographic
  models, but these cannot resolve unmeasured site mix.

**Consequence:** The proposed thrombolysis/thrombectomy
imaging-capture benchmark **cannot be calculated from
the currently frozen patient flags**. It would require
reconstructing a clinically reviewed patient-level
treatment cohort from additional source data, or a
different accessible medication/procedure record source.
We should NOT authorize another billion-row source pass
until the simpler feasibility gate and treatment codebook
assessment justify it. Treatment-record presence is
itself potentially incomplete and subject to coding
selection: this would be an *internal positive-control
cohort*, not criterion validity, and it would not
produce a universal lower bound for imaging sensitivity.

## Immediate read-only Step81 feasibility output

`scripts/step81_frozen_modality_demographic_gate.py`:

1. Rechecks Step62/63/68 source signatures and frozen
   Step68 aggregate totals.
2. Uses the existing Step71 conservative race/ethnicity
   label dictionary. Prints the proportion that is
   **explicitly unknown**, and the proportion that is
   **unknown plus other/unmapped**, separately. Do not
   equate other/unmapped with verified missingness, nor
   compare directly with old Diamond V7 missingness
   because the cohorts and coding definitions differ.
3. Uses Step69 patient-level modality-group aggregates.
   Prints nominal 95% **Wilson intervals for marginal
   proportions** across six modalities and four
   separate encounter definitions, by P.
   These are not HCO-cluster robust and cannot
   establish uncertainty on between-definition
   or between-group differences.
4. Withholds any displayed modality/missingness
   proportion if either its event or complement
   count is under 11. This remains an internal
   exploratory release gate, not institutionally
   certified cross-table suppression.
5. Provides no patient IDs, free-text demographic
   values or exact source-observed treatment codes.

It never rescans a procedure ZIP, exports patient-level
records, or modifies the frozen Step62–80 packages.

## Run on the investigator's workstation

```bash
(
  set -e
  git pull --ff-only origin analysis-rebuild-phase1-audit
  python -m py_compile scripts/step81_frozen_modality_demographic_gate.py
  python -m pytest -q tests/test_step81_frozen_modality_demographic_gate.py
  python -m pytest -q
  python scripts/step81_frozen_modality_demographic_gate.py
)
```

Send **TERMINAL OUTPUT ONLY**. This is private
internal exploratory analysis; do not email,
upload raw databases or images, or circulate
numerical tables outside the approved setting.

## Go/no-go decision

- If race/ethnicity are largely unknown/unmapped,
  keep them descriptive or internal; focus the paper
  on encounter linkage and measurement and avoid
  an unsupported disparity analysis.
- If demographic completeness and subgroup support
  are adequate, pursue the combined **measurement
  sensitivity of apparent sex/race associations**
  while using consistent denominators and measured
  ambiguity controls; validate demographic mappings.
- After the gate, decide whether the available
  Step63 EMER/IMP metadata could ground a small
  encounter-type sensitivity or whether all
  other-encounter imaging event kinds are
  fundamentally unobservable without a new pass.
- Treatment positive control: first create
  a **publicly vetted year-specific
  thrombolysis/thrombectomy codebook**, confirm
  those codes occur at sufficiently useful levels
  within the existing local exact-code profile,
  assess whether source procedure systems and
  dates support accurate treatment timing, then
  explicitly justify any new targeted clinical
  read. A published stroke imaging rate offers
  context, not validation of imaging receipt
  in this specific research network.
- No manuscript or supplemental results
  should claim that lacking CPT14 implies
  no clinical imaging, that P identifies
  institutions, or that adjusted sex/race
  code-capture contrasts prove care disparities.

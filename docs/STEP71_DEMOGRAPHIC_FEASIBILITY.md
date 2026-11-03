# Step71: Read-only demographic completeness and CPT14 outcome-feasibility audit

**Status (2026-10-20):** Completed successfully on the investigator's
authorized workstation: the Step71 fabricated tests and full
repository test suite passed, and the read-only demographic
feasibility audit returned for both cohorts with Step68 counts
reconciled. **No new source ZIP scans or patient-data exports.**
Its categorical mapping shows substantial unknown/unmapped race
and ethnicity as well as marked demographic variation in P
label, encounter-key quarantine and same-day code capture.
Unadjusted contrasts are NOT clinical imaging disparities.
See [Step72 exploratory demographic models](STEP72_EXPLORATORY_DEMOGRAPHIC_MODELS.md)
for the next locally executed, model-based robustness screen.
Private source-derived counts remain local-only.

## Why

Step70 completed successfully. In the uniform ages 18-50 cohort,
the crude `P=1` versus `P=0` same-day cross-encounter CPT14-coded
imaging contrast changed sign after common-weight standardization
to year and patient-level encounter quarantine. The same direction
held in the historical age-eligibility sensitivity.

Therefore, before fitting sex/race/ethnicity disparities models,
establish whether the available demographic fields are complete,
whether observed outcome definition differences are strongly
associated with demographic distributions, and how this differs
between patients with and without quarantined encounter keys.

## Step71 analysis scope

`scripts/step71_demographic_capture_feasibility.py` reads, read-only:

- Step62 `idx`, `person` and frozen `image`, which retain the
  source sex, race, ethnicity, birth year, broad ICD-10-CM I63
  admission candidates, P status and original same-IMP CPT14 imaging.
- Step63 frozen `idx` and patient-level `ambiguous` encounter
  quarantine (ANY ambiguous EMER/IMP key; not necessarily index).
- Step68 completed per-patient/per-modality CPT14 flags, and the
  independently frozen aggregate JSON.

It verifies Step62/63 database consistency, Step68 frozen
source fingerprints and completion, and EXACT reconciliation of
primary cohort size, inpatient CPT14, other-encounter same-day CPT14
and unique-ED CPT14 patient counts. It additionally checks
that sex, race, ethnicity, P, calendar-year, and quarantine
strata partition the indexed cohort exactly without missing
or duplicated patient memberships.

For **both overlapping cohort definitions**, the script calculates:

- `n`, share with I63 P label, share with ANY quarantined
  EMER/IMP encounter key, and absence/unrecognized proportions
  for sex, race, ethnicity.
- Any of 14 CPT neuroimaging codes on the frozen indexed IMP.
- Advanced (MRI brain, CTA head/neck, MRA head/neck) CPT14 codes
  on that IMP.
- Exploratory same-day coded-capture for any CPT14 and advanced
  codes on index IMP **OR another encounter** on index calendar day.
- Modality-specific inpatient code counts, available internally
  for reconciliation, not printed as unreviewed care disparities.
- Primary cohort exploratory rates by demographic category
  separately for `P=0` / `P=1` and for no-ambiguous
  / any-ambiguous patient groups.

The **sex/race/ethnicity labels are conservatively harmonized**:
only exact known source-text variants map to broad standardized
labels. Blank, unknown and explicitly missing map to
`UNKNOWN_MISSING`; unrecognized or other codes map to
`OTHER_OR_UNMAPPED`. No free-text source labels are emitted.
Do not infer non-Hispanic ethnicity from race or impute blanks.
Raw categories are retained only in the existing private Step62 DB,
not in printed output. High `OTHER_OR_UNMAPPED` rates
would indicate that source dictionary harmonization is necessary
before demographic regression.

All printed strata with fewer than 11 patient-cohort memberships
are suppressed. These safety features do **not** imply that
the printed aggregates have institutional release approval.

The two cohorts substantially overlap; their counts must NEVER
be added. The uniform 18-50 cohort is preferred for primary
sex comparisons because historical older eligibility limits
vary by sex.

## What this DOES NOT do

- No final statistical association estimate, p-value, adjusted
  disparity model, site/HCO adjustment or causal claim.
- No reclassification of SNOMED, HCPCS or ICD-10-PCS B-prefixed
  source rows as imaging without exact-year clinical coding review.
- No claim that another-encounter same-day CPT14 represents
  a scan performed in the index hospital, or that missing
  CPT indicates absent clinical imaging.
- No change to Steps62/63/68 local databases and no original
  clinical `procedure.csv` rescan.

## Single local execution

```bash
(
  set -e
  git pull --ff-only origin analysis-rebuild-phase1-audit
  python -m py_compile scripts/step71_demographic_capture_feasibility.py
  python -m pytest -q tests/test_step71_demographic_capture_feasibility.py
  python -m pytest -q
  python scripts/step71_demographic_capture_feasibility.py
)
```

Tests must pass before the read-only audit launches.
If a test fails, STOP and share its terminal traceback.

**Next handoff is TERMINAL OUTPUT ONLY**.
Do NOT upload ZIPs, SQLite, or private aggregate JSON.

## Decision after outcome-feasibility output

1. If source demographic labels are largely unrecognized,
   first review the authorized source vocabulary locally,
   then update the explicit recoding dictionary with tests.
   Do not call `OTHER_OR_UNMAPPED` a race/ethnicity.
2. Compare whether sex, race and ethnicity have different
   P/quarantine compositions and outcome-definition sensitivity,
   with missing/unknown kept as explicit categories.
3. Predeclare a primary **documented code-capture** outcome and
   site-coverage limitation, including original same-IMP CPT14.
   The other-encounter day0 measure remains a clearly labeled
   sensitivity, especially due to Step70 source-quality reversals.
4. Exact ICD-10-PCS imaging mappings and year applicability remain
   a separate official CMS/literature task, NOT inferred from source
   B-prefix frequency counts. The official historical CMS files
   are catalogued at:
   https://www.cms.gov/medicare/coding-billing/icd-10-codes
   (fiscal coding versions change October 1 and may have interim
   update dates).
5. Consider descriptive and ultimately adjusted models only after
   confirming demographic labels and freezing the outcome
   definition. HCO coding heterogeneity cannot be adjusted away
   without a validated HCO variable; acknowledge that as a
   limitation and interpret associations cautiously.

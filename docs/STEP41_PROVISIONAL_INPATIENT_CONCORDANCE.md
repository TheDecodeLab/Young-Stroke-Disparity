# Step 41: Provisional inpatient encounter technical concordance pilot

**Status:** BOUNDED TECHNICAL FEASIBILITY ONLY. Not a clinical result.

The Step 39 private worksheet identifies one encounter `type` whose
reference description and lexical suggestion correspond to inpatient
care. Step 40 showed that none of the worksheet's reviewer-decision cells
was completed at the time it was run. This code uses the lexical
**inpatient candidate** solely for a technical join feasibility check.
It does not overwrite review decisions, grant clinical sign-off, or
declare an eligible inpatient ischemic stroke cohort.

## Why this is the next substantive check

The Research Network export has patient IDs and encounter IDs in its
encounter, diagnosis, and procedure tables. Previously observed matching
patient IDs were encouraging, but separate nonrandom prefixes cannot
establish whether inpatient encounters actually have valid linked
ischemic stroke diagnoses and matching imaging procedure codes.

This script checks that directly **within the same bounded encounter
prefix**. It is still a nonrandom convenience sample, so it cannot
estimate clinical utilization or population linkage rates.

## What the script reads

1. Three **independent first-50,000-row** prefixes, one each from
   `encounter.csv`, `diagnosis.csv`, and `procedure.csv`;
   the cap must match Step 37 and cannot exceed 200,000 rows per table
2. The already generated Step 36/37 local aggregate JSONs
3. The **private local** Step 39 codebook worksheet (read-only), to
   identify lexical inpatient candidate types without committing the
   actual code list

It does not read `patient.csv`, scan the billion-row source tables,
extract the source ZIP, or save row-level data.

Identifiers are held only in memory for the pilot; emitted reports
contain **only aggregate technical counts** (small counts 1-10
suppressed). No raw encounter-type codes, clinical procedure codes,
patient/encounter/source identifiers, literal dates, or individual
records appear in the report.

The report counts:

- The number of distinct sampled provisional inpatient encounter IDs
- Diagnoses and procedures that share both encounter ID **and patient ID**
- Matching ICD-10-CM ischemic stroke (I63) and selected imaging CPT codes
  **within sampled candidate inpatient encounters**
- Whether both signal types appear in the same sampled encounter
- Whether selected imaging CPT dates fall within +/- 7 days of encounter
  start, using unambiguous `YYYYMMDD` or ISO dates
- The same technical signals for sampled encounters starting in
  2018-2019, where the date is parseable

**Important:** The selected CPT14 code set is not a full imaging
ascertainment scheme and may include CT, CTA, MRI, and MRA. No
diagnosis or procedure nonmatch can be interpreted as an absence of
care because the input event prefixes are truncated. A recorded
procedure is not evidence of completed imaging.

## Run locally in the cloned repository

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step41_provisional_inpatient_concordance.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip"
```

Generated files **only inside the cloned repo's ignored
`results/phase1/` directory**:

```text
step41_imp_encounter_concordance_pilot.json
step41_imp_encounter_concordance_pilot_REVIEW.zip
```

Both are owner-only permissions (0600). The review ZIP contains only
the aggregate JSON. Before sharing, the investigator must verify
institutional permission and complementary-disclosure safety. Never
commit any generated report, raw ZIP, or private worksheet to GitHub.

## How this affects the scientific protocol

This is not yet an imaging-disparities cohort. The final design must
still establish (a) observed inpatient admission semantics, (b)
diagnosis position and ischemic stroke index, (c) age eligibility,
(d) MRI, CTA, MRA code ascertainment and timing, (e) race/ethnicity
completeness and confounding, and (f) institutional data authorization.

The original clinical neuroimaging-disparities question remains the
objective. The next substantive analysis should be an **efficient,
imaging-independent, encounter-linked young stroke cohort** only
after verifying the above study definitions. Until then, no adjusted
clinical disparity model is supported by the pilot.

This repository is public and its history contains unresolved legacy
patient-level data governance issues. Keep PR #1 draft and unmerged.

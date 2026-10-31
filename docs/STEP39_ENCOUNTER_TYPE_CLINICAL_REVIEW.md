# Step 39: Clinical review of Research Network encounter-type terminology

**Status:** private codebook worksheet; clinical interpretation is NOT yet approved.
This step follows the uploaded Step 38 report. The source-side Step 38 report showed that all encountered type codes
matched entries in the `Encounter Type` reference vocabulary, but at least
one terminology-matched type could not be interpreted from keywords.
The exact nonrandom-prefix category counts remain solely in the private
Step 38 report, not this public documentation.

## Goal

Provide the clinical/data-steward reviewer with exactly the original
reference **code and description** for each encountered type, along with the
nonrandom prefix count and a machine-suggested lexical candidate category.
These five codes must be assessed before any hospital-based stroke cohort
or disparity model is defined.

## Run on the study workstation

From the cloned repository on branch `analysis-rebuild-phase1-audit`:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step39_encounter_type_clinical_review.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip"
```

The input TriNetX source archive stays outside the repository at its existing
location; it is opened read-only. Step 39 reads at most 50,000 rows of
`encounter.csv` and makes one streaming pass over the smaller terminology
reference table. It does not scan the billion-row diagnosis or procedure
tables. It uses the existing Step 36/37/38 aggregate reports to verify
source signatures, lineage, and prefix/reference row totals.

## Files created: all within the cloned repository

```text
Young-Stroke-Disparity/results/phase1/
  step39_encounter_type_clinical_review_LOCAL_ONLY.csv
  step39_encounter_type_review_status.json
  step39_encounter_type_review_status_UPLOAD_ONLY.zip
```

All paths are Git-ignored. Generated files are owner-only (0600).
The script rejects output paths outside `results/phase1/`. It never exports
patient/encounter/source identifiers or individual dates. Raw type codes,
reference descriptions, and per-code nonrandom prefix counts appear **only**
in the local worksheet, **not** in the ZIP or GitHub.

**Do not upload or commit the local CSV worksheet** unless the data steward
explicitly authorizes it. Share only the aggregate-only ZIP after reviewing
its contents and checking the institutional data-use restrictions.

## How to use the local worksheet

Read the five type codes and their `reference_description` and
`reference_path` columns. Ask a stroke clinician and/or the TriNetX
data steward to determine the exact meaning of each code, including whether
it represents an **inpatient admission**, emergency encounter, observation,
outpatient care, virtual encounter, other encounter, or unknown.

The `lexical_candidate_NOT_APPROVED` field is **not a clinical classification**.
The two trailing `clinician_decision_LEAVE_BLANK` and
`reviewer_notes_LEAVE_BLANK` columns are intended for manual review.
The manuscript's original inpatient target is not defensible merely because
the word "inpatient" appears in a reference description.

Before approval, explicitly check whether observation/ED-to-inpatient
transfers are single or multiple encounter records, whether `encounter_id`
is unique across patients/HCOs, what `source_id` means in each event
table, and whether the diagnosis/procedure record join reflects a shared
clinical episode. These need further private technical checks and clinical
review before a full reconstruction.

**Important:** rerunning Step 39 regenerates the worksheet. If you edit the
review columns, keep the annotated version as a different *local-only*
filename within `results/phase1/` before rerunning it.

## Go/no-go for a larger analysis

Proceed to design a **single** well-controlled private Research Network
reconstruction only after the investigators approve an inpatient
index definition, candidate diagnosis code list, age rules, encounter link
scope, procedures/imaging codebook, observation period, data-use restrictions,
and plans for missing race/ethnicity and other confounders.

No STEP 39 output is evidence of an imaging disparity. Even correctly
categorized encounter types do not establish complete capture of MRI,
CTA or MRA, nor do they establish national representativeness.

The linked GitHub PR remains draft and unmerged because the public repository's
historical clinical-data disclosure issue remains unresolved.

# Step 40: Review the encounter type decisions safely

**Status: clinical approval pending.** The investigator supplied the Step 39
aggregate-only review-status ZIP. It confirmed that all five observed
encounter-type codes had reference descriptions, with no competing
descriptions. Four type definitions were **not unequivocally inpatient**.
This status report confirms successful worksheet generation, **not** that
any clinician has approved the encounter classification.

Step 40 makes the manual review reproducible without exporting the codes.

## Before running

Open this **local-only** file in the repository's ignored results folder:

`results/phase1/step39_encounter_type_clinical_review_LOCAL_ONLY.csv`

Review the five rows with an authorized stroke clinician and/or TriNetX
data steward. Do not assume the original automated lexical candidates
are correct. In `clinician_decision_LEAVE_BLANK`, enter exactly one of:

- `inpatient` – confirmed inpatient encounter type
- `emergency` – emergency-department encounter
- `observation` – observation status (not assumed inpatient)
- `outpatient` – clinic or other outpatient encounter
- `virtual` – remote/telehealth encounter
- `other` – known other encounter type, described in private notes
- `unknown` – no defensible clinical classification yet

Leave the decision cell **empty if not reviewed**. Put the clinical
rationale, source definition, and any uncertainties in
`reviewer_notes_LEAVE_BLANK`. These private review notes never appear
in the upload ZIP or public GitHub.

**Important:** Step 39 regenerates its worksheet and would overwrite
edits. Do not rerun Step 39 after editing the file unless you first save
a private backup *within* `results/phase1/`. Step 40 reads the
worksheet without modifying it.

The reviewer still must decide whether an inpatient-type value corresponds
to a completed hospital admission, how transfers and emergency/observation
records are represented, and whether `encounter_id` is scoped consistently
across patients and source systems. A matching label alone does not
establish the manuscript's hospitalized-stroke cohort.

## Run Step 40

From the cloned repo:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step40_encounter_type_review_validation.py
```

Step 40 uses **only** the already-generated, local worksheet and Step 39
aggregate status. It does **not** read the source clinical ZIP,
large encounter/procedure/diagnosis tables, or any additional rows.

Generated files remain **only** inside the cloned repository's
Git-ignored `results/phase1/`:

```text
step40_encounter_type_review_validation.json
step40_encounter_type_review_validation_REVIEW.zip
```

The report contains only overall review-completeness **booleans** and
a count of codebook rows. It contains no raw encounter type codes,
terminology descriptions, individual code classifications, reviewer notes,
patient IDs, or clinical events. Both files are owner-only (0600).

**The script never sets `inpatient_definitions_clinically_approved=true`
or `ready_for_full_linked_stroke_cohort_extraction=true`.** Even if all
five rows have entries, clinical sign-off and independent assessment of
episode joins, inpatient status, time window, and procedure ascertainment
remain required.

## What to share

After local disclosure review, you may upload
`step40_encounter_type_review_validation_REVIEW.zip`. Do not upload
the five-row worksheet, notes, or original data ZIP without institutional
authorization. The report is a workflow-status record, **not** a study
result or a substitute for coauthor approval.

We will plan one efficient private, encounter-linked young-stroke
reconstruction **only after** the inpatient and imaging definitions and
source data authorization have been addressed.

This repository's draft PR remains unmerged because public Git history
contains unresolved historical TriNetX data-disclosure concerns.

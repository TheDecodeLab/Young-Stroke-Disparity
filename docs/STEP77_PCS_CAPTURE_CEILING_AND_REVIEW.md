# Step77: PCS patient-gain upper bound and restricted clinical code review

**Status:** Read-only implementation and fabricated synthetic tests committed.
Investigator workstation execution pending. No new procedure source scan,
new demographic model, patient reclassification or public result export.

## Scientific reason for this gate

The completed Step76 source discovery generated a restricted exact-code
queue of possible CNS/upper-artery CT/MR ICD-10-PCS procedures, using
already captured code-profile row frequencies and official CMS titles.
The queue includes overlapping age cohorts and potentially repeated
procedures; it is NOT a count of uniquely imaged patients.

The fact that all Step76 candidates pass an automated anatomy-phrase
screen is **not independent clinical validation**: Step74 already
preselected titles using related anatomical terms. Exact body part,
contrast and procedure method still require independent clinical/code
adjudication. Official year-neighbor title presence is not equivalent
to validity on an exact inpatient discharge date.

## Analytic decision rule (no new source extraction)

For the uniform age 18–50 cohort, obtain the already-frozen
`P=0` and `P=1` index-IMP patient denominators and inpatient-only
CPT14 patient numerators from Step68. Separately, sum *review-only
index-IMP PCS source-row counts* by P from completed Step74 across
both overlapping cohorts.

For each P group compute:

```text
absolute_maximum_new_imaged_patients =
    min(frozen_n - CPT14_index_patients,
        review_only_index_PCS_source_rows_across_both_cohorts)

maximum_possible_recorded_index_capture =
    (CPT14_index_patients + absolute_maximum_new_imaged_patients)
    / frozen_n
```

This deliberately unrealistic upper bound assumes every candidate
source row is a clinically correct, unique and previously CPT14-negative
patient of the **one** primary cohort. It is necessarily at least as
large as any actual patient-level incremental gain from ONLY the
already discovered PCS codes.

The completed Step76/Step74 aggregates show qualitatively that
even this maximum P=1 gain **cannot eliminate** the original
P0–P1 coded-capture gap. The exact source-derived numerical
bound is recomputed **locally** by Step77; do NOT commit the
private source results to the repository. This is a measurement
ceiling, not a causal hypothesis test, a radiology outcome or
an inference about source coding systems not yet reviewed.

## Script and clinical worksheet

`scripts/step77_pcs_gain_ceiling_and_clinical_review.py` reads only
the completed local, private Step68, Step74 and Step76 JSON reports,
checks frozen reporting policies and source-row reconciliation, and
prints the mathematical ceiling in the authorized terminal.

It creates an atomic, non-overwriting **LOCAL ONLY** clinician-review
CSV containing the exact observed PCS candidate codes and official
title variants, with all substantive decisions left `PENDING`:

- Verify full anatomic target and method; distinguish relevant
  neurovascular anatomy from unrelated arteries/brain structures.
- Decide if contrast/angiographic classification can actually
  be inferred from the official title/code.
- Verify official fiscal-year and discharge-date effective periods.
- Record include/exclude decision, clinical rationale, reviewer
  and date before freezing a year-valid codebook.

The worksheet contains no patient IDs or patient-level data, but the
fact that each public code is **observed in private source records**
still makes the list restricted source-derived evidence. Do not
commit, email or otherwise release the observed-code worksheet
without applicable institutional authorization. A public-only
clinical codebook may later be authored without source-frequency
or observed-in-private labels.

Private local worksheet path (not for upload):

`results/phase1/full_reconstruction_private/step77_decision_gate_private/step77_clinical_code_review_LOCAL_ONLY.csv`

## One bundled, fail-fast local run

```bash
(
  set -e
  git pull --ff-only origin analysis-rebuild-phase1-audit
  python -m py_compile scripts/step77_pcs_gain_ceiling_and_clinical_review.py
  python -m pytest -q tests/test_step77_pcs_gain_ceiling_and_clinical_review.py
  python -m pytest -q
  python scripts/step77_pcs_gain_ceiling_and_clinical_review.py
)
```

**Handoff: TERMINAL OUTPUT ONLY.** No ZIP, SQLite, private CSV/JSON,
patient data or original procedure source files. This Step77
does not re-read the raw ~1-billion-row procedure table.

## After the run

Do not launch another full procedure scan or additional demographic
models on the strength of review-only source-code frequencies.
P=0 combines nonprincipal/unmarked diagnosis indicators rather than
clinical confirmation of secondary ischemic stroke. True scan
performance, stroke severity, HCO/episode attribution, and
source coding differences remain unverified.

The next substantive prerequisite is independent clinical
adjudication of the restricted code list and a publicly defensible
year-specific codebook. Only then consider whether a targeted
patient-level source pass could meaningfully improve outcome
measurement beyond original CPT14 and the existing encounter
sensitivity analyses.

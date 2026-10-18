# Phase 1 decision after Step 44: full-cohort reconstruction specification (draft)

> **Superseded on 2026-10-17 for code and ED/inpatient definitions.**
> See [Step48 diagnosis/ED bridge protocol](STEP48_STROKE_CODES_ED_TO_INPATIENT_PROTOCOL.md).
> The initial Step45 full-scan CLI is now intentionally disabled because it
> would undercapture ED-before-inpatient imaging and ignore the investigator's
> additional stroke-code families. The historical 18–50 and sex-specific
> 18–52/18–54 co-primary AGE definitions remain unchanged.
> Treat the sections below as the earlier conservative plan, not an
> instruction to execute or the final source-wide phenotype.
>
**Status:** Technical plan, not executed, not clinically approved. This document
defines the next meaningful data-analysis step without creating another
nonrepresentative file-prefix pilot.

## Evidence and decision from Steps 36–44

- Research Network has an encounter table, encounter IDs in diagnosis and
  procedure records, and compact `YYYYMMDD` date strings.
- In a bounded *nonrandom* pilot, patient IDs were consistent among observed
  encounter joins; differences between event and encounter `source_id`
  were observed and their meaning is not yet validated.
- The source terminology identifies an `IMP` inpatient-encounter candidate.
  The local five-code worksheet and inpatient interpretation still require
  explicit investigator/data-steward review.
- Independently truncated encounter/diagnosis/procedure prefixes **cannot**
  estimate imaging utilization or true linked encounter coverage.
- The reference-only neuroimaging discovery found a much larger unvalidated
  code vocabulary than the historical CPT set. A description-only audit of
  the originally ambiguous head/neck entries found **no additional
  description-specific anatomy assignments**. That category must remain
  under human review; do not apply another keyword classifier as if it
  resolved the medical concept.
- No source-wide, age/sex/race-specific imaging outcome or disparities
  result has been demonstrated.

**Decision:** Stop the repeated prefix and terminology triage sequence.
Prepare one predeclared, data-governed encounter-linked extraction. The
next clinical-data pass must use the complete source tables and must not
silently treat missing procedure matches as absence of care.

## Target scientific question and estimand

Among *eligible young adults hospitalized with ischemic stroke* in
calendar years 2018–2019 in the available Research Network:

- Describe the proportion **with a recorded brain MRI**, **with
  recorded CTA head and/or neck**, **with recorded MRA head and/or neck**,
  **with any recorded vascular imaging**, and **without recorded MRI or
  vascular imaging**, by sex and race.
- Report absolute differences (percentage points) and confidence
  intervals, not just p values or odds ratios.
- Reserve `receipt` or `completed imaging` for codes with documented
  performed-procedure meaning. If that cannot be established, use
  `recorded procedure code` in tables and conclusions.
- A disparity claim requires defensible clinical confounding, missingness,
  site/capture assessment, and sensitivity analyses. The primary
  descriptive comparison is variation in documented imaging.

## Predeclared index and eligibility (NOT YET APPROVED)

1. **Diagnosis-based candidate identification:** complete scan of
   `diagnosis.csv` for ICD-10-CM `I63.*` in 2018 or 2019, retaining
   patient ID, encounter ID, event date, principal indicator and relevant
   source metadata in a **private local** stage. Do not decide eligibility
   from imaging. Determine actual values/meaning of
   `principal_diagnosis_indicator` before defining principal stroke.
   Evaluate missing encounter IDs separately.
2. **Hospital encounter validation:** complete scan of
   `encounter.csv` matching candidate patient+encounter pairs.
   `IMP` is a *provisional* candidate; require clinical/data-steward
   confirmation that it represents an inpatient hospital admission.
   Compare dates and inpatient stay boundaries. Check uniqueness of
   encounter IDs across patients and sites; do not automatically require
   `source_id` to agree across event and encounter tables before learning
   its provenance semantics.
3. **Demographics and TWO CO-PRIMARY AGE DEFINITIONS (user-confirmed):**
   complete scan of `patient.csv` for matched patients, preserving
   sex, race/ethnicity, YOB and missingness. Analyze **both primary
   cohorts in parallel**: (A) age 18–50 inclusive regardless of sex;
   (B) age ≥18 and ≤52 for men or ≤54 for women (original study rule).
   Neither is secondary. Present both denominators, imaging outcomes,
   and sex/race stratification explicitly; do not pool results or treat
   the cohorts as independent. Patients may enter both definitions.
   With year-of-birth only, actual age at admission is interval-censored
   by up to one year: use conservative definitely-in-range rules in the
   primary extracts and report ambiguous boundary ages separately.
   Cohort B cannot classify a person with unknown/nonbinary sex into a
   sex-specific threshold without a clinician-approved policy; track
   this as ineligible/unknown rather than imputing sex.
4. **Repeated events:** define one index hospitalization per patient
   (proposed earliest eligible 2018–19 admission) with a stated policy for
   overlapping/transfer encounters. Do not double-count people.
5. **Procedure outcomes:** one complete pass over `procedure.csv` to
   find only events matching the finalized index patients/encounters
   and codebook. Same-encounter, within-stay outcomes are preferred;
   a ±7-day patient-level window is a clearly labeled sensitivity
   analysis, not equivalent to inpatient receipt. Assess code
   completeness and site effects separately.
6. **Analysis:** no inferential sex/race models before comparing record
   completeness by site and group. When justifiable, adjust for
   individual clinical risk factors (e.g., hypertension, diabetes,
   hyperlipidemia, smoking) and age/site. Avoid automatic substitution
   of CHA2DS2-VASc for confounders. Preserve race-missing as an explicit
   category in descriptive analyses, and report complete-case bias
   concerns when fitting race models.

## Imaging definitions to freeze before the procedure pass

**Separate procedure concepts and anatomical targets.**

- Brain MRI: conventional MRI brain, not MRA.
- CTA head and CTA neck: separate, and an optional head/neck composite.
- MRA head and MRA neck: separate, and an optional head/neck composite.
- CT head: descriptive baseline comparator, not vascular imaging and
  not an 'advanced neuroimaging' outcome.
- Any vascular imaging = CTA head/neck or MRA head/neck under *approved*
  codes. MRI brain and vascular imaging are separate outcome families.

The historical 14 CPT code anchors can serve as a **clearly labeled
high-specificity exploratory sensitivity definition**, subject to
rechecking each code. They are **not** an approved primary full-source
codebook. Broad SNOMED/HCPCS/ICD terminology matches are candidates for
clinical review only; the mixed-anatomy entries must not be
forced into a single category.

Record code-system/code pairs, description, modality, anatomy,
encounter linkage interpretation, 'ordered' vs 'performed' meaning,
approval reviewer/date, and known limits. Unreviewed concepts must
not silently enter numerator definitions.

## Engineering architecture: one controlled full scan per large table

The source Research Network ZIP remains outside the clone, read only.
Implement a local, disk-backed, restart-safe staged pipeline using
Python/DuckDB or SQLite **inside the cloned repository's ignored
`results/phase1/` directory only**. Do not load entire billion-row
tables into memory.

Predeclared pass order:

1. One streaming pass over `diagnosis.csv`; retain only eligible
   I63 candidate rows and aggregate coding/quality diagnostics.
2. One streaming pass over `encounter.csv` and indexed join on the
   restricted candidate keyset; verify inpatient-encounter validity,
   missing/colliding keys and date relationships.
3. One pass over `patient.csv` for candidate demographics and age
   eligibility; preserve sex/race missingness.
4. One streaming pass over `procedure.csv` with a **reviewed, frozen**
   codebook and keyset; calculate event flags and timing in the private
   stage without exporting record-level rows.
5. Generate disclosure-reviewed, suppression-protected aggregated
   denominators/numerators, overlap counts, quality gates and audit
   metadata **only** under `results/phase1/`. Do not commit, publicly
   push, or upload patient-level stages.

The implementation must estimate local storage and time, log one-time
per-table pass completion without logging identifiers, support cleanup
of partial data, never claim an incomplete pass is source-wide, and
be synthetically tested with deliberately shuffled cross-table rows,
duplicate encounters, conflicting patient/source IDs, missing principal
indicators, competing admissions and absent imaging. Avoid publication
of sensitive derived patient rows, even in Git history.

## Explicit approval/gating checklist

**Not yet approved**, and not inferable from Steps 36–44:

- Institutional owner/data-use approval for this full-source local
  processing and approved handling of derived row-level stages.
- Inpatient `IMP` mapping, principal I63 flag semantics, transfer and
  collision rules reviewed by the study clinical/data team.
- Both co-primary age definitions and treatment of YOB uncertainty.
- Primary imaging codebook and procedure performed-vs-ordered meaning,
  including CPT and relevant non-CPT systems.
- Reporting disclosure suppression and standards for missing race/site
  confounding.

This specification is a blueprint, **not** an instruction to run a
multi-billion-row scan now. Do not treat missing unreviewed codes or
missing procedure joins as proof of no imaging. The public repository
still has unresolved historical patient-level data governance exposure.
Keep PR #1 **draft and unmerged** until institutionally resolved.

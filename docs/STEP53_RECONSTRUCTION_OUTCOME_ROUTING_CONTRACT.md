# Step 53: Reconstruction outcome-routing contract (synthetic reference only)

**Investigator decision validated on the workstation at commit `557a8ab`: 415 passing tests, three unchanged warnings.** Same-inpatient-encounter imaging is the **primary outcome (A)**. ED-inclusive imaging is an **unverified date-only sensitivity (B)**. ED max-gap 0, 1, and 2 calendar days are secondary window sensitivities. Both previously approved co-primary age populations remain independent overlapping analyses.

**Status of Step53:** pure Python reference logic and synthetic tests; NOT a production Research Network extractor, not a clinical codebook validation, not a database schema migration, and not permission to read any real clinical records. The superseded Step45 real-scan CLI remains explicitly **DISABLED**.

## Scientific definitions and units

The analysis unit is one **preselected index hospitalized stroke encounter per person per age cohort**. Index selection must come from age/stroke/inpatient eligibility without inspecting imaging. Apply the same index policy independently to `uniform_18_50` and `original_sex_specific_18_52_54`; a person may appear in both but must not be pooled as independent observations.

- **A, primary:** a reviewed recorded-performed imaging category with the **exact same `patient_id` and `encounter_id`** as that person's index `IMP` encounter and a procedure date within the encounter's reported start/end calendar dates. An unknown or invalid inpatient end date renders within-stay capture **unassessable**, not proof of no imaging.
- **B, provisional sensitivity:** A plus categories from one **reciprocally unique date-adjacent** `EMER` encounter for the same patient, with `EMER.end_date` on admission day or the prior calendar day. The ED procedure must also fall within the ED encounter and no later than the recorded inpatient start day. Such records are **not validated transfers or confirmed same-hospital procedures**. ED matches are never used to determine hospitalized stroke eligibility.
- **C, time-window sensitivities:** compare B under max gaps of 0, 1 and 2 *calendar* days. Wider windows may trigger more competing ED candidates; **B counts need not rise monotonically**, because ambiguous matches are excluded.
- **Modality:** MRI brain, CTA head, CTA neck, MRA head, MRA neck; CT head as comparator. Deduplicate records at patient + index cohort + analysis definition + imaging category rather than treating procedures as unique patients. Report each modality, as well as clinically defined composites only after review of those composites.

No matching uses unverified `source_id`. `patient_id` may or may not have stable multi-HCO meaning. Date-only matching cannot establish ED-to-IP transfer; ambiguous multiple ED and multiple IP cases must remain unresolved, including non-index inpatient encounters. Stage data-quality exclusions and missingness by cohort, sex and race before inferring disparities.

## Testable reference logic

- [Pure assembler](../scripts/step53_outcome_reference_assembler.py): `assemble_outcome_reference(index_admissions, all_inpatient_encounters, all_emergency_encounters, imaging_events)`.
- [Synthetic-only tests](../tests/test_step53_outcome_reference_assembler.py): prevent ED capture in A; test date windows, non-index competing admissions, imaging dates outside visit bounds, missing end dates, duplicate codes, two-cohort overlap, and unreviewed event rejection.
- Every provided imaging event must explicitly have `codebook_reviewed_performed: True` and one of the **known reference category names**. This is only a **caller-provided assertion**, not independent codebook verification. The production pipeline must load a truly reviewer-approved codebook, match source code system + code + performed semantics, and record its provenance before it can label events as reviewed.
- This module accepts **preselected index rows** and in-memory normalized events, not raw CSV files. It **does not validate ICD coding**, determine principal diagnosis, select index admissions, handle full-scale memory/performance, or run models. It does not read ZIPs, SQLite, clinical records or approval files and produces no persistent output. Its per-index in-memory result includes identifiers and **must never be copied to GitHub, external services or ordinary shared outputs**.

## Required design for a future approved, bounded-memory full reconstruction

1. **Source/provenance and approvals:** document authorized purpose, encrypted storage, exact ZIP and Step36 signature, cohort tables, study period, data steward review, and the approved procedures codebook. Explicitly approve alternate outcome A/B logic and cross-HCO ID scope; keep all private row-level stages in `results/phase1/full_reconstruction_private/`. No current approval is implied by investigator agreement.
2. **Diagnosis:** on a future *authorized* full-file pass, stage 2018–19 ischemic stroke candidate diagnoses using reviewed ICD-10 I63 family, with separate retinal `H34.1` and legacy ICD-9 433.x1/434.x1 sensitivity flags. Do not infer the exact previously claimed 9/118 enumerated codes or `P` principal semantics; review the diagnosis list and code-system provenance.
3. **Encounters:** stage all `IMP` admissions needed for stroke index selection, plus all potential `EMER` and competing `IMP` encounters in the relevant patient/date scope. The full reciprocal match pool must include *non-index* inpatient visits or it can create false unique ED matches. Verify key uniqueness and whether the export's IDs are stable across organizations.
4. **Patients/age:** join exact patient keys, stage sex/race/ethnicity/YOB and uncertainty bounds; independently select an earliest definitely eligible admission in each age cohort, without observing imaging. Audit uncertain age boundaries.
5. **Imaging:** stage only codebook-approved performed events. Match primary A by exact person+index IMP encounter and inpatient stay bounds. For B, use the full ED/IP reciprocal matching pool, reject ambiguous cases, and apply the 0/1/2-day ED calendar windows. Count at most one recorded modality indicator per patient/cohort/definition.
6. **Private QA:** report independent cohort denominators; missing inpatient end dates; missing ED dates; duplicate or cross-patient encounter IDs; unique/ambiguous ED-IP candidates; inpatient-only and ED-contributed counts; codebook/source-system capture by sex and race; changes in model estimands between A and B/C. Review whether suppression is needed even before an aggregate is shared.
7. **Clinical/statistical review:** finalize exact source codebook and diagnoses, covariates, subgroup definitions, site representation, adjusted models, multiplicity, and language avoiding causal assertions. Only after data-owner and clinical approval should any real full-source execution pathway be considered.

## Immediate next safe local action

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
```

No re-run of Step36–51, no `--execute-full-scan`, no changing private approval flags, and no protected data upload. The data-owner and clinician reviews remain real blockers, not formalities. Leave draft PR #1 **unmerged** pending the earlier historical restricted-data Git governance review.

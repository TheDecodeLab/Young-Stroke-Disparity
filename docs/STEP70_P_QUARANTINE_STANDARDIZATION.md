# Step70: Standardize the P-label imaging-code contrast by year and encounter ambiguity

**Status:** Read-only implementation and fabricated tests committed.
Pending investigator workstation test and real-data execution.
**No new TriNetX source scan is performed by Step70.**

## What Step69 established

In the primary uniform 18-50 cohort, CPT14 capture on the frozen
same-index IMP encounter is much lower in the unvalidated I63
`P=1` group than `P=0`. Including CPT14 codes recorded on
**another encounter with the same admission calendar date** changes
the unadjusted comparison substantially, and the P groups have
markedly different frequencies of patients with any
Step63-quarantined encounter key.

The principal scientific question is whether this reversal
persists once year and encounter-record ambiguity are given
the **same distribution** across P groups.

Crucial interpretation:
- `P=1` means at least one I63 on the indexed IMP had the P
  primary diagnosis indicator. `P=0` is a **mixture** of
  secondary, blank and otherwise non-P indicators.
- `ANY_AMBIG` means **one or more** of the indexed patient's
  source EMER/IMP encounter keys was quarantined for conflicting
  or missing dates; the affected key is NOT necessarily the
  selected index admission. It is a source-data quality stratum,
  not proof of a bad index or clinical diagnosis.
- `DAY0_other` is patient-level CPT14 recorded under any
  **different** encounter on the index admission date. It has
  neither verified EMER/IMP type nor verified same HCO. This is
  a deliberately broad sensitivity, NOT a clinical imaging rate.
- Only the 14 previously frozen CPT codes are used for outcomes
  here. The alternative system profiles in Step68 are source-row
  counts, NOT patient-level modality outcomes.

## One bundled, read-only comparison

`scripts/step70_P_quarantine_standardization.py` reuses the
completed private Step62/63/68 SQLite databases and the
patient-aggregating `Step69.aggregate()`. It verifies the
read-only Step62/63 source snapshot, the frozen Step68 scan
metadata, and Step69 reconciliation to Step68 aggregate outputs.

It reports **four CPT14-code-capture definitions** separately:
1. indexed IMP only;
2. indexed IMP OR other encounter on same admission day;
3. indexed IMP OR frozen unique ED link;
4. indexed IMP OR ED/other encounter in -2 to 0 day screen.

For each overlapping cohort and each definition:

- **Crude comparison** of P1 versus P0 coded-capture percentages;
- **No ambiguous encounter keys** comparison;
- **At least one ambiguous encounter key** comparison;
- **Direct standardization to common quarantine mix**;
- **Direct standardization to common calendar-year mix**;
- **Direct standardization to common joint calendar-year ×
  quarantine mix**;
- For the expanded same-day endpoint, year-by-quarantine P
  contrasts and denominator counts.

Standardization weights are the pooled original-cohort
`(n_P0 + n_P1)/N` proportions for each stratum; both P groups
receive identical weights. Every included stratum must have
both P values. Denominators and numerator totals must reconcile
exactly to each frozen cohort/P aggregate. Any missing stratum,
snapshot disagreement or inaccurate count raises a hard error.

This provides an interpretable **descriptive measurement
sensitivity** to differing source-quality and year distributions.
It is **not a causal mediation or adjusted disparity estimate**.
Because quarantine is associated with coding behavior itself,
standardizing does not validate encounter-specific imaging care.

## Official imaging codebook context (separate workstream)

The step69 prefix discovery should NOT be fed directly into
patient imaging outcomes. Official historical CMS tables show:

- `B02` CNS computerized tomography and `B03` CNS MRI;
- `B32` upper-artery computerized tomography and `B33`
  upper-artery MRI (verify the specific body part);
- `B31` upper-artery **fluoroscopy**, not CTA;
- `B24` **heart ultrasonography**, not brain/head imaging.

These are merely three-character **table families**, never
billable/patient-classifying code sets. Match each observed
**complete 7-character code** to a version-specific official
CMS description and valid date, including the actual brain,
carotid or intracranial anatomy, imaging modality and contrast
where appropriate. Do not count B24 or generic B31 as
head CT/MRI/CTA/MRA.

Historical primary CMS starting points:
- https://www.cms.gov/files/document/2016-pcs-code-tables.pdf
- https://www.cms.gov/files/document/icd-10-pcs-2018-tables-and-index-pdf.pdf
- https://www.cms.gov/medicare/coding-billing/icd-10-codes

The PCS code-family discovery numbers are source procedure rows
(and overlapping cohort memberships), NOT distinct young-stroke
patients or performed images. No automatic ICD-10-PCS, HCPCS,
or SNOMED imaging endpoint is released by Step70.

## One local execution, after synthetic and full-suite tests

From the repository root:

```bash
(
  set -e
  git pull --ff-only origin analysis-rebuild-phase1-audit
  python -m py_compile scripts/step69_same_day_attachment_diagnostics.py
  python -m py_compile scripts/step70_P_quarantine_standardization.py
  python -m pytest -q tests/test_step69_same_day_attachment_diagnostics.py tests/test_step70_P_quarantine_standardization.py
  python -m pytest -q
  python scripts/step70_P_quarantine_standardization.py
)
```

Runs in a fail-fast subshell so an earlier test failure stops
the analysis. It does **not** read or process the ~993-million-row
procedure CSV/ZIP and does not change Steps62/63/68 checkpoints.

**Handoff: TERMINAL OUTPUT ONLY.** No result ZIP, private JSON,
or SQLite file is needed. Clinical-derived aggregates remain
subject to institutional disclosure rules.

## Decision after the run

1. If the P reversal disappears or shrinks substantially after
   year×quarantine standardization, classify the earlier apparent
   reversal as **sensitive to differential source-data quality**.
2. If it persists within both reliable and ambiguous strata,
   encounter attachment remains a substantive source-coding
   hypothesis, but not proof of performed same-episode imaging.
3. Pursue exact CMS-year PCS and literature codebook development
   independently from these P-label checks.
4. Primary endpoint wording remains **documented imaging-code
   capture**, with sensitivity definitions and source-quality
   stratification transparently reported. Demographic disparities
   should not be modeled from a redefined endpoint before
   pre-specifying it.

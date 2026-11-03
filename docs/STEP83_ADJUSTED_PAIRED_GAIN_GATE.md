# Step83: Adjusted demographic sensitivity of additional same-day CPT capture

**Status:** Synthetic test and read-only local run PENDING.

## Why Step83 is required after Step82

Step82 established that crude and adjusted sex/race/ethnicity **code-capture**
contrasts can differ markedly between index inpatient and broad same-day
encounter attribution. The P=1 source-recording subgroup, not a validated
clinical acute-stroke subset, differs further from the overall cohort.

Subtracting contrasts estimated by two separate binomial GLMs would
produce a change in adjusted risks **without a reliable paired interval**.
Step83 directly models a binary event that is meaningful at patient grain:

> **Additional same-day capture** = no matching code on indexed IMP
> encounter AND a matching code on another encounter on index day.

This is an observable paired record-capture event, not a newly
performed clinical scan or verified linkage to the same stroke episode.

## Frozen-source design

- Reads only immutable Step62/63/68 local SQLite checkpoints; verify
  schema/source signature, completed 993,025,015-row legacy procedure
  checkpoint and cohort/code aggregate reconciliation. Does NOT open
  raw source ZIP or export patient identifiers.
- Reuses Step82 grouped patient covariate/mask stream, then subtracts
  `*_imp` numerators from `*_day0` numerators per covariate stratum.
  Exact patient-level paired event validity follows from nested
  Step68 imaging bitmasks; the aggregate any-code additional captures
  must equal frozen Step68 `new_day0_other`.
- Importantly, **modality-specific new-capture flags can be positive
  when any-code new-capture is zero**. For example CT may already
  be recorded on IMP but MRI first occurs on another same-day encounter.
  The synthetic tests specifically protect this distinction.

## Prespecified exploratory contrasts

For each of any 14 CPT codes, advanced imaging composite, head CT,
brain MRI and head CTA, calculate an adjusted **difference in probability
of additional same-day recording** across:

- male vs female, Black vs White, Hispanic vs non-Hispanic source labels;
- full cohort adjusted for index year, coarse age proxy, source P,
  ambiguity status and the other recorded demographics;
- P=0-only, P=1-only and unambiguous-key-only subsets, adjusting
  only covariates actually varied within each subset.

The P=0 and P=1 source groups are not validated as hospitals,
clinical cohorts, or care pathways. No source HCO identifier,
clinical severity, verified procedure performance or medication
administration exists. The original 2016–2024 period remains
part of the source-level data and is adjusted as a factor.

## Internal privacy and uncertainty rules

Each reported comparison must have >=11 patients in all relevant
P/ambiguity/demographic support strata and >=11 event and
complement patients in each compared category. Only adjusted
difference in additional-code capture and a **nominal 95%
model-based delta-method interval** print to the terminal.
No underlying subgroup category counts, risk rates or source codes
are output. Missing and unmapped demographic categories are
diagnosed by P without fabricating completeness.

Intervals assume independent patients under the working
binomial model and **do not account for HCO/site clustering**.
There are multiple exploratory modalities/contrasts and no
multiplicity adjustment or hypothesis testing. A true
site-adjusted causal disparity estimate is not available.

These are internal analytic safeguards, not certification
for external result release. The Step79 output
disclosure flag remains in place; institutional clearance
will be needed before external circulation, but outreach
must not be initiated without the investigator's instruction.

## Local execution

```bash
(
  set -e
  git pull --ff-only origin analysis-rebuild-phase1-audit
  python -m py_compile scripts/step83_adjusted_same_day_gain.py
  python -m pytest -q tests/test_step83_adjusted_same_day_gain.py
  python -m pytest -q
  python scripts/step83_adjusted_same_day_gain.py
)
```

Return **TERMINAL OUTPUT ONLY** for internal scientific review.
Do not upload private local data, patient/encounter IDs, SQLite,
numerical sources, or patient-level extracts.

## Decision after Step83

Step82 already supports a **measurement-led manuscript**, using
the old clinical-demographic motivation only as context.
Step83 decides whether adjusted demographic sensitivity of
newly attributed codes is stable enough to retain as a
substantive secondary Results section. A failure or
strong P heterogeneity would favor reporting demographic
contrasts cautiously as an exploratory quality sensitivity,
or choosing a methods-only manuscript.

A separate encounter-type mechanism cannot be established
from the frozen image flags because they lost the exact
code-bearing non-index encounter ID/type. No conclusion
should assign them to radiology or outpatient visits.
Thrombolysis/thrombectomy verification is not possible
from frozen patient flags and requires separately approved
clinical-code validation and reprocessing.

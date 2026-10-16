# Phase 1 missingness results and decision (2026-10-16)

Source: study-team-generated aggregate `missingness_age50.csv` after
running `scripts/step05_missingness.py` on the common age <=50 cohort.
Only aggregate, non-identifying values appear in this document.

## Missingness

| Variable | Known | Missing or unknown |
| --- | ---: | ---: |
| Race | 5,331 | 17,901 (77.05%) |
| Ethnicity | 5,925 | 17,307 (74.50%) |

## Imaging receipt by **race recording** (NOT by racial identity)

| Race information | n | MRI received | Any vascular received |
| --- | ---: | ---: | ---: |
| Known | 5,331 | 82.25% | 73.10% |
| Missing or unknown | 17,901 | 83.44% | 72.98% |

The missing/unknown group has 1.19 percentage points higher
unadjusted MRI receipt. This **does not identify** the mechanism
of missingness or establish that complete-case race comparisons are
unbiased.

### Sex-specific MRI receipt

| Race recording | Men | Women | Difference (Women minus Men) |
| --- | ---: | ---: | ---: |
| Known | 80.47% (n=2,028) | 83.35% (n=3,303) | +2.88 pp |
| Missing/unknown | 81.55% (n=7,646) | 84.85% (n=10,255) | +3.30 pp |

Race recording is also associated with sex composition:
20.96% of men and 24.36% of women have recorded race.
This is only an observed selection contrast and not an
assessment of the true racial composition of missing records.

## Interpretation and decisions

1. The unadjusted sex-MRI difference remains in known- and
   missing-race subsets. It is small; clinical significance is untested.
2. Racial comparisons remain secondary, with major potential
   selection bias. No missingness-assumption or multiple-imputation
   claim is supported by these summaries.
3. Continue a *preliminary* age/year-only binomial model as a
   reproducibility and methods benchmark. It is explicitly **not**
   a fully clinically adjusted model or evidence of unequal care.
4. For a publication-ready model, request original pre-index clinical
   diagnoses, stroke severity, hospital identifier and other clinically
   relevant covariates where available. Document missingness and
   decisions before fitting definitive models.
5. Keep NIS replication on hold until age bins, code mappings, and
   survey-weighted procedures can be verified.

## Data governance

This repo remains public with previously tracked row-level records.
Do not commit local cohorts, patient-level rows, detailed geographic
values, or nonreviewed breakdowns. Review contractual/institutional
approval, including history remediation when required.

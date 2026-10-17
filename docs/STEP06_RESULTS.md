# Step 6 results: preliminary age/year-only models (2026-10-16)

Source: the study team's `minimal_models_age50.csv` (six aggregate rows)
for an age 19-50 analytic cohort of 23,232 patients. The script uses a
binomial GLM with HC3 covariance and marginal standardization.
This analysis does **not** include stroke severity, indication, treatment
setting, hospital effects, insurance or individual vascular risks.
No row-level data are included here.

## Main results

The risk difference is standardized to the observed pooled age/year distribution,
defined as **men minus women**, in percentage points (pp).

| Outcome | Men adjusted % | Women adjusted % | RD pp (95% CI) | p |
| --- | ---: | ---: | ---: | ---: |
| MRI receipt | 81.246 | 84.527 | -3.281 (-4.275, -2.288) | 9.64e-11 |
| Any CTA/MRA receipt | 74.022 | 72.289 | +1.732 (+0.575, +2.890) | 0.00336 |

These are **associations**, not causal effects or inequity estimates.

## By availability of race information

| Subset | MRI men-minus-women RD pp (95% CI) | Any vascular RD pp (95% CI) |
| --- | ---: | ---: |
| Known race (n=5,331) | -3.050 (-5.215, -0.885) | +0.865 (-1.589, +3.319) |
| Missing race (n=17,901) | -3.415 (-4.534, -2.296) | +1.985 (+0.670, +3.301) |

The MRI association is similar in direction across race-availability
subsets. The known-race vascular contrast includes zero and is
imprecise. These sensitivity analyses do not establish that race
missingness is ignorable, and they provide **no adjusted race effect**.

## Verification and interpretation

- The submitted CSV contains 6 rows, each with internally consistent
  adjusted probability differences and confidence intervals.
- The full-cohort MRI absolute difference is modest, despite a very
  small model-based p value. Do not equate statistical significance
  with clinical relevance.
- The present any-vascular binary endpoint differs from the **sum
  of counts** used as a composite in the older manuscript. Its
  +1.73 pp adjusted sex contrast should not be compared to the old
  composite-count p=0.91 as if they were the same estimand.
- HC3 variance does not account for clustering by clinical site if
  such clustering is present. Provider/site identifiers are absent.
- These estimates are conditional on original cohort assembly and
  imaging code ascertainment, which have not been independently
  reconstructed from source clinical events.
- Do not fit a definitive clinical adjustment model until individual
  clinically relevant covariates have been extracted and validated.

## Next steps

1. Examine the four **mutually exclusive** vascular imaging categories:
   CTA only, MRA only, both, neither. The new Step 7 script reports
   counts and MRI receipt by sex, year and predefined age bands.
   This is descriptive and is **not** a clinical substitution test.
2. Obtain original diagnosis/procedure extraction queries and
   individual risk factors to construct defensible adjustment models.
3. Independently reconcile NIS source code, age strata and
   survey-weighted design; no cross-database replication claim yet.
4. Review data-sharing permissions for original patient-level
   parquet tracked in the public GitHub repository.

# Step73: Model-based uncertainty and covariate-support diagnostics

**Status:** Synthetic-only Python implementation and tests committed,
pending investigator local execution. All Step62/63/68 databases are
read-only; no further source procedure scan is needed.

## Source of the decision

Step72 finished with 699 passing repository tests and
**17 of 17 converged exploratory grouped binomial GLMs**
in both overlapping candidate coded-stroke cohorts.

In the uniform 18-50 primary cohort, the key **adjusted differences
in documented CPT14 code capture** are sensitive to endpoint:
sex has small differences; Black–White contrasts are small
after measured source-quality adjustment; Asian and
American Indian/Alaska Native contrasts are sizable negative
for both inpatient and same-day capture. Native
Hawaiian/Pacific Islander contrast changes considerably when
another same-day encounter is included. Ethnicity contrast
also changes sign or magnitude across outcome definitions
and complete-demographic-case selection. This is NOT
evidence of different confirmed clinical imaging receipt
or a national hospital-adjusted disparity.

Step72 only computed **point estimates** and no model
uncertainty or positivity diagnostics. An adjusted
contrast can be unstable when covariate support is sparse
or the model extrapolates across demographic groups with
different P and encounter-key quarantine distributions.

## Step73 scope

`scripts/step73_uncertainty_support_diagnostics.py`
independently reconstructs Step72's finite aggregated
model table from the frozen read-only Step62/63/68
databases and reconciles cohort counts/captured CPT14.
For the **same 17 specifications**, it:

1. Refits the same grouped binomial/logistic GLMs
   (year, approximate age band, sex, race, ethnicity,
   optional P and/or Step63 quarantine).
2. Recomputes average model-predicted code-capture
   probabilities after setting the focal demographic
   group to the reference and alternative category.
   The fixed standardization distribution is the
   corresponding fitted model population.
3. Uses the mathematical delta method
   (the gradient of the averaged prediction difference
   with respect to the GLM coefficients and the
   model's working covariance matrix) to calculate
   **nominal 95% confidence intervals** for the
   percentage-point differences. These are estimates
   under the fitted independent-binomial model and
   are NOT hospital-cluster-robust, propensity-weighted,
   causal, or guaranteed to cover the true clinical
   utilization contrast. They must NOT be presented
   as definitive epidemiologic inference.
4. Reports whether each demographic contrast has
   **missing or small counts** (under 11) in one
   or more crossed binary `P×held` source-quality
   cells for the reference and alternative
   category. This is a limited support diagnostic,
   not complete overlap validation.
5. Emits a compact, local-only terminal summary
   for six prespecified comparisons: female vs male;
   Black, Asian, AIAN and NHPI vs White; and Hispanic
   vs non-Hispanic ethnicity. Large, sparse and
   sensitive point estimates should be treated
   as research-quality signals requiring further
   validation, not as corrected healthcare disparities.

Modality and endpoint definitions remain the same
14 CPT codes. Unreviewed ICD-10-PCS/B-prefixed,
SNOMED or HCPCS codes **are not included**.
The usual source/HCO variability, lack of stroke
severity, diagnosis P validity, unknown demographics,
and time-window episode-attribution limitations
remain in force. The two cohort samples **overlap**.

## Execution: one bundled local-only round

```bash
(
  set -e
  git pull --ff-only origin analysis-rebuild-phase1-audit
  python -m py_compile scripts/step73_uncertainty_support_diagnostics.py
  python -m pytest -q tests/test_step73_uncertainty_support_diagnostics.py
  python -m pytest -q
  python scripts/step73_uncertainty_support_diagnostics.py
)
```

The fail-fast shell stops before data analysis if
the synthetic tests or full suite fail.

**Next handoff: TERMINAL OUTPUT ONLY.** No ZIP,
SQLite, manuscript file, source data, JSON or
other private result attachment is required.

## Interpretation gate

Compare nominal intervals, point estimates and
support flags among primary inpatient-only,
advanced-only, and exploratory broader same-day
coded outcomes; benchmark against Step72's
complete-case and no-quarantine sensitivity.
Flag the contrast as fragile if the direction/
magnitude is highly outcome-, sample-, or
support-dependent. Even a nominal interval
not crossing zero does **not** solve unmeasured
institutional coding variation or data-capture
bias.

Separately, the final expanded neurovascular
imaging codebook must be built from official
**exact seven-character, year-valid** ICD-10-PCS
and vetted alternative codes, never all PCS B
codes. We have not approved or applied that
broader codebook yet.

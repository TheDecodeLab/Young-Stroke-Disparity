# Step87: Frozen aggregate standardization sensitivity for Supplementary Table S3

**Scope:** Reproducible, read-only analysis of the existing private Step78 `table3_year_quarantine.csv` output. The script and synthetic unit tests are public, but the actual source CSV, stratum counts, detailed diagnostic report, and manuscript outputs stay in approved private storage. No TriNetX ZIP, source clinical table, or patient-level checkpoint is read.

## Scientific question

Do the published exploratory P=1 minus P=0 standardized recording-code contrasts rely on near-empty year-by-encounter-ambiguity strata? Is the sign stable to reasonable changes of the descriptive standardization target? Do the ambiguous and nonambiguous source-recording groups show the same direction?

The code independently reconstructs exact integer event numerators from the full-precision percentages and denominators in the frozen aggregate, then checks year-versus-ALL group reconciliation. It uses common weights proportional to the pooled P-group membership in each joint stratum, consistent with Step70. It recalculates the weights after every restricted-population comparison. An ambiguous-key group label is a source-recording-quality marker, not a hospital type, imaging receipt, or clinical acuity marker.

## Sensitivities

The script reports joint-stratum support and event complements, calendar-year omission, three-year-era pooling, changing minimum P-group denominator, year-only standardization, and contrasts standardized separately within each encounter-key ambiguity group. Its source CSV only supports independent verification of **index-inpatient and index-plus-other-same-day** outcomes. The unique-ED and broader-near-admission endpoints are not independently re-estimated from this file because their required joint-stratum numerators are absent.

The numeric stability checks assess *descriptive sensitivity*, not hospital-independent uncertainty or a care disparity. Do not interpret a sign reversal as causal adjustment or clinical equity evidence.

## Authorized local reproduction

Run the test suite before running the review on the authorized workstation:

```bash
python -m pytest -q tests/test_step87_s3_aggregate_sensitivity.py
python scripts/step87_s3_aggregate_sensitivity.py \
  --acknowledge I_CONFIRM_INTERNAL_REVIEW_ONLY
```

The source CSV path is the existing Step78 aggregate location by default. Output is created exclusively under gitignored `results/phase1/full_reconstruction_private/step87_s3_aggregate_private/`, with no overwrite and 0600 file permissions. The script prints only coarse yes/no statuses. A detailed report never belongs in GitHub.

## Execution and manuscript handoff

The investigator supplied the Step78 aggregate CSV in the private project conversation. The analysis and six fabricated-data tests passed in the controlled container environment. The follow-up v1.11 Word manuscript and supplement, provided privately to the investigator, retain the exploratory S3 results with newly documented stratum support, year-exclusion and era-pooling checks, and contrasting ambiguity-specific descriptive associations. The supplement maintains separate Methods, Results, and Limitations sections and its original numeric tables.

This evidence closes the *minimum-stratum and calendar-year stability* check for the main index/same-day comparison only. It does not close clinical validation, HCO clustering or case-mix, historical annual CPT-codebook review, or journal submission declarations.
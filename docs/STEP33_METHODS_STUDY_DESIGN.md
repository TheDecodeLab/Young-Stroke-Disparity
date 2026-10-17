# Step 33: Recorded imaging-code heterogeneity and methods-paper concept

**Status:** Source Step32 QC validated on study workstation:
**157 tests passed; two nonblocking warnings**. Step32 uses the
already extracted private indexes, not the original 1.17-billion-row
procedure CSV. Its broad age, sex and year stratum counts
reconcile independently to all 86,902 patients and to the Step30
combined head/neck full-scan totals in all four time windows.

These results are only *recorded CPT-code matching around a
principal I63 diagnosis date* in the existing Diamond extract.
Do not use the word hospitalized, performed imaging, first-ever stroke,
healthcare access or disparity effect in results based on this outcome.

## Descriptive findings: proposed primary +/-1 calendar day

Fixed denominator = 86,902 approximate-age 19-50 persons with a
first observed principal ICD-10-CM I63 diagnosis in 2018-2019.
The rate numerator is presence of at least one of 14 reviewed
imaging CPT codes (CT brain, MRI brain, CTA/MRA head/neck) within
+/-1 calendar day. Age comes from birth year only.

| One-dimensional stratum | Denominator | With a matching included code | Matching-code percentage |
| --- | ---: | ---: | ---: |
| Age 19-29 | 7,456 | 3,922 | 52.60% |
| Age 30-39 | 20,051 | 9,761 | 48.68% |
| Age 40-50 | 59,395 | 26,266 | 44.22% |
| Recorded female | 49,074 | 23,411 | 47.71% |
| Recorded male | 37,828 | 16,538 | 43.72% |
| Index year 2018 | 48,706 | 21,283 | 43.70% |
| Index year 2019 | 38,196 | 18,666 | 48.87% |

Each dimension sums independently to 86,902 and the common
39,949 people with any matching included code. Age, recorded sex
and index year results are **separate marginal views**, not mutually
exclusive rows across the entire table; do not sum all seven rows.

Approximate unadjusted percentage-point differences in
matching-code frequency:
- Age 19-29 versus 40-50: +8.38 points.
- Recorded female versus male: +3.99 points.
- 2019 versus 2018: +5.17 points.

These contrasts have **no adjustment, confidence intervals or
claim about imaging receipt**. They can arise from patient
mix, unmeasured coverage, billing/coding workflows, source
observation, clinical decisions, stroke definition or other factors.
Do not label any difference a clinical disparity.

## Relating heterogeneity to code-list and window sensitivity

A uniform 86,902-person denominator yields:
- Same-day 14-code match: 37,379 / 86,902 (43.01%).
- +/-1 day: 39,949 / 86,902 (45.97%).
- +/-3 day: 41,097 / 86,902 (47.29%).
- +/-7 day: 42,300 / 86,902 (48.68%).

Changing the acceptable time window from same-day to +/-7
days changes *any-match* recorded-code ascertainment by
**5.66 percentage points**, while expanding the original
nine-code definition to 14 codes changes it by only **0.20
percentage points** at +/-1 day. These changes are
**measurement-definition sensitivity**, not verified biases in
clinical care or a gold-standard ascertainment error.

Over half the population still has no listed imaging code
within +/-1 day, and 51.32% within +/-7 days. Without a
complete enrollment/claims observation model and encounter
identifiers, do not infer how many received no imaging.

## Recommended manuscript framing: methods/data quality

**Working title**:

*How Cohort Selection, Imaging Code Definitions, and Temporal
Linkage Affect Recorded Neuroimaging Patterns in a
Diagnosis-Indexed Stroke Dataset*

**Question:** In an existing 2018-2019 administrative data
extract, to what degree do analysis choices alter who enters
a stroke-related imaging cohort and the count of people
with observable procedure-code matches?

**Specific objectives (NOT clinical disparity aims):**

1. Audit imaging-conditioned inclusion in the historical
   notebook and demonstrate why patients having CT only
   were excluded by its original data-processing logic.
   Important: original and reconstructed denominators
   differ in age and index specifications; **never treat
   their size difference as a quantified causal bias
   without a harmonized source-level reconstruction**.
2. Quantify sensitivity of code matching to (a) the
   historical 9-code and reviewed 14-code definitions,
   (b) intracranial/head-only versus combined head/neck
   definitions, (c) day 0, +/-1, +/-3, +/-7 temporal windows.
   Keep a single imaging-independent diagnosis denominator.
3. Describe variability of observed CPT-code matching
   across broad recorded age, sex and index-year groups.
   Explore whether apparent differences are stable under
   different code and window definitions, not whether
   specific groups clinically received insufficient imaging.
4. Assess information quality: high missing/unknown race
   (77.90%) and ethnicity (75.39%), 10.46% unknown/invalid
   birth year among the broader diagnosis index, lack
   of an encounter identifier, incomplete observation
   and uncertain site-level code capture.

**Design:** An observational source-data methods audit,
not a patient-outcomes or hospitalization-utilization study.
No encounter or performed-imaging gold standard exists.
A clinical stroke specialist's independent sign-off was
not obtained; the CPT catalog was reviewed using
historical CMS listings and relevant stroke guidelines.
A publication needs coauthor/ethics and data release review.

## Planned scientific exhibits

| Exhibit | Content | Source |
| --- | --- | --- |
| Figure 1 | Diagram: old imaging-conditioned cohort vs new diagnosis-first imaging-independent denominator; label non-equivalent age rules | Notebook + Steps 8-25 |
| Figure 2 | Any-code match versus temporal window, historic 9-code versus new 14-code and head/neck split | Step 31 aggregates |
| Figure 3 | Descriptive matching-code percentages by age band, recorded sex, index year | Step 32 broad aggregates |
| Table 1 | Demographic/diagnosis-index attrition and missingness | Steps 22-24 |
| Table 2 | Codes, anatomic interpretation, 9 vs 14 coverage and exact window specifications | Step 30 + clinical codebook |

All proposed tables/figures remain **internal until
institutional data-sharing and complementary small-cell
disclosure review**. Every plot must prominently label
the outcome **recorded CPT code match**, not receipt
of imaging.

## Next lightweight computation: Step 33

The script
[step33_aggregate_patterns.py](../scripts/step33_aggregate_patterns.py)
checks all age, sex and index-year marginal totals, head/neck
nesting, code-preserving sensitivity windows and Step 31 matching
denominators. It recomputes broad descriptive code-match
percentages, unadjusted percentage-point differences and
relative definition sensitivity from Step31 + Step32
**aggregate JSONs only**.

Run locally from project root:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q && \
python scripts/step33_aggregate_patterns.py \
  --step31 results/phase1/step31_expanded_reconciliation.json \
  --step32 results/phase1/step32_recording_heterogeneity_qc.json \
  --output results/phase1/step33_recording_pattern_descriptives.json
```

This never reads original source ZIP, private SQLite or
patient-level records. All outputs still carry
cross_table_disclosure_review_required=true and
clinical_inference_allowed=false.

**No further billion-row scan is indicated.** Prioritize
a rigorous limitations/feasibility assessment before
claiming manuscript publishability or running sex/race
regressions. This branch is a draft and has not been merged.

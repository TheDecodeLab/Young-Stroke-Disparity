# Step 26: clinical protocol and data-feasibility decision memo

**Status:** Proposed specifications for review, **NOT clinical approval**. No new
clinical data scan, encounter validation, modeling, or manuscript rewrite is
authorized by this document.

## 1. Established engineering findings

Step 25 reconciles the previously scanned original 2023 TriNetX Diamond
export and completed SQLite indexes without reading source records:
- 1,425,659,024 diagnosis and 1,166,493,611 procedure rows were processed,
  with source-manifest verification.
- 962,351 unique patients had a first **principal ICD-10-CM I63-family
  diagnosis in 2018–2019** (not necessarily their first-ever stroke).
- 86,902 met the **provisional uniform age 19–50 and recognized sex**
  criteria based on year of birth.
- Historical nine-code CPT window of ±7 calendar days: 8,713 CT only,
  24,074 CT plus MRI/CTA/MRA, 9,355 MRI/CTA/MRA without CT, 44,760 with
  no matching one of those four modalities. The four counts sum exactly.
- 10.46% of indexed patients have missing/invalid birth year. Among the
  eligible group, 77.90% have unknown/missing race and 75.39% have
  unknown/missing ethnicity.
- Step 22 confirmed time-window sensitivity: MRI 17,080 patients with
  same-day code vs 27,459 patients within ±7 days; CT 24,826 vs 32,787.

These are **code-matching counts**, not encounter-linked receipt,
clinically adjudicated stroke diagnoses, or population imaging rates.

The dataset's **Diamond Data** cohort label and 4.29 million source
patients do not establish national representativeness or complete
capture. Ask the source data steward how the exported cohort was
assembled (including any stroke-related prefilter), what enrollment
and service coverage applies, and whether claims are fully observable.

## 2. The most important scientific decision: population and outcome

| Candidate study target | Required denominator | Can current Diamond export verify it? | Implication |
| --- | --- | --- | --- |
| **A. Imaging during index hospitalized ischemic stroke** (closest to the submitted/rejected manuscript) | All eligible *verified admissions* or first hospital episodes, regardless of imaging | **No.** No admission/encounter key was found in the ZIP's source tables | Request encounter-linked source or validated claims inpatient episodes. **Do not claim this estimand** based only on date proximity |
| **B. Recorded imaging around first 2018–19 principal I63 diagnosis** | All qualifying diagnosis-indexed patients with adequate source observability | Partly, as a *patient-date temporal proxy*, not proof of hospitalization or performed imaging | A different, carefully labeled descriptive question may be possible after source and codebook validation |
| **C. MRI/CTA/MRA among CT-coded potential stroke pathways** | CT-coded plus clinically validated index stroke candidates | CT code receipt is observable only for a limited historical CPT list; CT itself conditions selection | Cannot make claims about CT use or access among all stroke patients; target population changes substantially |

**Proposed priority:** Preserve the original admission-focused question
only if the team can obtain admission/encounter linkage. If not feasible,
formally decide with clinical coauthors whether question B is scientifically
worth publishing with conservative claims. Do not quietly substitute B
for A while retaining the original manuscript's title, abstract or
conclusions.

## 3. Investigator decisions requested before another large scan

### 3.1 Stroke diagnosis and episode definition

- Do we require an inpatient facility claim, admission dates, discharge
  status, place of service and a unique encounter/claim or hospitalization
  identifier? These are **not** available as established linkage keys in
  the current CSV schemas. Ask TriNetX/data steward about an episode-level
  export or verified claims encounter reconstruction.
- Define whether an ICD-10-CM `I63.*` **principal** diagnosis (indicator
  `P`) is sufficient for case ascertainment; explain `S` and `Unknown`.
  The 2018–19 source contains many I63 rows with Unknown status. They
  were excluded from the current diagnosis index.
- Review I63 subcodes, including **I63.6**, and choose whether to exclude
  nonarterial infarction phenotypes. The current script includes all
  syntactically matching I63 subcodes, with no event-level validation.
- The legacy notebook additionally included ICD-9-CM `433.x1/434.x1`
  codes and `H34.1`. Determine whether those belong in case definitions,
  prior-stroke lookback only, sensitivity cohorts, or neither.
- First principal diagnosis *in 2018–19* is not first-ever stroke:
  agree an available lookback, washout rule, and index-event handling
  of recurrent claims without an admission key.
- Clarify the date field's meaning and claims completeness at the
  patient and provider level, before interpreting calendar-day matches.

### 3.2 Age and sex: a previously overlooked design mismatch

The historical notebook declares **`YOUNG_AGE_FEMALE = 54`** and
**`YOUNG_AGE_MALE = 52`**, requiring age **above 18**. These were
taken from Abedi et al., *Defining the Age of Young Ischemic Stroke
Using Data-Driven Approaches* (J Clin Med 2023, PMID 37048683;
DOI 10.3390/jcm12072600). The paper proposed sex-specific cutoffs
from an EHR study of 13 Pennsylvania hospitals and noted that
validation in more diverse populations is needed.

The newer reconstruction uses the uniform age range **19–50**.
These are different populations. Their counts are **not** expected
to agree.

**Proposed protocol decision:** Prespecify the primary age definition
based on the scientific question. To reproduce the original clinical
young-stroke definition, the historical 19–54 for women and 19–52
for men merits consideration, with age-standardized/common-support
sensitivity analyses when comparing sexes. To compare all sexes under
identical eligibility criteria, use uniform 19–50 as the primary
analysis and the historical sex-specific cutoffs as a separately
labeled sensitivity analysis. Both may be reported if approved, but
**their denominators must not be pooled or equated**.

Only year of birth is available, so year(index)−birth year can be one
year different from actual age at the event, notably around cutoffs.

### 3.3 Imaging codebook, time and indication

Historical manuscript definitions (from `dataset/df_tot_CPT_codes.csv`):
- CT brain: `70450`, `70460`, `70470`
- CTA head: `70496`
- Brain MRI: `70551`, `70552`, `70553`
- MRA head: `70544`, `70545`

**Candidates for licensed-codebook / radiology review, not approved
expansions:** CTA neck `70498`; MRA head `70546`; MRA neck
`70547`–`70549`. Assess possible billed HCPCS and ICD-10-PCS
representations, bundling, professional/facility codes, head-vs-neck
imaging, and any claim types not represented as CPT rows.

- Define **performed imaging** vs **billed/recorded procedure code**.
- No imaging in nine historical codes does **not** prove no scan occurred.
  The 44,760 unmatched patients need source-coverage interpretation.
- Day 0 vs ±1, ±3 and ±7-day windows make substantial differences.
  Choose a scientifically defensible **primary window** before seeing
  effect estimates. Without encounters, even a narrow window does not
  prove the same admission or event. Keep other windows as sensitivity.
- If restricting to CT-coded patients, acknowledge conditioning on an
  imaging outcome changes the estimand and may induce selection bias.

### 3.4 Race, ethnicity, sex and other disparity covariates

- In the reconstructed age-eligible group, 77.9% of race and 75.4% of
  ethnicity are missing/unknown. **Do not present complete-case
  contrasts as population race/ethnicity disparities.**
- Determine why race and ethnicity are unavailable: missing at source,
  vendor-defined Unknown, site/network mix, or post-join loss.
  Evaluate observable differences between missing and nonmissing
  records without revealing small groups.
- Sex comparisons also require stable denominator, index date and
  complete imaging classification; major limitations extend beyond
  race/ethnicity.
- Consider severity, stroke subtype, site/HCO, insurance, deprivation
  and care pathway as confounders **only if measured and linkable**.
  Do not claim these covariates exist in this export without checking.

## 4. Explicit approval checklist

No modeling or 1.17B-row procedure rescan until the study lead and a
clinical stroke specialist agree to:
1. A single target estimand and study population (A, B, or C above).
2. Encounter-source availability, episode index and provenance.
3. Diagnoses, first-event/washout, study years and age/sex criteria.
4. Complete modality codebook, principal time window and sensitivity windows.
5. Source missingness and analytic strategy for race/ethnicity.
6. TriNetX/institutional data-use permission, Git history remediation and
   cumulative small-cell disclosure controls.

Record reviewer, decision date, rationale, changes requested and the
approved protocol version in **institution-approved storage**. No
automatic approval flag is inferred from a passing Python test.

## 5. Current publication/data governance hold

Earlier public Git history includes a legacy patient-level derived
TriNetX Parquet. An earlier fine-grained I63 report also suppressed
a small category whose count could be recovered by subtraction from
released totals. Treat that prior report as needing disclosure review;
the coarser repaired report does **not** cancel earlier release risks.
Do not upload clinical ZIP/SQLite or publish additional tables without
approved release review.

**Recommended next handoff:** Have the clinical and data teams decide
whether encounter-linked data are available and sign off on the
study target and age/codebook specifications. In parallel, request
source documentation on the meaning of `principal_diagnosis_indicator`
and demographic missingness, without launching additional massive scans.

# Step 27: hospitalization-level feasibility protocol

**Draft, for clinical and data-steward review only.** We are preserving
the original research question: variation in recorded brain MRI and
vascular CTA/MRA imaging during index ischemic-stroke hospitalizations
among younger adults. This is NOT authorization to rescan or model.

## Current evidence and scientific stop

The full Diamond ZIP reconstruction verified its source row counts and
selected 962,351 patients with a principal ICD-10-CM I63 diagnosis in
2018-2019 and 86,902 with approximate age 19-50 and recognized sex.
Historical CPT linkage within ±7 days showed 8,713 CT-only patients
and 44,760 people without any of four listed modality classes.
The age-eligible group has 77.9% unknown race and 75.39% unknown
ethnicity. The data have patient identifiers and event dates, but
none of 20 original ZIP member headers provided a validated common
encounter/admission identifier. Therefore **none of these code-matching
figures are verified inpatient imaging utilization**.

The previous manuscript excluded CT-only patients because it defined
the cohort after filtering advanced imaging. The replacement must
select stroke admissions **before** looking at CT/MRI/CTA/MRA codes.

## 1. Feasibility: ask for source semantics, not patient records

Request an approved schema/data dictionary for encounters, inpatient
facility claims, diagnoses, procedures, demographics and coverage.
Minimum evidence needed:

| Required relationship | What must be available or demonstrably derivable |
| --- | --- |
| Patient | Stable pseudonymous patient key linking all relevant tables |
| Inpatient episode | Hospitalization/encounter/facility-claim episode ID, or a documented and validated stay-grouping algorithm |
| Timing and setting | Admission and discharge boundaries; inpatient vs ED, observation and outpatient indicators; transfer handling |
| Diagnosis | Stroke ICD code and code system; diagnosis-to-admission relationship; meaning of principal indicator P/S/Unknown |
| Procedures | Procedure-to-**same-admission** relationship; procedure date; code, system, claim/billing type and coverage |
| Demographics | Age or birth information, sex, race/ethnicity and definitions of unknown/missing |
| Site and observability | De-identified provider/hospital key if authorized; population selection, claims capture, enrollment, calendar coverage and billing lag |
| Governance | Data license/DUA, authorized environments, IRB/privacy review, permitted aggregate release and cell-suppression policy |

A field called encounter ID is not enough: its meaning and consistency
across tables must be confirmed. A patient ID plus ±7 days is **not**
proof of the same hospitalization. The original ZIP's Diamond Data
cohort label does not prove completeness or representativeness.

## 2. Proposed study estimand and episode-first analysis

**Target population:** all eligible patients whose prespecified index
hospitalization for ischemic stroke began during 2018-2019, independent
of imaging receipt. This can only be constructed after source feasibility
has been demonstrated and clinicians approve diagnosis codes and setting.

**Index:** identify verified inpatient episodes; associate their
diagnoses by encounter linkage; apply principal ischemic-stroke
definition; resolve transfers, overlapping claims, readmissions,
and whether the unit is first episode per person over two years
or first per person-year. Use a prespecified lookback for prior stroke
when incidentness is claimed. Do not infer first-ever stroke from
the earliest 2018-2019 record alone.

**Age:** original notebook used >18 through 54 for women and
through 52 for men; provisional reconstruction used common 19-50.
Choose one *primary* inclusion rule and justification before analysis.
For sex comparisons, assess the resulting age-overlap problem and
pre-specify common-age or standardized sensitivity. Birth-year-only
age is approximate at cutoff boundaries.

**Outcomes:** any recorded brain MRI during the linked admission;
any recorded head/neck vascular CTA/MRA (specify whether individual
or combined outcomes are primary); CT brain documented separately.
Specify code-system coverage, whether performed versus billed imaging
can be observed, facility/professional claims completeness and
timing of ED imaging immediately preceding an inpatient stay.
Use clinically approved CPT/HCPCS/ICD-10-PCS codebooks; the nine
historical CPT codes omit relevant head/neck variants. A lack of
one of these nine codes is not proof of no imaging.

**Denominator:** includes eligible people with CT only and without
any identified imaging. Assign modality flags by LEFT joining
encounter-validated imaging to the preselected index episode; avoid
selecting the cohort based on the procedure outcomes.

**Adjustment and interpretation:** plan age, year and site/HCO
where observed; clinical indication/severity, pre-index vascular
risk factors and access variables only if linkable and validated.
The legacy composite vascular risk score included female-sex
weighting and is not automatically appropriate in sex comparisons.
With >75% unknown race/ethnicity, do not claim population race
disparities from complete cases or assume missingness at random.
Observed imaging differences alone are not measures of care quality.

**NIS:** keep prior NIS claims on hold separately. NIS requires
its own original source methods/survey design, and procedure
code coverage must be verified rather than assumed equivalent to
CPT claims.

## 3. Explicit decision gates

- **Gate A, governance:** licensed data access, institutional review,
  permissions to analyze and share aggregates, remediation assessment
  for existing public patient-level Parquet and prior small-cell report.
- **Gate B, schema feasibility:** study team and data steward document
  a valid admission/episode unit, reliable diagnoses/procedure joins,
  setting indicators and complete modality observability. **No patient
  rows requested at this stage.**
- **Gate C, limited authorized linkage QC:** in secure local storage,
  inspect linkage uniqueness, dates, transfers, repeat admissions,
  principal coding, procedure attribution and missing claims coverage;
  share only permitted suppressed aggregates.
- **Gate D, finalized protocol:** investigator and stroke specialist
  approve age range, index, stroke and imaging codebooks, observation
  period, primary window, denominators and missingness strategy
  **before** any full re-extraction.
- **Gate E, analysis authorization:** only after a revised admission
  cohort reconciles to source and passes clinical QC can disparity
  modeling be considered.

| Steward response | Decision |
| --- | --- |
| Valid and licensed shared inpatient episode key | Proceed to limited secure linkage QC after approvals |
| Only claim headers can identify stays | Require a documented and validated inpatient-episode algorithm first |
| Only patient IDs and event dates available | **STOP original hospitalization study**; formally reconsider the research question with coauthors |
| Admission linkage works but imaging capture is incomplete | **STOP** until observability improves or outcomes are revised |
| Missing data-use authorization | **STOP**; do not transfer, publish or merge derived clinical data |

**Next:** [Data-steward request](STEP27_ENCOUNTER_DATA_REQUEST.md) and
[review sign-off template](STEP27_APPROVAL_RECORD_TEMPLATE.md).
No new big ZIP scan is requested by this document.

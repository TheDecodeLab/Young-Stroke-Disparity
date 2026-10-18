# Active Research Network Study Plan and Decision Register
**Plan of record:** 2026-10-18, after successful local Step57 execution. **This document supersedes conflicting provisional assumptions in earlier Steps 1–48; the earlier documents remain an audit trail, not active execution instructions.** Consult the [code evidence and manuscript-citation register](references/IMAGING_CODE_CITATION_REGISTER.md) and [citation files](references/imaging_references.csl.json).

## 1. Current evidence and execution status

- Local workstation: **511 passed, 3 existing nonblocking warnings**, Step57 **13** CPT-labelled reference entries classified: **8 excluded from six diagnostic imaging outcomes, 5 held** as nonstandard-length labels. All **14/14** published core CPT code meanings were found in the pre-existing **3,270-entry reference vocabulary**.
- System mix among reference terminology entries: CPT 30, HCPCS 20, ICD-10-PCS 80, ICD-9-CM 3, SNOMED 3,137. **These are NOT frequencies of actual procedures** in the Research Network.
- **No Research Network patient/encounter/diagnosis/procedure source-wide scan has been run under the rebuilt phenotype**. Step45 old real-data CLI **remains disabled**. Step49–53 logic has only been validated with synthetic records. The final Research Network study years, encounter semantics, procedure-use coverage, source-specific mapping and clinical event meaning are unknown.
- Step47 `finalize` is **not** valid for Research Network's full period because its signoff worksheet hardcodes Diamond-style `valid_for_2018_2019`. Never silently mark codebook/institutional approval fields true.
- PR #1 stays **draft and unmerged** pending governance review of possible restricted clinical data in preexisting repository history. No source-derived private terminology rows or clinical data should be uploaded to GitHub.

## 2. Population, source, period and denominator

**Separate data sources and research questions**:
- **Diamond**: fixed 2018-01-01–2019-12-31 study period; historical source-specific analysis. Its old per-year results and code-review scope cannot be generalized to the Research Network.
- **TriNetX Research Network**: *proposed* `IMP.start_date` cohort window **2016-01-01 through the last adequately complete calendar year observed in approved, local coverage QA**. 2016 is an investigator-selected post-ICD-10 era starting point (not an observed lower bound). End date unknown. Test calendar-year and HCO coverage and recent partial years *before* finalizing. CMS verifies transition to ICD-10 on **2015-10-01** [CMS2015_ICD10].
- The unit of analysis is **one eligible index hospitalized ischemic stroke encounter per person per age cohort**. Exact stroke diagnosis family candidate definitions: ICD-10-CM `I63.*`; retinal arterial occlusion `H34.1` as distinct subgroup/sensitivity, not silently pooled; ICD-9-CM `433.x1`/`434.x1` are legacy-era sensitivity/provenance and not presumed valid for 2016+ U.S. service dates. The previously mentioned 9/118 individual-code enumeration is **not established** and MUST NOT be fabricated. Principal-diagnosis indicator, `IMP` semantics and whether ED diagnosis should qualify need steward/clinical confirmation; assess broad-vs-principal criteria separately.
- **Two independent overlapping co-primary cohorts**: (Ages) all patients 18–50 and (Historical) men 18–52/women 18–54. Apply age definitions independently; do not pool overlapping counts or pretend independence. Only YOB exists; specify and audit possible exact-age interval and uncertain eligibility. Unknown/nonbinary sex handling for the historical definition needs a signed rule. Select index admissions without using any imaging availability.

## 3. Two imaging outcome definitions, investigator approved

| Role | Definition | Linkage status |
|---|---|---|
| **Primary A** | At least one documented code from evidence-backed modality set, recorded on exact **same `patient_id` and index `IMP.encounter_id`** during the inpatient stay | Same encountered event key; procedure code is **NOT proof scan completed** |
| **Sensitivity B** | A plus modality-specific coded procedures from **one** preceding `EMER` encounter for same `patient_id`, satisfying reciprocal uniqueness, ED **end date** to IMP **start date** **0–1 calendar days** | **Date-only tentative association; NOT proven same hospital or one stay** |
| **Further sensitivities C** | Repeat B at 0 and 0–2 **calendar-day** date windows; report unlinked/ambiguous/missing-date cases | Wider windows need not yield monotonic estimates due to competing matches |

Require ED `EMER` and inpatient `IMP` labels, distinct encounter identifiers, valid starts/ends, no reversed interval, and reciprocal unique candidate pairs **against all eligible candidate encounters including non-index inpatient stays**. Never assume `source_id` identifies an HCO, or that shared dates prove same hospital. Missing inpatient end date makes inpatient-stay imaging classification **unassessable**, not confidently negative. The denominator remains independent of imaging. Report **recorded imaging-code capture** rather than performed imaging or lack of care. Do not attach standalone ED stroke visits to a hospitalized denominator.

## 4. Evidence-backed imaging categories and codebook

**High-specificity core** (all external CPT meanings explicitly listed in CMS 2010 Transmittal 738, Attachment 1, PDF page 6 [CMS2010_MPPR]; 14 exact codes):

| Category | CPT codes | Endpoint role |
|---|---|---|
| MRI_BRAIN | 70551, 70552, 70553 | Brain MRI indicator |
| CTA_HEAD | 70496 | Head CTA indicator |
| CTA_NECK | 70498 | Neck CTA indicator |
| MRA_HEAD | 70544, 70545, 70546 | Head MRA indicator |
| MRA_NECK | 70547, 70548, 70549 | Neck MRA indicator |
| CT_HEAD | 70450, 70460, 70470 | Plain/contrast head CT comparator, separate from advanced MRI/vascular imaging |

Step57 external review of 13 other **CPT-labelled reference entries**: eight definitively **not standalone target diagnostic exams** (`0398T`, `0865T`, `0866T`, `61736`, `61737`, `61751`, `78814`, `78830`) and five seven-digit **unresolved purported CPT identifiers**. These five must be held rather than truncated, guessed, clinically excluded or included. See crosswalk and source register for evidence and restrictions.

**Version-aware future definitions**: new **2026-01-01** CPT `70471` combined head-and-neck CTA potentially maps to **both CTA_HEAD and CTA_NECK** but is **not** in historical CPT14; `70472` and `70473` are cerebral CT perfusion, separate from non-perfusion diagnostic CT; `0042T` ends in 2025. CMS/HHS rule evidence is [HHS2025_OPPS2026]. Any 2026 inclusion requires actual service-year coverage, local code occurrence and version-appropriate implementation.
  
**Broader-code sensitivity pending**: Exact source-code and version mapping for SNOMED, HCPCS and ICD-10-PCS; don't use lexical substring matches or convert 3,137 SNOMED reference entries into measured clinical utilization. Procedure rows’ code-system distributions and performed/order status remain unknown. The eight exclusions are **from six specific outcomes only**, not assertions these services never appear clinically.

## 5. Analysis and manuscript framing

- Report denominators and per-modality/composite documented-code rates in each age cohort **separately**; distinguish CT_HEAD comparator and any advanced imaging composite by a frozen rule.
- Planned disparity comparisons by sex, race, ethnicity and age require preregistered strata, confounders, calendar year and site/capture sensitivity. Avoid interpreting observed associations as causal. Assess missingness and HCO representation by strata before models.
- ED sensitivity B can only measure change in *coded event capture under a provisional date-only association*, not validity of a hospital transfer. Describe limitations of missing ED imaging codes and incomplete network participation.
- Manuscript citations: [Vagal2017_AJNR] and [Wang2024_JACR] for research framing; [CMS2010_MPPR] for CPT14 modalities; [CMS2026_MRIanalysis] and [CMS2025_MRgFUS] for exclusions; [HHS2025_OPPS2026] for future 2026 codes; [CMS2015_ICD10] for era transition. Those do NOT validate patient-level use in TriNetX. Reference metadata: `docs/references/imaging_references.csl.json`, `.ris`, `.bib`, plus full code-level crosswalk.

## 6. Institutional pre-reconstruction acceptance gate

Before proposing *any* revised full-source clinical processing, use the
[authorizations and scientific evidence gate](RESEARCH_NETWORK_PRE_RECONSTRUCTION_GATE.md)
and the [one-pass request for the data steward](RESEARCH_NETWORK_DATA_STEWARD_REQUEST.md).
These list required DUA/IRB scope, legacy restricted Git-history review,
encryption/privacy boundaries, diagnosis and `IMP`/`EMER` semantics,
encounter/HCO ID scope, actual procedure code-system and performed/order
capture, observed complete calendar-year QA, age/sex policy, and disclosure
requirements. The pure planning gate never grants clinical-scan authorization.
The old Step45 full-data CLI **remains disabled**; if execution is later
approved, build an independently reviewed **new** bounded-memory extractor
for the revised A-primary/B-sensitivity phenotype.

## 7. What is done vs. still blocked

| Workstream | Decision or evidence state |
|---|---|
| Reference terminology & public CPT14 meanings | **Verified** (14/14 present, 3,270 references; no patient rows) |
| 13 extra CPT-like identifiers | **Completed code-meaning review**: 8 excluded, 5 unresolved source identities |
| Encounter/linkage and outcome separation | **Synthetic tests pass**; not validated on actual source |
| Research Network years 2016+ | **Provisional selection**, no observed clinical end year |
| Stroke Dx exact code scope, principal flag, HCO semantics, YOB uncertainty | **Still require institutional/clinical semantics QA** |
| Full performed-vs-ordered imaging, non-CPT mappings, availability across HCOs | **Unknown on clinical source** |
| Institutional data-use authority, historical Git exposure and disclosure protections | **Independent unresolved approval/governance gates** |
| Full-source rebuilt reconstruction and models | **Not run; old Step45 scan disabled** |

**Manuscript drafting:** The prospective [Methods and codebook scaffold](MANUSCRIPT_METHODS_CODEBOOK_SCAFFOLD.md) retains the stable citation keys without inventing results. **Next work:** A scientific manuscript codebook and methods section can be drafted against the cited **code meanings and transparent limitations**. Any actual utilization estimates require appropriately authorized local data-quality checks, the revised bounded-memory clinical extractor, crosswalk/source semantics validation and a governed disclosure plan. Continue to keep all private outputs Git-ignored and PR unmerged.

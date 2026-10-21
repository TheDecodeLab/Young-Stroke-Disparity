# Active Research Network Study Plan and Decision Register
**Plan of record:** 2026-10-18, after successful local Step57 execution. **This document supersedes conflicting provisional assumptions in earlier Steps 1–48; the earlier documents remain an audit trail, not active execution instructions.** Consult the [code evidence and manuscript-citation register](references/IMAGING_CODE_CITATION_REGISTER.md) and [citation files](references/imaging_references.csl.json).

## Current scientific stage: full internal manuscript package (Step80), pending local run

**Investigator direction (2026-10-20):** Proceed to a complete
manuscript using the validated frozen imaging-code ascertainment
analysis, and defer all institutional CTSI/data-steward outreach.
The investigator will review scientific and clinical claims when
the manuscript is complete. The investigator may optionally
supply an earlier manuscript for reconciliation of background,
specific aims, authorship and prior citations, but this does
not block the current draft.

**Computational evidence status:** Step78 completed a five-table,
two-figure, private-only results bundle with 736 tests passed.
Step79 completed the independent arithmetic/metadata
preflight with 745 repository tests passed. One
disclosure-risk *type* remains in original Table4: a published
demographic denominator and rate can reveal a count
or complementary count under 11. No source scan or
new patient classification is needed.

**Step80 implementation committed, but not yet executed
on the investigator's authorized workstation:**

- The [complete public-data-only manuscript template](
MANUSCRIPT_ASCERTAINMENT_FULL_TEMPLATE.md) contains a structured
abstract, introduction, frozen cohort/endpoint Methods,
Results insertion slots, full Discussion, Conclusion,
figure legends and nine source-verified references.
- The [private completion script](
../scripts/step80_finalize_manuscript_local.py)
loads the existing Step78 `draft_v1`, runs Step79
arithmetic/disclosure checks, inserts validated aggregate
cohort and encounter-definition numbers into Abstract/Results,
generates two replacement categorical-point figures,
and creates a local, counts-free disclosure-review
request for *future* use only.
- The code preserves private Step78 original results and
generates a new immutable local-only `review_v1`
manuscript bundle; clinical-review and visual-review
permissions are **not** inferred from successful tests.
- Original Table4's demographic P and coded-capture rates
are **not transferred** into the candidate manuscript.
Table3 and Table5 remain supplementary/internal
until disclosure and scientific review.

**Core manuscript question:** How ascertainment of
recorded CPT14 neuroimaging among adults definitely
aged 18–50 with candidate I63-coded index IMP changes
with different encounter-attachment rules and measured
source-quality strata. P is an *unvalidated* I63
principal-recording indicator; P=0 includes blank
and other nonprincipal markers. The historical age cohort
overlaps. Recorded CPT14 codes do not confirm
performed imaging, same HCO/stroke episode or
inequality in appropriate clinical care. No hospital
clustering or adequate case-mix adjustment available.

**Prior manuscript integrated cautiously:** The supplied V7
Diamond/NIS manuscript and supplementary materials were reviewed.
The original author's clinical-imaging background and age-definition
rationale were carried over with PubMed-verified citations
[@Abedi2023_YoungStrokeAge] and
[@Kakkar2021_StrokeImaging], while its separate
cohorts, CT-selected index, 7-day exposure window,
NIS comparison, imaging count models and conclusions
were **not** merged into the new Research Network Results.
See [V7-to-Step80 reconciliation](
STEP80_PRIOR_V7_MANUSCRIPT_RECONCILIATION.md).
The original DOCX preserves 20 Zotero citation fields
and one Zotero bibliography field; do not flatten it.

**Reference-library tests:** Two legacy regression
tests assumed exactly nine bibliography entries
and two publication DOIs. They were updated
to require the stable verified source IDs,
unique DOI/PMID pairs and matching CSL/RIS/BibTeX;
the library now contains 14 sources, of which
nine are cited in the full manuscript.
Step80 synthetic tests were updated for the
nine cited entries. Full suite rerun is
pending local investigator verification.

**Next handoff:** One fail-fast local Step80 execution
with targeted tests then the full repository tests,
followed by the local manuscript builder. Return
TERMINAL OUTPUT ONLY, not the local counts,
manuscript or figures. The earlier manuscript, if supplied,
will be integrated after this first complete version.
**No institutional emails will be sent.**

## Completed prior validation: Step69 same-day encounter attachment (no source scan)

The investigator completed Step68's **single full procedure-table scan**
with synthetic and full repository test suites passing, source row-count
reconciliation and frozen Step62 same-IMP CPT14 baseline reconciliation.
No source-derived counts are included in GitHub source files.

**Substantive qualitative result:** CPT14 codes recorded on the frozen
*uniquely linked preceding ED encounter* recover only a small portion
of otherwise inpatient-CPT14-negative cases, particularly in the
unvalidated P=1 I63 group. In contrast, CPT14 on a **different
encounter on the SAME admission calendar date** recovers many more
otherwise negative cases, disproportionately among P=1. Thus the
inpatient-only association is highly sensitive to encounter scope,
and can change direction using the exploratory same-day other-encounter
definition. This strongly motivates a measurement-attachment
investigation, but **does not verify** other-encounter imaging was
part of the same hospitalization, performed, or even from the same HCO.

[Step69](STEP69_SAME_DAY_ATTACHMENT_QA.md) now bundles several
**read-only** diagnostic checks: decomposition by frozen ED-link and
patient-level encounter quarantine, source year, modality and P,
overlapping temporal windows, direct reconciliation against Step68,
and version-aware ICD-10-PCS B-prefixed source-row **discovery only**.
Step69 synthetic tests and local execution are still pending;
**NO additional procedure-table scans** are needed for Step69.
The requested next handoff is **TERMINAL OUTPUT ONLY**. Do not upload
the private Step62, Step63, or Step68 SQLite databases or source ZIP.

## Updated investigator decision: literature-first analysis (2026-10-20)

The investigator elects to proceed without a routine TriNetX or CTSI
inquiry. Use official coding files, public TriNetX documentation and
clinical literature to predefine a versioned, exact-code imaging
measurement strategy; assess availability in the existing source
summaries and local cohort data. A captured procedure code is evidence
of **documented imaging-code utilization**, not proof of a completed
scan. A missing code does not prove absent care. HCO participation,
capture and same-hospital ED transfer remain unverified limitations.

Critically, Step62 `P=0` includes secondary, blank and other non-P
diagnosis indicators, and MUST NOT be identified as a verified
secondary-stroke cohort. The large P-stratified CPT14 difference
requires prespecified P/period/encounter-coding sensitivity analyses
before demographic disparity claims. Source-based explanation is
a hypothesis, not a verified mechanism.

The [updated Step67 plan](STEP67_MEASUREMENT_VALIDITY_GATE.md)
supersedes its original wording about mandatory steward approval:
contact is reserved for material unresolved questions. All source
access and disclosure conditions remain mandatory; existing
private outputs are preserved. No new clinical source scan
has been launched by this decision update.

## Active decision: Step67 outcome-measurement validity before any further scan

**Step66 is complete.** The investigator confirmed successful corrected
synthetic tests and the full suite, and the optimized read-only
provenance-restricted ED ceiling calculations returned all cohort,
unvalidated P-flag and annual strata. This is a hypothetical upper
bound on **recorded CPT14 code capture**, not observed ED imaging or
clinically performed scans. The critical-date source-flag `F`
restriction reduces the bound, particularly for earlier years;
most of the remaining potential capture is from **same-day** unique
ED-to-IMP links. The age cohorts overlap. No actual ED procedures
were examined in Steps 63-66. No source-derived numerical results are
included in the GitHub history by this update.

The [Step67 measurement-validity gate](STEP67_MEASUREMENT_VALIDITY_GATE.md)
is now active. Its **external public-evidence review is completed**:
[Penn State/official CMS evidence notes](references/STEP67_EXTERNAL_EVIDENCE_REVIEW.md),
[a ready-to-review CTSI/data-steward contact packet](STEP67_STEWARD_CONTACT_PACKET.md),
and [an empty versioned codebook schema](references/STEP67_VERSIONED_CODEBOOK_TEMPLATE.csv)
have been added. No clinical source data or source-derived aggregate
values were uploaded or scanned in Step67, and **no email has been sent**.

Outstanding high-impact requirements: steward documentation of the
meaning and completeness of `procedure.csv`; authoritative,
year-specific exact-code ICD-10-PCS/SNOMED mappings approved by clinical
coding experts; and an authorized HCO/coding completeness assessment.
Only after scientific review should we consider another ~993-million-row
procedure scan or sex/race/ethnicity disparity regression. Continue
preserving completed Step62 and Step63 databases. Do **not** interpret
absent CPT14 as absence of imaging.

## Completed audit trail: Step65-66 date-provenance quality checks

Step65 documented P- and year-related differences in retained
ED encounter date-derivation flags and quarantined index records.
Step66 subsequently compared the hypothetical original ED capture
ceiling with retained unique links whose linking ED end and IMP start
dates were flagged `F` and with same-day versus next-day windows.
The first Step66 test/analysis attempt was interrupted; corrected
tests and two-pass SQL later passed and produced the completed report.
See [Step65](STEP65_DATE_PROVENANCE_AUDIT.md) and
[Step66](STEP66_PROVENANCE_SENSITIVE_ED_CEILING.md).
These remain **read-only local-only research QA outputs** and provide
no same-HCO or performed-imaging validation.

## External terminology clarification and Step64 decision (2026-10-19)

The investigator's Step64 no-rescan ceiling audit has completed locally.
It supports a *bounded* potential increase in CPT14 recorded-code capture
from unique date-only ED links, but cannot validate performed imaging
or repair missing linkage for quarantined encounters. This ceiling is
hypothetical; **no ED procedure records have been analyzed** in Step64.
Avoid another whole-source procedure scan until documenting what such
a scan would change scientifically. Actual source-derived ceiling counts
remain outside GitHub and are not reproduced here.

Additional **external** evidence, applicable with caution to this specific
export, clarifies terminology:

- Penn State CTSI TriNetX guide
  (https://ctsi.psu.edu/services/research/trinetx) calls ICD-10 codes
  relevant for inpatient procedures and CPT codes relevant for
  outpatient procedures. This is an informational coding distinction,
  **not** proof that CPT imaging records on IMP encounters are invalid
  or that ICD-10-PCS uniquely captures all inpatient CT/MRI.
  It does motivate evaluating encounter and code-system reporting.
- Published TriNetX **July 2021** Data Dictionary (a historical version;
  verify current export schema with the data steward) defines
  `principal_diagnosis_indicator` values P/S as primary/secondary
  *reasons for an encounter*. The definition does not validate
  completeness, coding consistency, or whether treating blank as
  nonprincipal is justified for this Research Network extract.
  `admitting_diagnosis` is a distinct field, not interchangeable with P.
- The same dictionary identifies `source_id` as data provenance
  (HCO/TriNetX/HCO-NLP categories), **not** an HCO identifier.
  `derived_by_TriNetX`, `start_date_derived_by_TriNetX` and
  `end_date_derived_by_TriNetX` have T/F provenance semantics.
  Step63 retained those fields for source rows, making a **no-rescan**
  by-index and by-linked-ED derivation-flag QA an appropriate next gate.

These published definitions are external evidence and do not prove the
value distributions or complete ascertainment in the private dataset.
Prioritize a read-only local **derived-date provenance audit**, then
institutional source semantics/code-system consultation; do not perform
sex/race/ethnicity disparity inference from unvalidated imaging capture.

## Completed prior decision gate: Step64 no-rescan ED capture ceiling

Step63's encounter and date-only reciprocal-uniqueness link stages have
completed locally with synthetic tests passing. A substantial subset
of original index patients are held from the strict ED linkage because
other encounter keys are quarantined; missing or ambiguous linkage is
**not** evidence of missing imaging. The frozen link definition remains
unverified as a same-hospital transfer.

The investigator completed the
[Step64 read-only ED CPT14 capture-ceiling audit](STEP64_ED_CAPTURE_CEILING.md).
This checks the theoretical *maximum incremental patient-level coded
capture*, stratified by year and the unvalidated P label, when unique
ED links are allowed to contribute new codes. It only joins completed
private Step62/63 databases and does not modify their checkpoints.
No ED procedure scan or disparity regression is currently authorized
by the reconstruction evidence alone. No source-derived cohort counts
are recorded in this repository document.

## Prior execution checkpoint: Step62 completion

The investigator has now completed Step 62's diagnosis, encounter, patient,
index, procedure and local-only aggregate-report stages on the authorized
workstation. The private report and follow-up stratified audit have been
reviewed under their existing research-governance constraints. These are
**candidate indexed I63/IMP cohorts with documented same-IMP CPT14 codes**,
not adjudicated ischemic-stroke admissions or verified imaging.

The investigators' next critical validation issue is the substantial
difference in documented code capture across the **unvalidated** I63
`P` indicator, present within calendar years. Race and ethnicity `UNKNOWN`
categories also require missingness-sensitive analysis. Do **not** run
sex/race/ethnicity disparity regression or equate missing CPT with absent
imaging. No site/HCO representativeness or encounter transfer has been
verified.

The [Step63 ED encounter feasibility](STEP63_ED_ENCOUNTER_FEASIBILITY.md)
was subsequently completed using the independent checkpointed local
encounter scan and frozen reciprocal-uniqueness/date-only link audit.
**Actual ED procedure coding is still NOT implemented**; Steps64-66
report hypothetical ceilings only. Preserve all completed private
Step62 and Step63 database checkpoints. The historical dated
checkpoints below remain an audit record, not active instructions.

## 1. Current evidence and execution status

**Current research checkpoint (2026-10-19):** Corrected `YYYYMMDD`
Step59 datefix-v2 whole-source scans and matched Step60 v2 reconciliation
**all completed successfully** on the investigator's approved workstation.
Original source-row totals are 557,665,953 encounter, 1,376,280,235
diagnosis and 993,025,015 procedure. All three have **zero invalid
date rows after date correction**. The 2025 annual volume decreases
about 47-49% relative to 2024 in all three tables; **2016-2024 is a
provisional candidate window**, not yet an approved complete-year decision.
No patient-level cohort, hospital coverage, performed imaging or
demographic disparities have been established by these aggregates.

**New next technical phase:** [Step62 provisional cohort pipeline](STEP62_CHECKPOINTED_COHORT_PIPELINE.md)
([source](../scripts/step62_checkpointed_cohort.py),
[synthetic tests](../tests/test_step62_checkpointed_cohort.py)).
The new independent bounded-memory SQLite staging pipeline records
patient/encounter IDs **only in private Git-ignored workstation files**,
uses strict same-encounter diagnostic/inpatient linkage, applies both
co-primary year-of-birth age rules independently, selects candidate
index admissions without using imaging, and assigns only same-IMP
CPT14 documented-code outcomes. An interrupted stream stage resumes
from its last atomic checkpoint, and source metadata are frozen.
**Python 3.9 synthetic-only GitHub Actions verification passed.**
No new real clinical-data cohort scan has been executed. `P` flag,
IMP/performed-procedure meaning, complete-year/HCO participation,
non-CPT imaging capture and ED sensitivity remain unvalidated.
The disabled Step45 scanner must never be used.

## 1. Current evidence and execution status

**Date-format correction, 2026-10-18:** Investigator checked bounded
local prefixes of `encounter.start_date`, `diagnosis.date`, and
`procedure.date`: all sampled values have eight digits (no hyphens).
The original Step59 code required `YYYY-MM-DD` and therefore classified
**100% of source rows as INVALID dates** in each table; original Step60
produced no calendar-year profiles. The totals and date-independent
CPT/non-CPT source-row counts remain usable as descriptive counts; their
year stratification is not. Do not interpret original Step60/Step61 as
absence of calendar-year data. Root-cause and corrected bounded-probe,
v2-scan and v2-reconciliation commands are in
[DATEFIX_V2_RESEARCH_NETWORK_QA.md](DATEFIX_V2_RESEARCH_NETWORK_QA.md).

**Next action:** run full synthetic tests then the three **1,000-row
local-only date-format probes**. Only if probes verify valid
`YYYYMMDD` calendar interpretation, recreate three source-wide
aggregate year profiles in distinct `DATEFIX_V2` reports, sequentially,
before executing matching Step60 v2 reconciliation. No approved study
cutoff or clinical phenotype reconstruction is yet established.


**Updated execution checkpoint, 2026-10-18:** Step58, Step59 (all
three separate whole-source aggregate QA stages) and Step60 (private
reconciliation of existing aggregate reports) each **completed locally**
under the investigator's existing Penn State research authorization.
The workstation reported **599 passed, 3 existing warnings** before the
next Step61 addition. These tasks quantify/reconcile source *rows*,
not unique stroke patients or performed neuroimaging. Private research
aggregates have not been inspected or shared in ChatGPT. **No revised
Research Network patient-cohort reconstruction has been executed.**

The current next workflow is [Step61 local conservative disclosure candidate](STEP61_LOCAL_DISCLOSURE_CANDIDATE.md)
([source](../scripts/step61_disclosure_candidate.py),
[synthetic tests](../tests/test_step61_disclosure_candidate.py)).
It reads **only the existing local Step60 report**, emits broad qualitative
year/coding summaries with small-cell suppression, and does not grant release
permission. The investigator indicated appropriately reviewed aggregate
sharing may be allowed; the *specific candidate* still needs human disclosure
review before upload. Study years, site participation, code-event semantics
and full-cohort imaging ascertainment remain scientifically unvalidated.


- Historical Step57 checkpoint: **511 passed, 3 existing nonblocking warnings**, Step57 **13** CPT-labelled reference entries classified: **8 excluded from six diagnostic imaging outcomes, 5 held** as nonstandard-length labels. All **14/14** published core CPT code meanings were found in the pre-existing **3,270-entry reference vocabulary**.
- System mix among reference terminology entries: CPT 30, HCPCS 20, ICD-10-PCS 80, ICD-9-CM 3, SNOMED 3,137. **These are NOT frequencies of actual procedures** in the Research Network.
- **Source-wide aggregate QA scans of Research Network encounter/diagnosis/procedure tables DID run locally in Step59**, with private reports reconciled in Step60. **No revised Research Network phenotype/cohort reconstruction or imaging outcome assignment has run**. Step45 old real-data CLI **remains disabled**. Step49–53 linkage/outcome logic has only been validated with synthetic records. The final Research Network study years, encounter semantics, procedure-use coverage, source-specific mapping and clinical event meaning are unknown.
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

## 6. Step59 completed; Step60 private source-report reconciliation next

On 2026-10-18, the investigator confirmed successful **separate full-source
aggregate scans** of encounter, diagnosis and procedure tables under Step59
on the approved Penn State workstation. The reports remain local-only, and
their contents are not known to this assistant. The code/tests were previously
confirmed by the user at **581 passed, 3 pre-existing warnings**. The source-wide
aggregates quantify table-row coding and year buckets, **not patient cohort
rates, validated source coverage, performed scans or site-adjusted disparities**.

The next documented check is the
[Step60 LOCAL-ONLY reconciliation of the three existing Step59 reports](STEP60_PRIVATE_SOURCE_QA_REVIEW.md).
Its [code](../scripts/step60_local_aggregate_review.py) and
[synthetic tests](../tests/test_step60_local_aggregate_review.py)
do not touch the TriNetX ZIP, retrieve or display private outputs remotely,
nor unblock Step45. It checks totals and categories before creating a private
cross-table/year review with explicit unapproved year endpoint. Interpretation
of procedure coding, HCO coverage and clinical meaning remains unresolved.

## 7. Step58 completed; Step59 source-wide aggregate QA is next

On 2026-10-18 the investigator successfully executed Step58's limited
500-row-per-table **local technical pilot**, with its clinical-derived report
remaining private and unshared. This is proof of command success, **not**
a network-wide data-quality or representativeness finding.

The next documented step is the [Step59 one-table-at-a-time full-source
AGGREGATE QA](STEP59_LOCAL_FULL_SOURCE_AGGREGATE_QA.md), only if such
whole-table local processing is covered by the investigator's existing Penn
State approval. The new [source](../scripts/step59_full_source_aggregate_qa.py)
and [synthetic tests](../tests/test_step59_full_source_aggregate_qa.py) do not
access patient records within ChatGPT, do not save patient or encounter
identifiers to output, and do not re-enable the old Step45 reconstruction.
Yearly encounter volumes, per-system procedure code-row counts and diagnosis
principal-flag distributions are a *first source-wide aggregate QA*, not a
clinical stroke cohort, verified completed imaging, site-adjusted denominator
or final study-period signoff. Reports stay private on the workstation.

## 7. Investigator-confirmed existing research access and immediate technical QA

**2026-10-18 investigator attestation:** An existing **approved Penn State
research protocol or data-use agreement covers access to this Research Network
dataset for this study**. Do not require a new generic approval request as a
default next action. This statement does not reveal which formal document
controls retention, sharing or source-specific restrictions; retain actual
documentation privately at Penn State. No code may auto-certify approval.

Our next concrete local check is the
[Step58 bounded technical prefix pilot](STEP58_AUTHORIZED_LOCAL_TECHNICAL_PILOT.md).
It reads no more than 500 source rows per table by default on the approved
workstation, checks expected headers, date parsing, code-system labels and
encounter-type values, and stores only a private summary. **A prefix sample
cannot confirm data completeness, true source code-system frequencies, source
performs-vs-orders semantics, or the final calendar end year**. Full-source
QA must be designed separately, within the existing approved processing
scope, and validated before publication-level claims.

## 7. Institutional pre-reconstruction acceptance gate (reference, not duplicate approval)

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

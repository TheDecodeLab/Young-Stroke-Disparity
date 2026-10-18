# TriNetX Research Network Reconstruction: Data Access and Validation Gate
**Plan of record:** 2026-10-18. This is the **single pre-reconstruction handoff** for governance and methodological validation. It is NOT an authorization, results report, or instruction to run the old Step45 scan. Read alongside the [active study plan](ACTIVE_RESEARCH_NETWORK_STUDY_PLAN.md) and [manuscript coding evidence](references/IMAGING_CODE_CITATION_REGISTER.md).

## What is already established

The investigator-confirmed estimand is documented imaging-code capture among index hospitalized ischemic stroke patients in **two overlapping co-primary cohorts** (all 18–50; historical men 18–52 and women 18–54). Imaging **A primary** = code from the CPT14 high-specificity core under the index `IMP` encounter within admission dates; **B sensitivity** = A plus provisional uniquely date-matched preceding `EMER` coding, 0–1 calendar days from ED end to IP start, with 0 and 2 day maximum-gap comparisons. The 14 CPT meanings are documented in official CMS sources. This **does not** prove an actual exam occurred.

**Diamond = 2018–2019. Research Network = proposed 2016-01-01 through its last adequately complete *observed* calendar year, end year currently unknown.** The patient/encounter scope, site identity and procedure-system usage are not demonstrated by the terminology-only review.

Most recent local code confirmation: **524 tests passed, 3 nonblocking warnings** at commit `c50c528`. Those tests are synthetic/reference-only and cannot authorize source use.

## Approval and evidence matrix

| Area | Specific evidence or response needed | Decision owner | Completion status |
|---|---|---|---|
| **1. Data-use authorization** | Data-owner/IRB or DUA decision allowing this named Research Network stroke/disparity analysis, local staging and aggregate reporting; scope, access, retention and permitted linkage | Institutional data owner / privacy/IRB | **PENDING** |
| **2. Secure work environment** | Approved encrypted volume, users/roles, audit controls, private processing boundary and destruction/retention policy | IT security / data owner | **PENDING CONFIRMATION** |
| **3. Historical repository review** | Review legacy Git history for restricted patient/terminology content, determine remediation and merging/public release status | Data steward / institutional privacy | **PENDING**; PR #1 remains draft |
| **4. Source provenance** | Original source archive and signed manifest identity; four core table schemas and counts, key scope and dataset coverage description; no upload | Data custodian / analyst | **PARTIAL**: metadata/header inspection only |
| **5. Observation period** | Year-by-year **observed** full-year admission/diagnosis/procedure coverage and possible HCO participation changes, date validity, source lag; independently reviewed eligible endpoint year | Data steward / statistician | **PENDING**; cannot assume 2025/2026 or 2018–2019 |
| **6. Encounter semantics** | `IMP` means inpatient admission and `EMER` means ED; fields `start_date`, `end_date`, timestamp granularity, transfers, discharge and missingness definitions | Data dictionary / clinical data steward | **PENDING** |
| **7. Diagnosis and principal flag** | Official `I63.*` inclusion, `H34.1` retinal separate vs cerebral-only, historic 433.x1/434.x1 sensitivity and what `P` means in diagnosis table; case ascertainment | Neurologist / terminology steward | **PENDING** |
| **8. ID and HCO scope** | Verify patient/encounter IDs unique/stable over sources, whether facility/HCO and parent/episode keys exist, cross-site collision rates and any reliable ED→IP transfer key | Data steward | **PENDING**. **Do not promote `source_id` to HCO** |
| **9. Procedure recording** | Does a `procedure.csv` record indicate completed imaging, an order, or billing/coding? Relevant code systems, year-version, date field and site-specific missingness | Data steward / radiology informatics | **PENDING** |
| **10. Imaging codebook** | CPT14 matches source CPT version as used; whether exact SNOMED/HCPCS/ICD-10-PCS mappings improve coverage, five seven-digit purported CPT labels held, year-aware 2026 changes | Terminologist / study team | **PARTIAL**: external meaning validated; actual capture not |
| **11. Demographic policy** | Year-of-birth age uncertainty and sex-specific boundaries, unknown sex/other labels, race/ethnicity missingness and analysis coding | Investigator / biostatistician | **PENDING** |
| **12. Reporting and disclosure** | Small-cell aggregation/suppression threshold, complementary suppression, allowable stratifications, data sharing/publication limitations, retention | Privacy/data owner / investigator | **PENDING** |
| **13. Resource and staging plan** | Approved bounded-memory design, encrypted scratch size, status/checkpoint validation and restart logic; separate code for new phenotype | IT / data owner / statistician | **PENDING** |

**A reported source-key absence is a *valid documented finding*, not a valid claim of verified linkage.** With no trusted site/episode key, the investigator's chosen B remains provisional date-only **sensitivity** and cannot be called confirmed same hospitalization.

## Required analysis QA once data-owner authorization is obtained

The following design specifies **future** local QA and its grain. It is not a command to run now, does not set a cutoff threshold, and cannot be inferred from the 3,270 terminology candidates.

| Private check | Unit / denominator | Main question | Why it matters |
|---|---|---|---|
| Encounter year and date coverage | Calendar year × (verified HCO only if available) × encounter type | Which **full years** have usable observed admissions and how do partial/missing years differ? | Cohort period and secular trends |
| Diagnosis capture | Year × coding system × encounter type × principal flag | Is principal `I63` valid and stable? Are legacy ICD-9 entries plausible? | Hospitalized stroke numerator/denominator |
| Procedure system utilization | Year × code system × encounter type × verified HCO if available | What share of **actual procedure records** use CPT, SNOMED, HCPCS, ICD-10-PCS or local codes? | CPT14 undercapture risk |
| Codebook event coverage | Year × coding system × imaging category | Does CPT14 represent most or a sparse subset of recorded procedures? Exact mapping and record-status audit needed | Imaging measurement bias |
| Procedure time and semantics | Candidate code × order/performed status × date validity (as authorized) | Are events completed examinations and correctly dated? | Misclassified outcome |
| Encounter-key quality | Patient-encounter key, duplicate/conflict and missingness rates | Are keys stable, unique and joinable across tables? | Wrong patient/encounter attribution |
| ED/IP matches and exclusions | Patient-episode candidates, reciprocity and 0/1/2-day windows | What fraction is unique vs ambiguous? Does availability vary by subgroup? | Sensitivity B uncertainty |
| Demographic/age capture | Each co-primary population, with YOB boundary and sex/race/ethnicity missingness | Is cohort eligibility and equitable capture assessable? | Denominator and disparity biases |
| Primary/sensitivity comparison | Each age cohort × approved demographic strata × modality | A recorded capture vs B recorded capture; no confirmed-transfer claims | Robustness of the estimand |

**Do not use raw patient rows, identifier-level joins, HCO micro-strata, or small unsuppressed counts in ChatGPT, GitHub, PR attachments or public artifacts.** All QA outputs belong to institutionally approved encrypted local storage and require disclosure review before sharing. Do not present reference-vocabulary frequencies as clinical-utilization frequencies.

## Explicit interpretation/analysis blockers

- **Critical: no institutional authorization evidenced for running the revised full archive.** This is a question for the institution, not a Boolean a script can grant.
- **High: actual CPT/procedure-system capture unknown.** Reference data (CPT 30, SNOMED 3,137, etc.) do not quantify clinical utilization; a CPT-only disparity comparison may partly measure differences in coding systems across hospitals.
- **High: inpatient/ED and HCO linkage semantics unverified.** The exact same encounter identifier supports the A definition only if identifiers and dates are valid; ED-to-IP date-only B must not be called a confirmed transfer.
- **High: the Research Network's end year and hospital coverage are unknown.** Selecting it from max date/export metadata risks truncation bias and calendar-year confounding.
- **High: outcome meaning and race/sex/site-dependent missingness unknown.** Terminology labels alone cannot prove a scan was performed.
- **Medium/high: age YOB uncertainty and diagnosis principal flag** require an explicit protocol and private validation before patient counts are estimated.

No numeric thresholds are prescribed without empirical baseline and clinical/data-owner acceptance. Review year/sex/race distributions and missingness before setting thresholds to avoid an arbitrary pass.

## How this gate is used

The pure [planning gate](../scripts/research_network_pre_reconstruction_gate.py) and its [synthetic tests](../tests/test_research_network_pre_reconstruction_gate.py) enumerate independent evidence categories. A reviewer can later reference **non-identifying** institutional decision IDs in a separately maintained private packet. Their mere presence never changes Step45 approval files or enables a real scan.

The function `coverage_window_candidate()` accepts **explicitly reviewed synthetic-style annual decision flags**, not clinical data. It only identifies a *provisional contiguous candidate* from 2016 and always reports that actual clinical end-year approval is false. Absence of an HCO key may be documented while retaining the provisional ED sensitivity interpretation. A completed checklist is still **independent-review-required**, not approved by the script.

**Next actual dependency**: obtain the institutional decision on authorized purpose, local audit scope, site/encounter metadata and procedure recording, using the [one-pass data-steward request](RESEARCH_NETWORK_DATA_STEWARD_REQUEST.md). Only after those real decisions can a new bounded-memory local extractor be designed and separately approved; never reactivate the superseded Step45 scanner or pretend existing tests validated a clinical dataset.

Leave draft PR #1 **unmerged** until the legacy history privacy review.

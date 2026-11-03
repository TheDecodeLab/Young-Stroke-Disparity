# One-Pass Data Steward / Institutional Review Request (Working Template)

> **Optional clarification document (2026-10-18):** The investigator
> confirms existing Penn State protocol/DUA access covering this study.
> This template is **not** a mandatory application or next step. Use it
> only for data-dictionary ambiguity, procedural meanings, allowable
> disclosure or any remaining agreement-scope questions. The immediate
> local technical next step is
> [Step58](STEP58_AUTHORIZED_LOCAL_TECHNICAL_PILOT.md).

**Study:** Disparities in documented neuroimaging among adults hospitalized with young-onset ischemic stroke, using the TriNetX Research Network export.

**Purpose of this handoff:** Request the data owner and appropriate institutional reviewers to make **specific, documented decisions** needed before the team runs the revised full-cohort reconstruction. This public template contains no patient records, institution-specific authorization IDs, data paths or source-derived code descriptions. Complete the actual request in an institution-approved private communication channel.

## Short request

We plan an observational analysis of neuroimaging documentation among hospitalized young stroke patients in the Research Network, separate from our earlier Diamond study. We propose to select index inpatient ischemic stroke admissions from **2016 through the last adequately complete available calendar year**, with two overlapping co-primary age definitions (all 18–50; historical men 18–52 and women 18–54).

The investigator has specified a **primary inpatient-only documented imaging-code outcome** (exact same `IMP` encounter). The **ED-inclusive outcome is a sensitivity analysis**, using unique same-patient date-adjacent ED `EMER` and inpatient `IMP` encounters and clearly labeling the ED link *provisional* absent a verified site/episode key. We have external CPT code definitions but **have not established the actual source procedure-record semantics**. No newly scoped full clinical-data analysis is requested without permission.

Please clarify the following, and confirm the governance process that would authorize approved **local-only** source QA and a subsequent new bounded-memory cohort reconstruction.

### Governance and security decisions

1. Is this study purpose, the relevant Research Network export and the proposed local analysis (including diagnosis, procedure and encounter linkage, and adjusted demographic comparisons) covered by an existing approved DUA/IRB or other authorization? If not, what approval path is required?
2. Is local use of encrypted private staging tables, one complete sequential read of each necessary source table where approved, de-identified/aggregate QA and retention governed by the institution's security rules? What limits apply to HCO-level counts, outputs, access, retention and publication?
3. What institutionally approved process should review any restricted research data possibly present in earlier Git history before this draft branch is merged or released?

### Data dictionary and scientific semantics

4. In this export, what exactly do `IMP` and `EMER` indicate? Are encounter `start_date`/`end_date` admission/discharge/first-last coding dates, and are they only calendar dates? What proportion may be missing (to be quantified **only after** authorization)?
5. What is the scope and stability of `patient_id` and `encounter_id` across data sources and HCOs? Is any verified HCO, facility, parent encounter, transfer or hospitalization-episode key available through export metadata or another approved mapping? **`source_id` must not be assumed to be HCO**.
6. What does `principal_diagnosis_indicator=P` mean for the specific diagnosis table? Is diagnosis associated with an inpatient stay vs an ED event? Are ischemic stroke I63 codes and retinal artery occlusion distinguishable? Are ICD-9 entries meaningful for modern U.S. service dates?
7. In `procedure.csv`, does an entry represent a completed examination, an order, a claim, a reported result or a mixture? What are the supported code systems/versions (CPT, SNOMED, HCPCS, ICD-10-PCS, local codes), and can modality codes map to actually documented studies? Can the source identify imaging modality and anatomy independent of billing codes?
8. Is a validated research-compatible **year-by-year coverage/participation** report available to identify the last complete calendar year and changes in the contributing hospitals over time? Is it permissible to calculate a private year × code-system × visit-type coverage audit under the approved protocol?
9. Is there more precise age information than year of birth? If not, what age-boundary and sex-category coding choices are institutionally and scientifically defensible?
10. What are the required aggregate disclosure rules (minimum cell sizes, complementary suppression, output review, and external collaborator access restrictions)?

### Requested deliverables (no patient extracts)

Please provide or identify the **authorized location** of (a) applicable DUA/IRB/data-owner decision(s), (b) code-system and encounter data dictionary, (c) HCO/parent episode identifier documentation or confirmation of absence, (d) rules distinguishing performed studies from orders or reports, and (e) permissible aggregate QA and reporting thresholds.

We do **not** request patient-level files by email or GitHub, public row-level outputs, access to additional source systems without governance, or preemptive activation of the disabled full-scan pipeline.

## Internal team decision record (to complete privately, not commit)

- Governance authority, decision IDs and approval scope: **pending**
- Intended source and identifier scope: **pending**
- Permission for bounded local data-quality pass: **pending**
- Permission for later cohort reconstruction and modeling: **pending**
- Workstation and storage authorization: **pending**
- Encounter / episode / site and procedure semantic documents: **pending**
- Source complete-year and coding-system coverage assessment: **pending**
- Demographic handling, ischemic stroke code scope and disclosure plan: **pending**
- Legacy repository-history privacy clearance: **pending**

**If reviewers cannot verify a hospital/episode key**, do not force a false linkage: retain A primary, label B **unverified date-only sensitivity**, and make that limitation explicit in the manuscript. If CPT procedure capture is inadequate or variable by hospital, the planned study must report this and consider validated non-CPT code sensitivities or revise the estimand before running disparity models.

For the complete decision matrix and precise post-approval private QA specification, see [pre-reconstruction gate](RESEARCH_NETWORK_PRE_RECONSTRUCTION_GATE.md). This request itself **does not constitute approval**.

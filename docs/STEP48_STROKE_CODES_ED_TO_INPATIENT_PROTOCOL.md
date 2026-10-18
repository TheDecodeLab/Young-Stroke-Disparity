# Step 48: Study phenotype expansion and emergency-to-inpatient linkage (design + synthetic code only)

**Status: Research-backed protocol amendment, unapproved for source-wide real-data execution.** `scripts/step48_reference_stroke_ed_policy.py` contains pure/testable rules. It does not read the Research Network ZIP, perform clinical extraction, infer HCO identity, or approve any patient record.

## Investigator directions recorded

- Use literature-supported and verifiable imaging code definitions; add imaging **sensitivity analyses** for narrower and broader review-supported code sets.
- Use `IMP` as the working inpatient type because the source reference terminology labels it **Visit: Inpatient Encounter**, subject to data-quality confirmation of its practical use. Include an emergency (`EMER`) encounter when it precedes/converts into an inpatient `IMP` episode. Imaging performed during that linked ED episode should contribute to the hospitalization imaging outcome.
- Consider the supplied stroke code families: ICD-9 `433.x1` and `434.x1` (the user's example table refers to 9 individual codes; the full 9-code list was not supplied), ICD-10-CM `I63.*` (the table refers to 118 individual codes; the full 118-code list was not supplied), and `H34.1` (central retinal artery occlusion).
- Preserve the **two co-primary age cohorts** (all sexes 18–50; original sex-specific men 18–52/women 18–54). Diagnosis policy and imaging sensitivity sets apply to *each*, without pooling overlapping patients.

## Evidence and careful limits

1. A directly relevant sex-disparities neuroimaging study used ICD-9 `433.x1`, `434.x1`, and ICD-10 `I63.xx`; it analyzed CTA, CTP, MRI, and MRA separately. This supports the case-family approach and imaging outcome families but **does not establish exact sensitivity/specificity in the Research Network** or validate every CPT, SNOMED, HCPCS or PCS code.
   - Boltyenkov et al., *Sex-based disparity in acute stroke imaging utilization and the impact on treatment and outcomes: 2012–2021*. https://pmc.ncbi.nlm.nih.gov/articles/PMC10840948/
2. A population-based study analyzed race, sex and age differences in use of CTA, MRI and MRA and found associations with age and care-center type. This supports explicit care-setting/site stratification rather than interpreting missing imaging codes as absent clinical care.
   - *Age, Sex, and Racial Differences in Neuroimaging Use in Acute Stroke*, AJNR. https://pmc.ncbi.nlm.nih.gov/articles/PMC7963631/
3. Administrative stroke algorithms have trade-offs. For ischemic `I63.*` inpatient records, one validation study found high predictive value but lower sensitivity under a principal-only rule than under an any-diagnosis-position rule. **This was a Taiwan claims/registry study, not external validation of TriNetX.**
   - *Performance of ICD-10-CM Diagnosis Codes for Identifying Acute Ischemic Stroke in a National Health Insurance Claims Database*. https://pmc.ncbi.nlm.nih.gov/articles/PMC7524174/
4. Acute stroke guidelines discuss urgent emergency assessment and advanced cerebral/vascular imaging. For our source, imaging events can happen **before** the inpatient encounter starts.
   - Powers et al. *2019 Update to the 2018 AHA/ASA Guidelines for Early Management of AIS*, *Stroke* 2019, doi:10.1161/STR.0000000000000211. https://pubmed.ncbi.nlm.nih.gov/31662037/
5. The AHA statement identifies central retinal artery occlusion as **retinal ischemic stroke**. Its imaging indications can differ from brain infarction. Therefore, honor the investigator's broad H34.1 inclusion request by keeping a broad phenotype comparison, but **report H34.1 as a separate retinal subgroup and a cerebral-only sensitivity cohort**; don't pool it invisibly with I63.
   - Mac Grory et al., *Management of Central Retinal Artery Occlusion*, *Stroke* 2021, doi:10.1161/STR.0000000000000366. https://pubmed.ncbi.nlm.nih.gov/33677974/
6. CMS specifies that U.S. providers transitioned to ICD-10 codes for services on or after **October 1, 2015**. Any 2018–19 `ICD-9-CM` diagnoses in a U.S. Research Network export should be counted and evaluated for source/mapping/data provenance before their use as contemporary AIS diagnoses.
   - https://www.cms.gov/medicare/coding-billing/icd-10-codes

These are literature/official-source support for *family definitions and study architecture*, not proof of every local code's meaning, hospital site capture, or performed-imaging status. Step46/47 source code review and the imaging-codebook signoff are still needed. The exact list of 118 and 9 diagnosis codes **has not been provided**; no count of unique eligible codes is verified by this protocol.

## Predeclared diagnosis policies (for implementation after audit)

- **Broad study phenotype:** code families from the investigator's table. Record `cerebral_ischemic`, `retinal_ischemic_H34_1`, and `legacy_icd9` tags independently. Do not count duplicate codes/diagnoses as independent people. Permit H34.1 in the requested broad phenotype only with a clear published distinction and separate retinal results.
- **Cerebral ischemic sensitivity:** `I63` subcategories, with ICD-9 433.x1/434.x1 only if validated as genuine contemporaneous events; exclude H34.1 from this sensitivity.
- **Diagnostic position:** principal-only versus principal+secondary or any-position **sensitivity**; do not use a synthetic `P` indicator as proof of true principal diagnoses until TriNetX source semantics are checked.
- **Period:** 2018–2019 incident/inpatient episodes. Audit/label ICD-9 rows separately because 2018/19 service dates postdate the U.S. transition.
- **Codebook version:** require a local exact 127-code inventory (9+118) if the investigator wants strict **individual-code** matching rather than prefix-family matching. The counts in the prompt do not reveal those individual codes; do not invent the 127 entries. Note that `H34.1` may or may not already be within the stated 118 depending on how the original code table was counted.

## Proposed ED → IMP episode definition

Different encounter IDs can represent the same patient arriving in the ED and then being admitted. For that reason, `patient_id+encounter_id` is a useful **within-record join key**, but not a complete **cross-encounter episode key**.

1. Candidate ED type = `EMER` and inpatient type = `IMP`. Confirm these meaning labels and confirm whether there is already an encounter parent/visit-group/admission identifier in the original export.
2. Same patient ID AND **verified same HCO/site** AND ED preceding inpatient admission on same/previous calendar day are **candidate links**, not clinically validated transitions. Date-only source timestamps cannot establish a true 24-hour interval.
3. Cross-HCO transfer, missing site identifiers, duplicate candidate ED visits, overlapping encounter records, absent admission dates, and multiple possible inpatient recipients must be marked **ambiguous** and not auto-linked.
4. `source_id` was previously observed differing between encounter/diagnosis/procedure tables and cannot be assumed to be an HCO/site key. Verify the stable site/HCO or parent episode key; do not infer one from `source_id` equality.
5. Once a unique ED→IMP episode linkage is defensible, define imaging coverage from the ED evaluation/start through inpatient discharge. Count ED and inpatient performed-code events toward the same **hospitalization** numerator, deduplicating at patient+episode+modality. Report separate ED-only, inpatient-only and combined modality capture. A ±2/3-day temporal window is a **sensitivity**, never proof of transfer.
6. Primary diagnosis inclusion and index selection must not depend on imaging. Do not merge stand-alone ED-only stroke visits into the *hospitalized* denominator unless a linked `IMP` admission exists. Ascertain stroke diagnoses in either linked encounter, with a sensitivity requiring inpatient principal code.

### Critical blocker in Step45

The present `scripts/step45_full_cohort_reconstruction.py` still supports only principal I63 ICD-10-CM in same `IMP` encounter, and only imaging recorded in that exact inpatient encounter. Running it for the newly agreed study would therefore produce **incomplete/misclassified stroke episodes and imaging**.

To prevent accidental execution of the outdated clinical phenotype, the Step45 **CLI real-scan path has been disabled** pending a reviewed Step49 implementation. Existing *synthetic tests and metadata-only `--zip` planning* remain available; no source scan is started. Do **not** set local Step45 approval JSON flags to true or issue `--stage --execute-full-scan` commands yet.

## Imaging sensitivity sets, proposed

- **A. Historical CPT14-anchor** high-specificity exploratory subset, distinguishing plain CT head (comparison only) from CTA, MRI, MRA. Exact code semantics still need documented verification.
- **B. Reviewed CPT** list (primary candidate if source coverage supports it), each with authoritative code descriptions/2018–19 validity and completed vs ordered meaning.
- **C. Reviewed CPT + additional systems** (SNOMED/HCPCS/ICD procedure code systems where local coverage and code semantics can be established), broader-sensitivity definition.

Need stable source-system denominators and missingness before comparing rates across sets. Do not automatically use all Step42 lexical candidates as an inclusion list.

## What is still needed

1. **Not immediate from the investigator:** If available, the exact list of 9 ICD-9 and 118 ICD-10 codes, or the source reference/table supporting those counts. Their exemplars already permit literature-supported candidate-family rules but **not proof of the exact expanded list**.
2. **Technical audit using metadata and eventually an institution-approved private diagnosis/encounter stage:** validity of `IMP`, `EMER`, principal flag, site/HCO encounter grouping, date-only timing, and transition ambiguity. No additional random independent clinical file prefixes.
3. **Clinical/review and data-use approvals:** documented imaging-code sets, permitted staging/privacy disclosure and full-source execution clearance.

The draft PR must stay unmerged pending legacy Git-history data-exposure review. No patient rows, codebooks or private terminology descriptions should be published in this repository.

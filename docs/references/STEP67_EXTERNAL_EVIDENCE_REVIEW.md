# Step 67 | External evidence review and unresolved measurement questions

**Reviewed 2026-10-19.** Public desk review only. No research-data
download, ZIP rescan, participant-level analysis, or external email sent.
This is supplementary to [Step67 decision gate](../STEP67_MEASUREMENT_VALIDITY_GATE.md)
and [the active study plan](../ACTIVE_RESEARCH_NETWORK_STUDY_PLAN.md).

## 1. What authoritative sources establish

| Claim | Public evidence | Evidence strength | Consequence |
|---|---|---|---|
| Penn State differentiates the **TriNetX Research Network** from **Diamond claims** data; Research Network datasets are primarily de-identified EHR-derived data, not primarily insurance claims | Penn State CTSI, [TriNetX Database Guide](https://ctsi.psu.edu/services/research/trinetx), sections "What kinds of data...", "Where do data...", and network definitions | Official institutional description of network, not proof of each row | Do not label `procedure.csv` as verified claims/billed service data; avoid calling the absence of a CPT code no imaging |
| TriNetX receives and maps multiple sources into standardized terminology and may reject source records during quality checks | Same Penn State CTSI guide, section "How are data transformed from the source?" | Official description of processing, not a quantitative capture audit | Changes in coding availability might reflect source/mapping rather than clinical behavior |
| TriNetX Research downloads retain HCO anonymity | Same Penn State CTSI guide, "Regional Collaborative Networks" | Official operational statement | `source_id` is not a usable hospital key; ask whether an APPROVED completeness measure can be provided without defeating anonymity |
| Penn State provides ICD-10 inpatient procedure lookups separately from CPT outpatient procedure lookups | Same Penn State CTSI guide, "Code Lookups" | General usage guidance; NOT a rule excluding inpatient CPT observations | Consider exact ICD-10-PCS codebook and encounter/coding-system coverage. Do not assume every inpatient radiology exam appears in PCS |
| CMS describes ICD-10-PCS as the classification for inpatient procedures and publishes codes with effective discharge periods and updates | CMS [ICD-10 files](https://www.cms.gov/medicare/coding-billing/icd-10-codes) and [2016-2017 archive](https://www.cms.gov/medicare/coding-billing/icd-10-codes/icd-10-cm-icd-10-pcs-gem-archive) | Authoritative vocabulary definitions, not local TriNetX coverage | A calendar-year analysis 2016-2024 spans multiple ICD-10-PCS fiscal-year code sets; code validity requires discharge-date/version matching and relevant interim updates |
| CMS ICD-10-PCS includes an imaging section; CT and MRI are distinct operation families, not direct substitutes for CPT codes | CMS [2016 ICD-10-PCS reference manual](https://www.cms.gov/files/document/icd-10-pcs-reference-manual-2016.pdf), Imaging section; year-specific current tables from CMS | Classification concept only; clinical mapping must be verified by code and year | Treat central nervous system CT/MRI families as *discovery cues*, not approved codes. Avoid `B*` or prefix-only extraction for patient outcome |
| Published research has documented imperfect encounter capture in some linked TriNetX EHR cohorts | Anand et al., *Clinical Pharmacology & Therapeutics*, 2023, [doi:10.1002/cpt.3027](https://doi.org/10.1002/cpt.3027) | General external empirical caution; cohort, network and period differ | Do not transfer study estimates to our cohort. Motivates explicit data continuity and HCO participation QA |

## 2. What these sources do NOT establish for this study

1. That `procedure.csv` corresponds to clinically completed, billed,
   ordered, or source-specific combinations of examinations.
   The fact that the field is called `procedure` is not enough.
2. That all CT head / CTA / MRA / MRI brain exams are captured by
   CPT14 or by ICD-10-PCS Imaging section B in this Research export.
3. That an ICD-10-PCS procedure row can be treated as a one-to-one
   substitute for a CPT radiology procedure, or that every routine
   inpatient diagnostic imaging exam requires PCS reporting.
4. That HCO contributions, code-system mapping, or ED/IMP encounter
   representation are comparable across years, sex, race, ethnicity
   or the I63 principal diagnosis `P` indicator.
5. That `source_id` identifies an HCO, that date-only ED-to-IMP
   matches indicate same-HCO transfer, or that `derived_by_TriNetX=F`
   guarantees real-time clinical accuracy.
6. That unspecified/blank `principal_diagnosis_indicator` equals
   secondary stroke, or that `P` identifies an independently
   clinically adjudicated principal stroke.
7. That local Penn State data-access instructions authorize
   disclosure of the private research export or project aggregate
   tables; this is governed by the actual data-use terms.

## 3. Codebook design: exact, versioned and **not yet executable**

Preserve current Step62 CPT14 primary code capture **unchanged**.

Candidate ICD-10-PCS investigation should start with **published
year-specific exact code files**, then obtain clinical/coding signoff.
Do not autogenerate an outcome from the first three characters:
the PCS seven-character code includes operation, body-part,
contrast, qualifier, and related dimensions that may change
meaning. The 2016 reference-manual brain CT example is illustrative,
not evidence that this export contains it or that all `B02*` codes
describe a diagnostic brain CT.

The draft codebook must contain:
- coding system and official exact code (not a substring/prefix);
- official short/long description and source URL;
- valid effective start/end **discharge** dates, including any
  mid-fiscal-year revisions;
- target category (CT head, MRI brain, CTA head/neck, MRA head/neck,
  separately defined perfusion, or exclude/hold);
- evidence of body part, contrast, modality and diagnostic-vs-adjunct
  distinction;
- approved operational mapping version and reviewer, with clinical
  justification independent of mere code string structure;
- whether the TriNetX source can be shown to include this code,
  verified ONLY by an authorized, separate local QA.

Codebook field schema and blocked example rows:
[`STEP67_VERSIONED_CODEBOOK_TEMPLATE.csv`](STEP67_VERSIONED_CODEBOOK_TEMPLATE.csv).
The file contains **no approved executable ICD-10-PCS entries**.

## 4. Unresolved evidence to request from the steward

The two highest-impact questions are:

**A.** Does an imaging-related `procedure.csv` row represent a
completed diagnostic exam, an order, a reported/mapped billing code,
or a site-dependent mix? Can an expert provide a validated
proxy or approved sensitivity/specificity estimates?

**B.** Which exact code systems and procedure fields have adequate
coverage for inpatient and emergency diagnostic neuroimaging across
2016-2024? Can coverage or encounter completeness be quantified
without identifying individual HCOs?

Supporting questions: `P/S/blank` semantics and recording practices,
`IMP/EMER` capture, `principal_procedure_indicator`,
derived dates, `source_id` data-source categories, versioned PCS
tables, and whether a radiology result/order linkage can validate
exam completion.

Use [the focused contact packet](../STEP67_STEWARD_CONTACT_PACKET.md)
rather than exporting any of the original private reports.

## 5. Stop/go and burden

- **STOP now**: no additional full clinical procedure scan, no
  demographic disparity modeling, and no claim about performed
  imaging or hospital-level inequities.
- **GO with no clinical data**: confirm code-system definitions,
  collect steward/coding expert responses, assemble exact
  vocabulary tables by effective dates, and obtain review.
- **GO with clinical scan only after signoff**: check feasibility of
  a scoped checkpointed source procedure pass and validation of
  missingness, overlaps and events. Do not modify Step62/63.
- **If no defensible clinical imaging endpoint exists**, formally
  choose between reframing this as *documented-code capture*
  disparities (with strong limits) or using a different source.

## 6. Disclosure and repository integrity

The older draft branch has a known intermediate commit which
temporarily recorded source-derived local-only counts. Those
counts were removed from later file contents, but Git history
retains them. **Do not merge, export/share branch history or
force-push rewrite without a scoped institutional
disclosure/repository-impact review.** This source review
contains no new clinical aggregate values.

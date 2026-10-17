# Step 29: Clinical codebook review and fixed-data extraction decision

**Status: REVIEW REQUIRED. Not approval. No clinical data scan is authorized.**

## Preflight findings

The study-team Step 28 aggregate preflight confirmed:
- Original Diamond ZIP archive member fingerprint matched the completed private indexes.
- Original procedure table declares **1,166,493,611** rows.
- Previously reconstructed diagnosis-first age 19-50 denominator: **86,902** people.
- Exactly **14 candidate CPT codes**, with **all 14 pending clinical review**.
- No original clinical source rows scanned; execution remains blocked.
- Proposed primary temporal window: index date plus/minus 1 calendar day, with plus/minus 7 as the maximum extraction window.
- Candidate codebook SHA256: 96a68b9e6b285fd8c4ddd6fc66fd0041605260f21df50206ca6b6e78cf371f57.
- Archive member signature SHA256: 66380d6f8676a8c024be71de6008aa2196ac798a46e2d3fcdc0049911c8c4513.

Fingerprints confirm the identity of the local source and candidate
codebook, **not** that any service or patient outcome is valid.

## Historical coding references

The 14 codes appear in pre-2018 CMS radiology listings; this verifies
historical plausibility, not completeness in the 2018-19 TriNetX export.
Review facility/professional duplicate charges, imaging site, modifiers,
procedure coding system, and version validity.

- [CMS 2012 diagnostic imaging list](https://www.cms.gov/regulations-and-guidance/guidance/transmittals/downloads/r2395cp.pdf)
- [2017 Federal Register on CY 2018 outpatient imaging composites](https://www.federalregister.gov/documents/2017/07/20/2017-14883/medicare-program-hospital-outpatient-prospective-payment-and-ambulatory-surgical-center-payment)
- [CMS historical imaging code list, effective 2011](https://www.cms.gov/Regulations-and-Guidance/Guidance/Transmittals/Downloads/R738OTN.pdf)

## Why head versus neck requires explicit review

| Recorded outcome | Candidate CPT codes | Anatomical meaning |
| --- | --- | --- |
| CT brain | 70450, 70460, 70470 | Head/brain structural CT |
| MRI brain | 70551, 70552, 70553 | Brain MRI |
| CTA head | 70496 | Cerebral/intracranial CTA |
| CTA neck | 70498 | Cervical vascular CTA |
| MRA head | 70544, 70545, 70546 | Cerebral/intracranial MRA |
| MRA neck | 70547, 70548, 70549 | Cervical vascular MRA |

**Two valid candidate analysis questions (choose ONE primary):**

1. **Intracranial/brain focused**: primary CTA head and MRA head
   separately; neck studies reported as secondary and combined
   head/neck vascular imaging only in sensitivity analyses.
2. **Whole neurovascular work-up focused**: primary any CTA head/neck
   and any MRA head/neck; report head-only and neck-only in secondary
   tables so neck scans are not mistaken for intracranial imaging.

CT brain and MRI brain remain separately reported in either design.

The expanded extractor saves exact code and code-system in a local
private database, permitting both anatomical classifications after
a single approved source scan. The historic limited SQLite cannot
reconstruct missing neck events without reading the existing ZIP again.

## Decisions to document before execution

| Question | Current status |
| --- | --- |
| Primary age/sex definition: 19-50 uniformly versus historical sex-specific upper limits | Pending investigator approval |
| Diagnosis definition: earliest observed principal I63 in 2018-19 | Pending clinical validation |
| Primary CTA/MRA definition: head only versus head + neck | Pending clinical approval |
| Clinical relevance of all 14 CPT codes | Pending clinical approval |
| HCPCS or ICD-10-PCS source codes with verified modality mapping | Not yet established |
| Primary temporal window (candidate +/-1 day), sensitivity 0, +/-3, +/-7 | Pending approval |
| Meaning of absent procedure record across Diamond providers | Unresolved source-capture concern |
| Race/ethnicity missing in >75% and implications for study claims | Not suitable for unqualified disparity inference |
| Institutional data-use and legacy public Git history disclosure | Requires authorized review |

**No investigator or clinician approval is implied by this memo or
by the passing Step 28 preflight.** A candidate codebook should
remain pending until actual review is documented in approved storage.

## Data availability and next work

The investigator confirmed that **NO new TriNetX data can be
obtained**. Work only with the authorized existing Diamond ZIP,
completed private databases and locally accessible documentation.

Do not trigger a 1.17-billion-row rescan until the outcome, exact
codebook, and data governance decisions are signed off. If the
team approves a new endpoint and complete enough code definitions,
the guarded Step 28 extractor can run ONCE and retain detailed
procedure codes privately for head-only, neck-only, and combined
analyses. If data capture remains uninterpretable, switch to a
methods/data-quality paper rather than unsupported clinical inference.

**This plan does not validate admissions, first-ever stroke, access
to imaging, or clinical treatment disparities. PR stays draft.**

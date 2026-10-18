# Step 54–55: Literature-based imaging code review, Research Network time policy

**Investigator direction, 2026-10-18:** perform this scientific coding review directly using published sources. **2018–2019 belongs to Diamond only**. Do not reuse that interval for the Research Network. Clinical literature review of a code's *meaning* is distinct from a Research Network procedure row representing a completed study. The latter has not been validated, so label all resulting estimates **recorded imaging-code utilization**, not verified completed imaging.

## Decisions from authoritative external coding sources

**CPT core: 14 exact, anatomically clear codes** (14 codes, six categories). External code meanings are sufficiently established for a **high-specificity coding-based main analysis**, subject to data-use authorization and source-system mapping audit. The current Study Step53 primary outcome remains **same inpatient encounter**, with provisional date-only ED linkage reserved for sensitivity analysis.

| Category | CPT codes | Scope |
|---|---|---|
| MRI_BRAIN | 70551, 70552, 70553 | Conventional anatomical MRI of brain (contrast variants) |
| CTA_HEAD | 70496 | Computed tomography angiography of head |
| CTA_NECK | 70498 | Computed tomography angiography of neck |
| MRA_HEAD | 70544, 70545, 70546 | MR angiography of head |
| MRA_NECK | 70547, 70548, 70549 | MR angiography of neck |
| CT_HEAD | 70450, 70460, 70470 | Conventional head/brain CT comparator (contrast variants) |

A [public, nonpatient, 14-row machine-readable CPT meaning codebook](STEP54_PUBLIC_CPT14_LITERATURE_CODE_MEANING_REVIEW.csv) is included in the repository; its entries are labeled evidence-supported **code meanings**, NOT verified performed-examination data.

**Primary external references**
1. CMS, *Diagnostic Imaging Code List*, effective 2011: https://www.cms.gov/regulations-and-guidance/guidance/transmittals/downloads/r738otn.pdf — explicit mappings for all 14 CPT codes. A historical code list is strong evidence of code meaning, not of universal source completeness or performed care.
2. CMS, *Medicare NCCI 2026 Policy Manual Chapter 9*: https://www.cms.gov/files/document/09-chapter9-ncci-medicare-policy-manual-2026-final.pdf — MRI brain 70551–70553 and related modality distinctions.
3. CMS, *Appropriate Use Criteria Advanced Diagnostic Imaging Code List*: https://www.cms.gov/files/document/r2404otn.pdf — includes brain MRI, MRA head/neck, head CT/CTA and procedure families.
4. Stroke imaging research context: Boltyenkov et al., *Sex-based disparity in acute stroke imaging utilization and the impact on treatment and outcomes: 2012–2021*, https://pmc.ncbi.nlm.nih.gov/articles/PMC10840948/ ; and *Age, Sex, and Racial Differences in Neuroimaging Use in Acute Stroke*, https://pmc.ncbi.nlm.nih.gov/articles/PMC7963631/ . These support modality choices and disparity research framing, not individual source code execution semantics.

**New 2026 coding:** CPT 70471 represents **combined CTA head and neck** from 2026-01-01. It cannot be forced into *only* CTA_HEAD or CTA_NECK; if verified as present in the study period, it should populate both categories using a future date-aware implementation. It is **not** part of the historical 14-code core. CPT 0042T (CT cerebral perfusion, used through 2025) was replaced effective 2026-01-01 by 70472 and 70473 for CT cerebral perfusion. **Perfusion is separate**, not a surrogate for CTA/MRA or regular CT head. Consider CTP as an optional separately reported secondary outcome only with correct year/version mapping, not an original imaging outcome.
- CMS 2026 update: https://www.cms.gov/files/document/annual-update-list-cpt-hcpcs-codes-effective-january-1-2026.pdf
- Federal Register 2026 imaging update explaining 70471, 70472, 70473 and deletion of 0042T: https://www.federalregister.gov/documents/2025/11/25/2025-20907/medicare-program-hospital-outpatient-prospective-payment-and-ambulatory-surgical-center-payment
- CMS CT perfusion coverage and code-replacement details: https://www.cms.gov/medicare-coverage-database/view/article.aspx?articleId=58223&ver=19

**Explicit non-targets:** 70554/70555 functional MRI is not equivalent to conventional brain MRI; 70540/70542/70543 MRI orbit/face/neck is not MRA neck or brain MRI; 70480–70482 orbit/temporal bone, 70486–70488 maxillofacial, 70490–70492 CT neck soft tissue are not plain brain CT or CTA neck. 93880/93882 carotid ultrasound is not CTA/MRA. These are excluded from the specified six modality indicators. The registry retains these codes as documented exclusions, rather than leaving an ambiguous lexical match.

**Other code systems:** Do **not** automatically convert SNOMED, ICD-10-PCS, ICD-9 procedure, or non-CPT HCPCS codes into the six outcomes by name resemblance or digit reuse. They may offer substantial additional Research Network coverage. A **broader code-system sensitivity** is worth developing when an exact concept map, code version/year and EHR source event meaning are available. Absence from the CPT core means **defer**, not known absence of imaging.

## Period correction: Diamond versus Research Network

| Dataset | Proposed inpatient index date policy | Status |
|---|---|---|
| **Diamond** | **2018-01-01 through 2019-12-31** | Fixed, carried from Diamond-specific design |
| **TriNetX Research Network** | **2016-01-01 through the last sufficiently complete observed calendar year** | Starting year is an explicit *planning decision* for the post-ICD-10 U.S. era; **ending year remains unknown** until approved full-data coverage/lag QA |

Use \`IMP.start_date\` to define the Research Network hospitalization year once inpatient \`IMP\` semantics are confirmed; define eligibility independent of recorded imaging. Don't substitute ZIP export date, latest source update date or oldest reference-terminology date for observed clinical completeness. Data coverage may differ by HCO, and network participation changes over time. Annual utilization and missingness/completeness must be audited in approved local data before asserting a usable last year. If coverage does not support a coherent 2016+ time frame, revise the preregistered window *before* interpreting disparities. If the investigator later wants pre-2016 events, plan a separately coded ICD-9 era analysis rather than merging incomparable eras.

The initial source-independent CPT core predates the proposed 2016 start; however, coding updates should remain version-aware and any future Research Network 2026 year needs a fresh full-year completeness decision. The source export might contain **no** 2026 care. Do not infer its clinical date range from publication history or from the source-terminology table.

## Automated local literature-based disposition of the full private inventory

This reproduces the review without requiring a neurologist to classify thousands of broad textual candidates manually.

\`\`\`bash
git pull --ff-only origin analysis-rebuild-phase1-audit
python -m pytest -q &&
python scripts/step55_private_literature_codebook_review.py prepare
\`\`\`

The Step55 command reads **only the already-prepared Step46 private reference terminology inventory**; it does not open the original Research Network ZIP or process clinical data rows. It assigns each reference candidate a status:

- \`core_exact_CPT_modality_candidate\`: one of the evidence-backed exact 14 CPT codes; externally credible anatomy/modality meaning.
- \`hold_CPT_external_vs_local_terminology_CONFLICT\`: an exact CPT anchor whose local terminology plainly conflicts with the published code meaning.
- \`extended_CTA_head_plus_neck_2026_only_NOT_CORE\`: combined CTA 70471, needs code-year applicability and dual-category support.
- \`CT_PERFUSION_SEPARATE_NOT_PRIMARY_CTA_MRA_MRI_CT_HEAD\`: CT perfusion code, year-aware, not silently included in the six outcomes.
- \`exclude_not_study_modality\`: clear alternative anatomy or functional imaging code.
- \`defer_CPT_not_in_literature_core\` or \`defer_unmapped_or_unverified_system\`: no externally verified exact mapping in this version; not automatically counted.

The command creates **three new owner-only files, without overwriting existing reviewer files or signoffs**, under \`results/phase1/full_reconstruction_private/imaging_review/literature_adjudication/\`:

1. \`all_reference_literature_dispositions_LOCAL_ONLY.csv\` — decisions across all reference candidates, identity hashes and evidence, no patient records or raw source descriptions.
2. \`CPT14_core_reference_matches_CANDIDATE_NOT_APPROVED_LOCAL_ONLY.csv\` — exact CPT core codes actually present in the private reference vocabulary.
3. \`literature_code_review_summary_LOCAL_ONLY.json\` — counts and missing anchor audit. Its counts are local reference statistics, NOT patient frequencies.

**Do not automatically invoke Step47 \`finalize\` for Research Network**: its old review sheet and hardcoded \`valid_for_2018_2019_yes_no\` column were designed for the Diamond period, while its target Step45 full-scan is obsolete. Step55 does not alter that pipeline, and never sets institutional approval booleans to true. The scientific code meanings can be defended without claiming a human signer approved source event semantics; a separate institutionally authorized audit must establish whether those actual EHR procedure rows mean an examination was documented as completed.

## Study-analysis interpretation and remaining independent checks

- The primary analysis is coded imaging on the selected IMP encounter, **not** confirmed images acquired. Provisional ED→IMP date-only linked imaging is sensitivity, with 0, 1, and 2 day windows.
- Preserve the two overlapping co-primary age populations (all 18–50; men 18–52 and women 18–54) without pooling.
- Qualify null procedure codes as **no imaging code observed**, not **imaging not performed**. Do not assume access to a complete imaging utilization capture system.
- No exact 9/118 individual stroke diagnosis code list was supplied; family-level definitions require a separate diagnosis provenance check.
- Unlike source-code meaning, hospital linkage, performed-versus-ordered status and missing source/HCO capture **cannot be settled from external literature alone**; avoid claiming such validation. Institutional data-use permission remains a separate question.
- Step45 real full-source scan stays hard-disabled. Draft PR #1 stays unmerged pending legacy Git-history research-data governance review.

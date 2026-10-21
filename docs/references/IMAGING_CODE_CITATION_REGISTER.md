# Manuscript Coding Evidence and Citation Register
**Verified / reconciled 2026-10-18.** Canonical study design: [current plan of record](../ACTIVE_RESEARCH_NETWORK_STUDY_PLAN.md). Machine-readable per-code map: [code-to-source crosswalk](CODE_TO_REFERENCE_CROSSWALK.csv). Zotero-importable library: [RIS](imaging_references.ris), [BibTeX](imaging_references.bib), [CSL-JSON](imaging_references.csl.json).

**Citation policy:** cite **what a code denotes** separately from **whether the Research Network contains, performs, or captures that clinical service**. The latter remains unverified. Code descriptors in this document are brief scientific paraphrases; official CPT text may be copyrighted by AMA. Source pages can change, so retain stable title, agency, transmittal/article or document ID and year, not just a hyperlink.

## A. Public core imaging code definitions

**[CMS2010_MPPR]** Centers for Medicare & Medicaid Services. *Multiple Procedure Payment Reduction (MPPR) on the Technical Component (TC) of Certain Diagnostic Imaging Procedures*. Transmittal 738, Change Request 6993; July 30, 2010, effective January 1, 2011. [Official CMS PDF](https://www.cms.gov/regulations-and-guidance/guidance/transmittals/downloads/r738otn.pdf), **Attachment 1, PDF p. 6**: directly lists **all 14 exact CPT codes** with CT head / CTA head and neck / MRI brain / MRA head and neck descriptions.

| Modality | Coded concepts | Primary published reference |
|---|---|---|
| CT_HEAD (comparator) | 70450, 70460, 70470 | CMS2010_MPPR |
| CTA_HEAD | 70496 | CMS2010_MPPR |
| CTA_NECK | 70498 | CMS2010_MPPR |
| MRI_BRAIN | 70551, 70552, 70553 | CMS2010_MPPR |
| MRA_HEAD | 70544, 70545, 70546 | CMS2010_MPPR |
| MRA_NECK | 70547, 70548, 70549 | CMS2010_MPPR |

**Use in manuscript:** Methods, "Procedure-code definitions", and Supplemental Table Sx caption. Correct phrase: "We defined *documented imaging codes* using CPT modality-specific code families ..." Do **not** assert observed scan completion or that no code implies no imaging.

## B. Eight examined CPT codes excluded from the six diagnostic categories

| Code(s) | Reason for exclusion from MRI_BRAIN / CTA / MRA / CT_HEAD | Source and reliability |
|---|---|---|
| 0398T | MRI-guided focused ultrasound **therapeutic ablation**, not diagnostic structural brain MRI; replaced by 61715 effective Jan. 2025 | **[CMS2025_MRgFUS]** [CMS A58323](https://www.cms.gov/medicare-coverage-database/view/article.aspx?articleid=58323&ver=12), 2025 revision R7: direct year change |
| 0865T, 0866T | Quantitative MR image analysis/postprocessing, possibly billed as adjunct to actual 70551–70553, not a substitute for a diagnostic acquisition | **[CMS2026_MRIanalysis]** [CMS A60245](https://www.cms.gov/medicare-coverage-database/view/article.aspx?articleid=60245), effective Jan. 2026: explicitly describes them as add-on codes |
| 61736, 61737 | Intracranial laser interstitial thermal treatment, not stand-alone diagnostic MRI despite MR guidance | AAPC CPT code pages [61736](https://www.aapc.com/codes/cpt-codes/61736), [61737](https://www.aapc.com/codes/cpt-codes/61737); public code pages, underlying precise descriptors/versions may need licensed AMA check |
| 61751 | Image-guided stereotactic brain biopsy/excision, not diagnostic scan | [AAPC 61751 code page](https://www.aapc.com/codes/cpt-codes/61751); licensed code descriptor not reproduced |
| 78814 | Limited-area PET with CT localization, not routine head CT or vascular CTA | [CMS A54953 diagnostic testing table](https://www.cms.gov/medicare-coverage-database/view/article.aspx?articleid=54953&ver=68), row 78814; official CMS current short descriptor |
| 78830 | SPECT with CT localization, not routine head CT or vascular CTA | Same [CMS A54953](https://www.cms.gov/medicare-coverage-database/view/article.aspx?articleid=54953&ver=68), row 78830 |
 
The **five seven-digit identifiers labelled CPT by the private source vocabulary** do not follow normal CPT code shape [AMA2026_CPTbasics]. Their *meaning and source-system identity are unknown*. The source-specific values were held locally and are **not copied to this public repository register**. Do not truncate, auto-include or clinically exclude them.

The AAPC entries are intentionally **supplemental web references**, not bibliographic records with invented publication years. When preparing a journal supplement, cite the stable CMS and AMA sources first; cite AAPC only if needed and check licensing/relevance.

## C. Year-dependent imaging coding

**[HHS2025_OPPS2026]** Centers for Medicare & Medicaid Services. *Medicare Program: Hospital Outpatient Prospective Payment and Ambulatory Surgical Center Payment Systems ...* Final Rule, *Federal Register* November 25, 2025, **Section 23, “Computed Tomographic Services (Head, Neck, and Cerebral Perfusion)”**. [Official govinfo PDF](https://www.govinfo.gov/content/pkg/FR-2025-11-25/pdf/2025-20907.pdf).
- 70471 = combined CTA **head and neck**, effective January 1, 2026. If source and service year support inclusion in *future broader imaging sensitivity*, both head and neck flags may be considered. **Not included in original CPT14 core**.
- 70472 = CT cerebral perfusion adjunct to concurrent CT or CTA. 70473 = CT cerebral perfusion without concurrent CT/CTA. 0042T = earlier CT cerebral perfusion, **deleted January 1, 2026**. All stay *separate* from simple CT_HEAD or CTA outcomes.
- **[CMS2026_CTP]** [CMS A58152](https://www.cms.gov/medicare-coverage-database/view/article.aspx?articleid=58152&ver=12) is secondary evidence of CTP changes. **Important nuance:** one CMS CTP coverage article says 70471 was subsequently removed *from that article's eligible-code list*. That is **not a deletion of the CPT 70471 code itself**. Use the Federal Register rule to define 70471.

**[CMS2015_ICD10]** [CMS ICD-10 Transition Moves Forward](https://www.cms.gov/newsroom/fact-sheets/icd-10-transition-moves-forward), October 29, 2015: U.S. claims transition October 1, 2015. Choosing 2016 as the start of the Research Network study is a **provisional investigator decision based on comparability**, not a date prescribed by CMS. Diamond's distinct 2018–19 period remains fixed.

## D. Biomedical articles for manuscript rationale, not codebook proof

**[Vagal2017_AJNR]** Vagal A, Sanelli P, Sucharew H, et al. *Age, Sex, and Racial Differences in Neuroimaging Use in Acute Stroke: A Population-Based Study.* AJNR Am J Neuroradiol. 2017;38(10):1905–1910. **DOI** 10.3174/ajnr.A5340; **PMID** 28838913. [PubMed](https://pubmed.ncbi.nlm.nih.gov/28838913/). Supports clinical justification for studying differences in advanced imaging and age/race/sex patterns; **not** claims about our data or current coding completeness.

**[Wang2024_JACR]** Wang JJ, Katz JM, Sanmartin M, Naidich JJ, Rula E, Sanelli PC. *Gender-Based Disparity in Acute Stroke Imaging Utilization and the Impact on Treatment and Outcomes: 2012 to 2021.* J Am Coll Radiol. 2024;21(1):128–140. **DOI** 10.1016/j.jacr.2023.07.015; **PMID** 37586470. [PubMed](https://pubmed.ncbi.nlm.nih.gov/37586470/). Note: a full-text repository has previously displayed an alternate “Sex-based” title. **The manuscript bibliography should use PubMed's “Gender-Based...” title**, not silently mix both.

**[Lewis2023_JAMIA]** Lewis AE, Weiskopf N, Abrams ZB, et al.
*Electronic health record data quality assessment and tools: a systematic review.*
J Am Med Inform Assoc. 2023;30(10):1730–1740.
DOI 10.1093/jamia/ocad120; PMID 37390812.
[PubMed](https://pubmed.ncbi.nlm.nih.gov/37390812/).
Supports background that EHR data completeness and quality require explicit
assessment; does not validate this research-network dataset.

**[Syed2023_JMIR]** Syed R, Eden R, Makasi T, et al.
*Digital Health Data Quality Issues: Systematic Review.*
J Med Internet Res. 2023;25:e42615.
DOI 10.2196/42615; PMID 37000497.
[PubMed](https://pubmed.ncbi.nlm.nih.gov/37000497/).
Supports general data-quality taxonomy and secondary-use caveats,
not a claim about clinical imaging access in this cohort.

**[An2025_JMIR]** An D, Lim M, Lee S.
*Challenges for Data Quality in the Clinical Data Life Cycle: Systematic Review.*
J Med Internet Res. 2025;27:e60709.
DOI 10.2196/60709; PMID 40266662.
[PubMed](https://pubmed.ncbi.nlm.nih.gov/40266662/).
Further supports the need for source-lifecycle data-quality verification.

## E. How to use the portable Zotero-ready library

`imaging_references.csl.json` is the canonical, internally keyed source metadata. `imaging_references.ris` can be imported into Zotero via File → Import; BibTeX is provided for reproducible citation managers/LaTeX. The stable keys (e.g., `CMS2010_MPPR`, `Vagal2017_AJNR`) are **project-local IDs**, not Zotero-generated item keys. Importing generates new Zotero item keys, and a future Word document requires Zotero Add/Edit Citation or valid linked Zotero fields; mere plaintext bracketed keys are **not functioning Zotero Word citations**.

Citation placement guide: Methods definition table → CMS2010_MPPR; exclusions → CMS2025_MRgFUS, CMS2026_MRIanalysis and the linked code sources; 2026-only coding → HHS2025_OPPS2026; coding era → CMS2015_ICD10; rationale/related literature → Vagal2017_AJNR and Wang2024_JACR.

**Unresolved evidence:** exact TriNetX procedure event meaning (performed vs ordered); actual code-system utilization and source/HCO coverage; HCO/ED-IP linkage; the final observation end-year. These cannot be cited as validated until an authorized source assessment exists. Keep draft PR unmerged and original Step45 full scan blocked.

# Manuscript-ready codebook and methods paragraphs (DRAFT, NOT RESULTS)

**Use only after the investigator, institution, and final data source checks confirm these methods were actually applied.** This draft records intended definitions and references. It must NOT be presented as a completed Research Network analysis. Citation keys point to [Zotero-ready reference exports](references/IMAGING_CODE_CITATION_REGISTER.md), not live Zotero Word fields.

## Background / rationale

Prior population-based research has found differences in advanced stroke imaging by age and race, with variation by the type of hospital. A more recent observational study also reported a sex-associated difference in CT angiography use among patients with acute ischemic stroke. These findings support investigating whether recorded imaging use differs between demographic groups, while recognizing that hospital characteristics and clinical case mix may contribute to such patterns. **Citations:** [Vagal2017_AJNR]; [Wang2024_JACR].

## Dataset and study period (prospective analysis description, not executed)

We plan to study hospitalized adults with ischemic stroke in the TriNetX Research Network. The proposed inclusion period begins January 1, 2016, after the United States transitioned to ICD-10 in October 2015. The ending year will be selected using the observed completeness of Research Network data and may differ by hospital. This time window is separate from the Diamond data analysis, which used 2018–2019. We will evaluate two overlapping, co-primary age definitions: patients aged 18–50 years and the historical definition of men aged 18–52 and women aged 18–54 years. We will account for uncertain age at admission when only year of birth is available. **Citation for U.S. coding transition:** [CMS2015_ICD10]. **The 2016 Research Network start is an investigator planning choice, not an externally demonstrated study result.**

## Imaging codebook and primary outcome

We propose to identify *documented imaging codes* using exact CPT definitions for MRI of the brain (70551, 70552, 70553); CT angiography of the head (70496) and neck (70498); MR angiography of the head (70544, 70545, 70546) and neck (70547, 70548, 70549); and conventional head CT (70450, 70460, 70470) as a separate comparison modality. The CPT definitions are recorded in a historical CMS diagnostic imaging code list. For the **primary analysis**, the numerator will include code records that share the patient's identifier and the index inpatient encounter identifier and fall within the inpatient encounter dates. The stroke hospitalization denominator will be selected independently of imaging. **Citation:** [CMS2010_MPPR], Attachment 1, PDF page 6.

A code recorded in an encounter is a measure of *documented imaging-code capture*. We will not describe it as confirmed image acquisition unless the source system's procedure-record status has been independently validated. The absence of a code does not establish that no imaging occurred.

## ED-inclusive and coding-system sensitivity analyses

The ED-inclusive sensitivity analysis will additionally count imaging codes from one preceding emergency encounter that can be uniquely matched to the same patient and has an end date on the admission day or previous calendar day. We will compare maximum matching gaps of 0, 1, and 2 calendar days. Because the current export lacks a verified same-hospital or shared-episode identifier, these remain **provisional date-only links**, not confirmed transfers. We will separately report ambiguous matches and missing encounter dates.

We will also examine the potential loss of documented imaging capture when analysis is restricted to the high-specificity CPT codes. This requires a separately authorized assessment of actual procedure-row code-system distribution and exact source mappings. Reference-terminology counts alone do not measure clinical use. Non-CPT mappings and completed-vs-ordered semantics are not yet established.

## Coding changes and exclusions

We excluded codes describing therapeutic surgery, image-guided biopsy, quantitative MR postprocessing without independently documented MRI, or nuclear imaging from the six specified diagnostic modality indicators. For example, 0398T represents MRI-guided focused ultrasound surgery and was replaced by 61715 in 2025. Codes 0865T and 0866T describe quantitative brain MR analysis rather than standalone diagnostic brain MRI. **Citations:** [CMS2025_MRgFUS]; [CMS2026_MRIanalysis]. The complete eight-code exclusion list and underlying URLs are in [the code-level reference table](references/CODE_TO_REFERENCE_CROSSWALK.csv).

For service dates beginning January 1, 2026, CPT code 70471 describes combined head and neck CTA; 70472 and 70473 represent cerebral CT perfusion, while 0042T was deleted. We will apply year-specific definitions only where the Research Network's available dates and code-system mappings support them. These codes were **not** silently added to the original CPT14 core. **Citation:** [HHS2025_OPPS2026] Section 23.

## Still required before a final Methods section

Confirm the final cohort period, HCO/coding coverage, principal ischemic stroke diagnosis semantics, year-of-birth boundary policy, encounters and links, actual coding-system use, codebook provenance and institutional approval for row-level analysis. Replace future-tense planned procedures with past tense **only after their documented completion**. Do not insert results, missingness estimates, adjusted odds ratios or site representation not derived from an authorized validated analysis.

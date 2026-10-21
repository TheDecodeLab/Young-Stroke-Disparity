# Encounter attribution substantially changes documented neuroimaging-code capture among young adults with ischemic-stroke diagnosis codes: an EHR research-network ascertainment study

**INTERNAL SCIENTIFIC REVIEW DRAFT — NOT CLEARED FOR EXTERNAL DISCLOSURE**

## Abstract

**Background:** Procedure codes are commonly used to identify healthcare services in electronic health record (EHR) research. However, codes can be recorded under different encounters, and missing codes may reflect incomplete data capture rather than absence of care. We examined how encounter attribution changes recorded neuroimaging ascertainment among young adults with candidate ischemic stroke.

**Methods:** We retrospectively identified definitely age-eligible adults 18–50 years with an ICD-10-CM I63-coded index inpatient encounter in a TriNetX Research Network extract from 2016–2024. The primary endpoint was at least one of 14 prespecified CT, MRI, CT angiography, or MR angiography CPT codes on the indexed inpatient encounter. Alternative recorded-code definitions included another encounter on the admission calendar day, a conservatively linked preceding emergency encounter, and a broader near-admission temporal screen. We examined differences by an unvalidated I63 principal-recording indicator (P) and descriptively standardized to common calendar-year and encounter-key-quality distributions.

**Results:** {{ABSTRACT_RESULTS}}

**Conclusions:** The measured occurrence and subgroup distribution of documented neuroimaging codes depend on encounter-attachment rules and source-recording characteristics. Broader calendar-day capture does not establish that a scan was performed during the indexed hospitalization. Studies using EHR procedures as imaging outcomes should explicitly define encounter attribution and assess recording quality before interpreting subgroup comparisons as clinical care differences.

**Keywords:** electronic health records; ascertainment; ischemic stroke; neuroimaging; administrative procedure codes; data quality; encounter linkage.

## Introduction

Head CT, brain MRI, CT angiography, and MR angiography serve different diagnostic purposes during stroke evaluation [@Kakkar2021_StrokeImaging]. Observational studies have described differences in neuroimaging use across demographic groups and clinical settings [@Vagal2017_AJNR; @Wang2024_JACR]. An important methodological distinction is that a coded record represents an observation in a data system; it is not necessarily confirmation that an examination was completed, and the absence of a code does not independently establish that no examination occurred.

EHR research networks integrate data generated for heterogeneous clinical and operational purposes. Data-quality reviews have emphasized that completeness, conformance, plausibility, and relationships between recorded elements must be evaluated in relation to the intended research question [@Lewis2023_JAMIA; @Syed2023_JMIR; @An2025_JMIR]. For procedure-based outcomes, the meaning of an observed code is inseparable from the encounter identifier, event date, available coding system, and degree of institutional data coverage. A patient may have emergency evaluation and hospitalization represented by different encounter records; without a trusted encounter-to-hospital linkage, joining them by date alone cannot establish that they reflect one episode of care.

These measurement concerns are particularly relevant when a reported utilization contrast changes with the definition of eligible records. A conservative same-inpatient-encounter endpoint can miss relevant imaging codes associated with earlier or differently recorded visits. Conversely, a broad same-calendar-day rule can add code records that do not belong to the same admission or institution. Each choice answers a different ascertainment question, and neither can automatically be treated as a gold standard for performed imaging.

We therefore examined the sensitivity of **documented neuroimaging-code capture**, rather than clinical imaging completion, to four encounter-attribution definitions among young adults with candidate ischemic stroke. Our objectives were to (1) quantify captured CPT codes on the frozen index hospitalization; (2) evaluate the additional capture associated with other same-day and uniquely linked emergency records; (3) assess whether differences across an unvalidated diagnosis-recording indicator changed under a common calendar-year and encounter-quality distribution; and (4) describe limitations of subgroup associations when clinical, institutional, and source-coverage information is unavailable.

## Methods

### Design, data source, and study period

We conducted a retrospective, observational ascertainment analysis of an investigator-held TriNetX Research Network export. The completed pipeline processed source patient, encounter, diagnosis, and procedure tables in earlier checkpointed stages. All analyses reported here were built from frozen, locally held indexed-cohort and procedure-capture checkpoints, not from subsequent extractions or rescans. Index inpatient encounters were restricted to starts between January 1, 2016, and December 31, 2024. The 2016 start follows the US implementation of ICD-10 in October 2015 [@CMS2015_ICD10]; the 2024 endpoint was selected provisionally after examining available year-level source coverage, not after an institutional site-completeness certification.

### Candidate stroke cohort and index encounter

We identified encounters recorded as inpatient (source type `IMP`) with a strict ICD-10-CM I63 or dotted I63.* diagnosis belonging to the same patient and encounter and dated within the recorded encounter interval. Such records represent **candidate** ischemic stroke, not clinically adjudicated acute cerebral infarction. Missing or reversed encounter intervals were not treated as evidence of absent imaging. Ambiguous competing earliest same-day candidate inpatient encounters were held rather than selected arbitrarily.

The primary cohort comprised adults **definitely aged 18–50 years** at index given the available birth year and encounter year. Where only birth year was known, definite inclusion required that the possible age range lie entirely within the specified limits; patients whose eligibility depended on an unobserved birthday were not assigned a fabricated exact age. Each eligible patient contributed one frozen earliest qualifying inpatient index within that cohort. A historical sensitivity cohort used 18–52 years for men and 18–54 years for women, reflecting a previous data-driven approach to defining young ischemic stroke [@Abedi2023_YoungStrokeAge]. We did not use those age limits for the primary endpoint. The historical and uniform cohorts overlap and must not be combined as independent samples.

### Documented CPT neuroimaging ascertainment

The primary binary outcome was the presence of any of 14 prespecified CPT diagnostic imaging codes attached to the same patient and the same frozen index inpatient encounter with a procedure date between the recorded admission start and end, inclusive. The published coding vocabulary included head CT (70450, 70460, 70470), brain MRI (70551–70553), CT angiography of the head (70496) and neck (70498), and MR angiography of the head (70544–70546) and neck (70547–70549). The code definitions are documented in the historical Centers for Medicare & Medicaid Services imaging-code reference [@CMS2010_MPPR]. This endpoint is referred to throughout as **documented CPT14 capture**. We did not equate a present code with a completed examination or a missing code with absence of imaging.

### Encounter-attribution sensitivity definitions

We evaluated four **separate patient-level binary definitions**, each retaining the same frozen indexed-patient denominator: (i) CPT14 documented on the index inpatient encounter; (ii) index inpatient capture or at least one CPT14 code under a different encounter on the **same calendar date as admission**; (iii) index inpatient capture or a CPT14 code from an emergency encounter conservatively linked to that index hospitalization; and (iv) index inpatient capture or codes identified under the broader pre-admission two-day through admission-day ED/other-encounter screen. The preceding emergency (source type `EMER`) linkage required a different encounter identifier, date compatibility, and reciprocal uniqueness among eligible emergency/inpatient candidates. The broader and same-day alternatives do not establish shared hospital identity or episode continuity. Patient-level code indicators were combined with logical unions to avoid double-counting within a definition.

### Source-recording indicators and analytic comparisons

We used a binary source diagnosis-recording indicator, `P`, for the presence of an I63 code marked principal on the indexed inpatient encounter. `P=0` includes secondary, blank, and other unmarked indicators, and **does not** define a clinically verified secondary-stroke group; `P=1` is **not** stroke severity. The encounter-key quality marker indicated whether **any** of the indexed patient's relevant emergency or inpatient encounter keys had conflicting or otherwise quarantined source dates/types. The affected key need not be the selected index encounter.

For each outcome, we calculated the percentage of indexed patients with a documented CPT14 code within each P group and the crude P=1 minus P=0 difference in percentage points. We additionally applied direct descriptive standardization using a pooled calendar-year × patient-level encounter-key-quality distribution, with common stratum weights for both P groups. This procedure assesses sensitivity to measured source-composition differences, **not** causality. We also examined year-only standardization and exclusion of patients with any quarantined encounter key in existing sensitivity diagnostics.

### Secondary demographic analyses

Previously completed grouped-binomial models explored recorded-code capture by sex, conservatively mapped race, ethnicity, calendar year, birth-year-derived age band, P indicator, and any-key encounter quarantine status. Missing and unmapped demographic values were not imputed as known groups. Marginal standardized contrasts and working-binomial/extra-binomial uncertainty diagnostics were generated, but there was no reliable hospital identifier for site clustering, no clinical severity measure sufficient for adjustment, and no verified imaging completion. These models were retained for internal measurement-methods evaluation and are not interpreted as estimates of racial or ethnic differences in clinically appropriate care. Disclosure-sensitive subgroup rates were **not** carried into this manuscript draft.

### Alternative inpatient coding-system feasibility

Separately, exact ICD-10-PCS title screens identified candidate CNS and head/neck vascular CT/MR code families. Observed PCS code rows represented source records across overlapping cohorts and possibly repeated procedures, not distinct CPT-negative patients. A deliberately generous algebraic upper bound showed that those selected PCS candidates alone could not eliminate the original inpatient P-group CPT14 contrast. The candidate codes remain subject to independent clinical anatomical, method, contrast, and fiscal-year validity review and **were not added to the patient-level primary outcome**.

### Quality control, uncertainty, and disclosure

The Step62/63/68 inputs remained read-only and were linked to frozen source signatures. Grouped source-QA aggregates and independent patient-level comparison counts were reconciled across code paths. The manuscript tables derive from a restricted local results bundle with explicit tests of numerator–denominator identities, nested outcome definitions, and model-estimate consistency. These tests support computational reproducibility, not validity of a clinical care endpoint. Institutional cross-table disclosure review is required before release. In particular, demographic category percentages that could reveal small event or complementary counts are withheld.

## Results

{{RESULTS_TEXT}}

## Discussion

In this research-network ascertainment study, the measured frequency of documented neuroimaging codes changed with the encounter definition, even though the patient denominators remained fixed. The direction and magnitude of group comparisons were sensitive to whether the analysis required a code on the indexed inpatient encounter or admitted records from other encounters near admission. These patterns identify a practical vulnerability in interpreting EHR procedure records: a measurement difference can arise from where the system stores a code, not necessarily from a corresponding difference in healthcare delivered.

The most defensible primary comparison uses procedure codes attached to the exact frozen index inpatient encounter, because its event attribution is defined at the same patient/encounter grain as the candidate stroke diagnosis. This decision improves reproducibility but may under-ascertain imaging documented on an emergency encounter or elsewhere in an episode of care. Our unique emergency linkage captures only records satisfying strict temporal and reciprocal-uniqueness rules; it therefore does not recover every potentially clinically related encounter. Conversely, broad inclusion of any different encounter on the admission date can capture additional CPT14 records but may incorporate records from a different setting, hospital, or reason for care. Thus a larger numerator under a broader definition cannot be treated as proof that the primary inpatient definition missed **performed** brain imaging.

The differences involving the P indicator underscore the potential consequences of administrative recording conventions. P was constructed from the source's principal-diagnosis flag and is not a validated stroke subtype, measure of clinical severity, or accurate partition of principal versus clinically secondary ischemic stroke. Because P=0 combines unmarked, blank, and secondary labels, strong contrasts between the groups may reflect patient selection, diagnosis recording, hospital mix, or other source practices. Descriptive standardization to the same year and any-key-quarantine composition can help reveal sensitivity to observable source mix; it cannot remove unmeasured institutional effects or create clinical comparability. The any-key quarantine marker is itself conservative and may refer to a record unrelated to the actual index stay.

Independent studies have reported demographic variation in stroke neuroimaging within defined populations [@Vagal2017_AJNR; @Wang2024_JACR], but those findings cannot be directly extrapolated to the coded-capture outcomes here. In our source, the sex/race/ethnicity analyses additionally faced unknown/unmapped category values, potential recording heterogeneity, and absent reliable hospital-clustered inference. Consequently, a demographic point-estimate difference in documented code capture should not be described as a difference in completed imaging or a disparity in clinically appropriate stroke care. More informative clinical comparisons would require a validated index diagnosis, actual study completion timestamps, site/episode attribution, indications, severity, and trustworthy demographic metadata.

The coding-system investigation provides a complementary negative result. ICD-10-PCS code descriptions can suggest candidate inpatient imaging families, but matching an anatomy phrase to a CMS catalog is not independent clinical validation. Because the source code profile counts procedures rather than newly captured patients, their maximum contribution to any patient-level expansion can be bounded without an additional full source scan. The resulting ceiling did not eliminate the index-inpatient P coding contrast when restricted to the reviewed PCS candidates. This finding does **not** rule out other CPT/HCPCS/SNOMED codes, incomplete site submissions, or alternative encounter attachment as possible explanations.

The study has important limitations. The data are a retrospective research-network extract with heterogeneous contributing sources. Index stroke was defined by same-encounter ICD-10-CM codes without chart adjudication, exact birthday was unavailable, and the study period was provisional pending full contributing-site coverage review. Procedure codes were not validated against radiology information systems or images, and a code's presence might reflect documentation or billing rather than a completed study. Emergency-to-inpatient relationships were constructed from available encounter identifiers and dates without verified HCO continuity. Hospital-specific clustering, cross-site contribution, clinical stroke severity, and imaging appropriateness could not be fully assessed. Demographic labels included unknown or unmapped categories, the historical and primary age cohorts overlapped, and the exploratory regression confidence intervals did not correct institutional dependence. Finally, the reported measurement scenarios are nested but not interchangeable estimates of clinical imaging utilization.

Despite these limitations, the analysis offers a reproducible approach for communicating procedure-code ascertainment uncertainty. Comparing a strict index-encounter outcome with deliberately labeled alternative attachment rules, while displaying source-quality-standardized contrasts, helps distinguish observed data behavior from stronger clinical conclusions. In a multi-institutional network, future validation should prioritize site-level completeness, encounter continuity, and radiology completion before patient-care disparity estimates are advanced.

## Conclusion

Documented neuroimaging-code capture in young adults with candidate ischemic-stroke admissions is sensitive to encounter attribution and recorded diagnosis/encounter-quality characteristics. Differences in EHR code capture should not be interpreted as differences in completed imaging examinations without complementary clinical and institutional validation. Explicit endpoint definitions, source-quality sensitivity analyses, and careful reporting of missing codes can improve the reproducibility and interpretation of stroke imaging research using EHR networks.

## References

1. Centers for Medicare & Medicaid Services. ICD-10 Transition Moves Forward. October 29, 2015. https://www.cms.gov/newsroom/fact-sheets/icd-10-transition-moves-forward. [@CMS2015_ICD10]
2. Centers for Medicare & Medicaid Services. Multiple Procedure Payment Reduction (MPPR) on the Technical Component (TC) of Certain Diagnostic Imaging Procedures. Transmittal 738; Change Request 6993. July 30, 2010. https://www.cms.gov/regulations-and-guidance/guidance/transmittals/downloads/r738otn.pdf. [@CMS2010_MPPR]
3. Vagal A, Sanelli P, Sucharew H, et al. Age, sex, and racial differences in neuroimaging use in acute stroke: a population-based study. *AJNR Am J Neuroradiol*. 2017;38(10):1905–1910. doi:10.3174/ajnr.A5340. [@Vagal2017_AJNR]
4. Wang JJ, Katz JM, Sanmartin M, Naidich JJ, Rula E, Sanelli PC. Gender-based disparity in acute stroke imaging utilization and the impact on treatment and outcomes: 2012 to 2021. *J Am Coll Radiol*. 2024;21(1):128–140. doi:10.1016/j.jacr.2023.07.015. [@Wang2024_JACR]
5. Lewis AE, Weiskopf N, Abrams ZB, et al. Electronic health record data quality assessment and tools: a systematic review. *J Am Med Inform Assoc*. 2023;30(10):1730–1740. doi:10.1093/jamia/ocad120. [@Lewis2023_JAMIA]
6. Syed R, Eden R, Makasi T, et al. Digital Health Data Quality Issues: Systematic Review. *J Med Internet Res*. 2023;25:e42615. doi:10.2196/42615. [@Syed2023_JMIR]
7. An D, Lim M, Lee S. Challenges for Data Quality in the Clinical Data Life Cycle: Systematic Review. *J Med Internet Res*. 2025;27:e60709. doi:10.2196/60709. [@An2025_JMIR]
8. Abedi V, Lambert C, Chaudhary D, et al. Defining the Age of Young Ischemic Stroke Using Data-Driven Approaches. *J Clin Med*. 2023;12(7):2600. doi:10.3390/jcm12072600. [@Abedi2023_YoungStrokeAge]
9. Kakkar P, Kakkar T, Patankar T, Saha S. Current approaches and advances in the imaging of stroke. *Dis Model Mech*. 2021;14(12):dmm048785. doi:10.1242/dmm.048785. [@Kakkar2021_StrokeImaging]

## Figure legends (internal manuscript draft)

**Figure 1.** Percentage of indexed patients with a documented CPT14 neuroimaging code by encounter-attachment definition and unvalidated I63 P indicator. The groups are data-recording strata, not severity categories, and expanded scope does not validate completed imaging.

**Figure 2.** P=1 minus P=0 documented-code capture differences, crude and descriptively standardized to a common year × any-quarantined-encounter-key distribution. Encounter definitions are nominal categories and must be shown as unconnected points, not a time series or dose-response curve. These differences are not causal effects.

## Tables planned for manuscript/disclosure review

**Table 1.** Primary uniform ages 18–50 index I63 cohort, P status, and patient-level any-key encounter ambiguity. Review release eligibility.

**Table 2.** Primary index-IMP CPT14 and alternative encounter definitions, observed capture counts and proportions, crude P contrast, and descriptive common-mix contrast. **Primary table**, pending institutional approval.

**Table 3 (supplementary/internal).** Year × encounter-key quality strata; only show after complementary suppression and cross-table disclosure review.

**Table 4 (WITHHELD).** Original demographic source-completeness exhibit includes potentially derivable small event/complementary counts; neither the original rates nor a supposedly “safe” replacement is cleared for release.

**Table 5 (supplementary/internal).** Exploratory demographic model contrasts, without reliable HCO-cluster inference or clinical imaging validation. Not evidence of unequal clinical imaging care.

---

*Provenance note: This Markdown is a publication-oriented scientific draft assembled using the frozen locally generated Step78 data. The source-derived values must remain on the authorized workstation; references use project-local keys with a matching Zotero-importable RIS/CSL-JSON/BibTeX library, but Markdown citations are not embedded Zotero Word fields. The manuscript is not approved for external disclosure or journal submission.*

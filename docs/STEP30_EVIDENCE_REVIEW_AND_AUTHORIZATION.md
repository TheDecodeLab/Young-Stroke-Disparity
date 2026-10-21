# Step 30: Literature-based clinical imaging code appraisal

**Evidence review, NOT a stroke neurologist's personal assessment,
IRB determination, or institutional data-use authorization.**

Date: 2026-10-17. Investigator expressly authorized an additional
single scan of the **already possessed** Diamond procedure table,
conditioned on its use being permitted under the existing agreement.
The investigator requested evidence-based clinical review instead
of an external clinician's sign-off. The codebook is tagged
**evidence_reviewed**, not clinician approved.

## Sources chosen to match 2018-2019 clinical practice

1. Wintermark et al., AJNR 2013: imaging recommendations from
   ASNR, ACR, and SNIS, PMID 23907247, DOI 10.3174/ajnr.A3690.
   [Full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC4072500/).
   The recommendations distinguish brain CT/MRI from intracranial
   and cervical vascular imaging, support cervical vessel imaging
   in ischemic stroke evaluation and acknowledge many valid
   modality pathways. Lack of MRI does not, by itself, prove
   deficient work-up.
2. Powers et al., 2019 AHA/ASA acute ischemic stroke guideline,
   PMID 31662037, DOI 10.1161/STR.0000000000000211.
   [Publication](https://pubmed.ncbi.nlm.nih.gov/31662037/).
   Rapid noncontrast CT can be sufficient for initial decisions
   in many patients; specialized CTA/MRI depends on indication,
   suspected large vessel occlusion, workflow and treatment.
   Therefore do not label an absence of advanced-imaging codes
   a clinical failure, lower quality of care, or inequity.
3. CMS Transmittal 2395 (issued in 2012),
   [diagnostic imaging CPT schedule](https://www.cms.gov/regulations-and-guidance/guidance/transmittals/downloads/r2395cp.pdf).
   Confirms the brain CT, CTA head/neck, brain MRI and MRA
   head/neck procedure code families were established before 2018.
4. CMS Radiology Manual, revision 1472,
   [MRA codes](https://www.cms.gov/Regulations-and-Guidance/Guidance/Transmittals/Downloads/R1472CP.pdf):
   MRA head 70544-70546 and MRA neck 70547-70549. Distinguishes
   procedure code from charge modifiers and coding system.
5. Administrative stroke-code validation, *Performance of
   ICD-10-CM Diagnosis Codes for Identifying Acute Ischemic Stroke
   in a National Health Insurance Claims Database*,
   PMID 33061648, DOI 10.2147/CLEP.S273853.
   Validates diagnosis coding *against adjudicated inpatient episodes*
   in a different claims population. It does NOT validate a
   procedure-linked encounter in our TriNetX export, which has
   no encounter ID.
6. Abedi et al., *Defining the Age of Young Ischemic Stroke
   Using Data-Driven Approaches*, PMID 37048683,
   DOI 10.3390/jcm12072600. Motivates historical sex-specific
   young-stroke upper-age cutoffs, but these produce different
   age groups for men and women. We use a single 19-50
   primary age range for comparability; this must be described
   as a changed source population.

## Modality and code determination

| Classification | CPT codes | Evidence-based assessment |
| --- | --- | --- |
| Brain CT | 70450, 70460, 70470 | Include. CT brain structural studies; no assumption that every code is an acute index admission CT |
| Brain MRI | 70551, 70552, 70553 | Include. MRI brain (with and/or without contrast); no MRI requirement implied |
| Head CTA | 70496 | Include as **primary intracranial CTA** |
| Neck CTA | 70498 | Include as separate *cervical vascular* endpoint, and in expanded CTA sensitivity |
| Head MRA | 70544, 70545, 70546 | Include as **primary intracranial MRA** |
| Neck MRA | 70547, 70548, 70549 | Include separately and in expanded MRA sensitivity |

**Decision on code inclusion for EXPLORATORY CODE EXTRACTION:**
Use all 14 exact CPT codes as an evidence-reviewed extraction
candidate. The additional five represent plausible cerebrovascular
studies. They may occur in a stroke work-up but are not equivalent
to brain-only imaging. Preserve the exact code, anatomy and
modality so head-only and head+neck outcomes can be reported without
mixing definitions.

This assessment does not certify completeness of CPT claims, nor
HCPCS or ICD-10-PCS coverage. The source uses explicit code-system
strings, and an identical numeric code in another system is NOT
treated as equivalent. No speculative code mappings are added.

## Primary estimand and window: methodological judgments

- One earliest **observed in 2018-2019** principal I63 diagnosis
  per person, index independent of imaging. Approximate age 19-50,
  recognized recorded sex. No established first-ever stroke,
  admission, clinical severity or index hospitalization.
- Recorded brain CT, MRI, **CTA head**, **MRA head** procedure
  codes around the diagnosis date are primary descriptions.
- Head+neck vascular code receipt is a sensitivity description.
- A +/-1 calendar day primary association window is a **pragmatic
  research choice**, NOT an evidence-proven admission-linkage
  algorithm. Also retain 0, +/-3 and +/-7 days.
- Patient with no included code remains in denominator, labeled
  *no matched included procedure code*; not *no imaging*.
- The user's existing source is all data available; a comprehensive
  claims observation period or patient/provider capture level is
  not established. No imaging utilization rate or quality-of-care
  inequity interpretation is supported without further validation.

## Execution mode and permission distinctions

- **Clinical-code review basis:** literature-based (this memo),
  not an independent physician's signoff. In the versioned
  literature CSV, all codes say evidence_reviewed rather than
  approved.
- **Scientific/technical research authorization:** The
  investigator authorized the rescan of the existing 1.17-billion
  procedure-row table. The actual local operator must select the
  explicit evidence-only research execution mode.
- **Data-use authorization:** This review does NOT establish that
  the existing TriNetX agreement, IRB or institution permits the
  additional derived private SQLite extract. The local operator
  must independently confirm authorization and attest to it
  through the execution flag. No names/signatures or institutional
  clearance are invented.
- **Data privacy:** Only the approved private directory outside
  Git may store patient-level SQLite; JSON audit uses aggregate
  counts and must undergo cumulative small-cell/reconstruction
  review before disclosure. Existing patient-level Parquet in
  public Git history should be reviewed under institutional
  data governance.

If local use permission is not confirmed, the next step is the
metadata-only plan, NOT execution. Even after an authorized
full scan, **clinical inference and publication remain blocked**:
first inspect capture, missingness, code distributions and source
limitations. User authorization to compute is not publication
approval or causally valid evidence.

## One-scan implementation contract

Only a local operator can launch the 1.17-billion-row scan on the
study workstation where the original source ZIP resides. The
assistant cannot launch work on that device remotely in this chat.

The codebook and source fingerprints are checked first. A full
manifest row-count match and exact preservation of every legacy
nine-CPT linked modality/day receipt are required before the new
private SQLite is marked complete. A partial/failed scan must not
be accepted for inference. The explicit literature-only mode
cannot produce an actual clinician sign-off.

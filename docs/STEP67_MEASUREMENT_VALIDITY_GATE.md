# Step67: Imaging outcome and diagnosis measurement-validity gate

**Research decision record, 2026-10-19. Public external-evidence desk
review completed; source-specific steward and clinical validation
PENDING. No real-data execution authorized by this document. No
procedure source scan performed in Step67.**

Two concrete deliverables from the completed public review:
- [External evidence and coding semantics](references/STEP67_EXTERNAL_EVIDENCE_REVIEW.md):
  official Penn State descriptions of the EHR-derived Research Network,
  HCO-anonymous download policy, CMS year-dependent ICD-10-PCS
  definitions, and evidence/limitations separated explicitly.
- [Ready-to-review CTSI/data-steward and clinical contact packet](STEP67_STEWARD_CONTACT_PACKET.md):
  brief, source-specific technical questions and a completion worksheet.
  **Draft only; no message has been sent.**

The [header-only versioned codebook template](references/STEP67_VERSIONED_CODEBOOK_TEMPLATE.csv)
contains no executable PCS/SNOMED mappings or source-derived codes.
Do not mistake the template for approval of expanded imaging outcomes.

## Investigator methodological decision (2026-10-20)

Proceed using public TriNetX descriptions, published scientific work and
official versioned codebooks rather than requiring a data-steward email.
The existing contact packet is optional and has NOT been sent.

Primary endpoint wording should describe **documented imaging procedure
code capture**, not independently confirmed completed scans or absence
of imaging. Broad same-IMP ICD-10-CM I63 diagnoses are coded stroke
candidates; the date-only ED link is a sensitivity, not proven transfer.
HCO participation and coding coverage may vary and should be reported
as limitations, without implying nationally representative sampling.

**P-label caution:** Step62's P=1 means a matched I63 diagnosis marked
primary; P=0 includes S, blank and other non-P observations, so it
cannot be called a validated secondary-stroke group. The large
difference in recorded inpatient CPT14 capture across P strata is an
unexplained measurement finding. Test source/encounter and annual
patterns rather than treating it as a real difference in care.

Next: use official CMS fiscal-year ICD-10-PCS code definitions and
already-verified CPT14 meanings to construct an exact, version-aware
imaging codebook. Check actual code availability and modality-specific
overlap before one additional justified checkpointed procedure scan.
Preserve all Step62-66 outputs and predefine uniform ages 18-50 as
the preferred primary cohort, historical sex-specific limits as
sensitivity unless a precommitted protocol states otherwise.

## Why this gate now

Steps 62-66 established two overlapping, provisional I63/IMP indexed
cohorts and evaluated **documented CPT14 imaging-code capture** within
the index IMP plus the hypothetical maximum addition from a frozen,
reciprocal-unique, date-only ED predecessor. Provenance checks
identified differences by index year and the unvalidated P flag in
both encounter quarantine and TriNetX-derived ED end dates.

A significant proportion of inpatient-indexed patients lack any of
the 14 selected same-IMP CPT codes. This MUST NOT be described as
missing clinically performed neuroimaging. Even upper-bound ED
linkage cannot resolve whether inpatient procedures are coded through
other systems, whether all institutions contribute these events, or
whether a procedure is an order versus performance event.

The source-wide Step59 procedure report already distinguishes
**CPT, ICD-10-PCS, SNOMED, HCPCS and other labels** by calendar year
at procedure-ROW grain (not young-stroke patients or scans). Thus a
repeat source-wide aggregate scan to recompute the same row totals
is not useful. The clinical/codebook gap is more fundamental.

## Decision gate 1: Clinical coding and provenance specification

Before writing the next patient-level scanner, ask the authorized
TriNetX/CTSI data steward and clinical co-investigator to resolve:

1. In the Research Network download, what exactly does a `procedure`
   record represent (performed procedure, claim-coded event, placed
   order, or a source-dependent combination)? Are these distinctions
   encoded? Are imaging CPT/ICD-10-PCS/SNOMED events complete enough
   for interpatient or inter-HCO comparisons?
2. For `type=IMP`, are diagnostic CT, CTA, MR and MRA procedures
   expected to appear in **CPT**, **ICD-10-PCS section B (Imaging)**,
   local mapped SNOMED concepts, or combinations? What validation
   documents exist for their TriNetX mapping over 2016-2024?
   The existence of an ICD-10-PCS Imaging section is not evidence
   of this export's completeness or a one-to-one CPT equivalent.
3. Which official **year-specific** code lists and descriptors should
   be used for 2016-2024, including brain/head vascular diagnostic
   imaging, contrast/qualifier distinctions, and cerebral perfusion
   as a separate endpoint? Build exact-code versioned maps only
   after an expert review. **Do not** use fuzzy strings, all `B*`
   codes, or a presumed direct mapping from CPT14.
4. Confirm I63/IMP cohort semantics, `principal_diagnosis_indicator`
   P versus S versus missing, `admitting_diagnosis`, source
   deidentification of encounters, and year coverage. A P-marked
   record should not be assumed clinically validated just because
   a legacy data dictionary labels P as primary.
5. Can the authorized user obtain an **HCO-consistent** site identifier,
   or an approved coverage/completeness report? `source_id` is a
   provenance category in historical dictionaries; do not treat it
   as a hospital key. If no site metric exists, avoid claims that
   between-patient recorded-code differences represent care
   disparities unconfounded by contributing HCO.
6. Determine whether any patient-level linkage of radiology
   results/orders to procedures, or an approved chart-reviewed
   validation sample, could establish the sensitivity, specificity,
   and missingness of the constructed outcomes.

## Decision gate 2: Frozen cross-system codebook

Build a separately reviewed codebook with these minimum fields:
`system`, `exact_code`, `year_start`, `year_end`,
`published_description`, `imaging_category`,
`diagnostic_versus_adjunct`, `contrast_or_method`,
`provenance_citation`, and `approved_by`.

- Primary CPT14 same-IMP code capture remains frozen and labelled
  as recorded-code capture rather than performed imaging.
- Alternate coding-system endpoints remain explicitly **unvalidated**
  until exact clinical mapping and local occurrence are reviewed.
- Maintain each modality separately, including the CT_HEAD comparator
  and MR/CTA/MRA advanced imaging. Separate perfusion tests rather
  than implying all cerebral imaging methods are equivalent.
- The overlapping age cohorts stay separate; preserve quarantine,
  missing demographics (especially UNKNOWN race/ethnicity),
  and diagnosis P-flag status in all QA.

**Official public starting points:** CMS's ICD-10-PCS code tables,
descriptions and guidelines by effective discharge year
(https://www.cms.gov/medicare/coding-billing/icd-10-codes),
and the original evidence-backed CPT14 code register
[`docs/references/IMAGING_CODE_CITATION_REGISTER.md`](references/IMAGING_CODE_CITATION_REGISTER.md).
CMS confirms ICD-10-PCS is a hospital inpatient procedure
classification. Its existence does not validate TriNetX data capture.

## Decision gate 3: Targeted cohort-level measurement test

Only after the above specification and local governance approval:

1. Implement a separate **checkpointed** procedure-only scanner
   capable of processing the 993-million-row source once, retaining
   only encounters belonging to the frozen Step62 selected IMPs
   and Step63 unique ED sensitivity set. Do not modify Steps 62/63.
2. Record per-code-system **matched patient/encounter and modality**
   capture, code-date within corresponding encounter span,
   provenance flags, same-IMP and ED portions, overlaps between
   coding systems, and missing/ambiguous events.
3. Quantify code-system availability by index year and P category
   and, if permitted, demographic strata; never interpret missing
   procedure codes as no scan without a validated source-completeness
   study. Distinguish code counts from patients.
4. Evaluate specificity: how often alternative-code-system events
   corroborate CPT14 versus occur only where CPT14 is absent;
   require review of any unexpectedly high or low rates or
   coding-period discontinuities. A large gain in code capture alone
   does not prove performed imaging.
5. Decide a primary, clinically interpretable endpoint or explicitly
   reframe the study as a **documented-code disparity** analysis.
   Do not run disparity regression until that outcome decision is
   signed off, and do not imply causal disparities without HCO
   adjustment or an acknowledged inability to estimate it.

**No source ZIP rescan should be launched now.** A bounded source
probe could verify parsing/schema of candidate code-system values,
but its first rows are not a representative sample for prevalence
or coverage inference.

## Remaining governance issue

An earlier draft-branch intermediate documentation commit contained
source-derived LOCAL ONLY aggregate numbers which were removed from
later file contents. Removing those lines from HEAD does NOT remove
them from repository history. Before sharing or merging, arrange a
separate repository-history and data-disclosure review under the
existing research-governance policy; avoid blindly rewriting
collaborators' Git history.

## Current milestone

- Step62: completed provisional indexed cohorts and same-IMP CPT14
  capture, NOT clinical stroke/imaging validation.
- Step63: completed conservative date-only unique ED links, NOT same-HCO
  transfer validation.
- Step64: completed hypothetical unrestricted ED augmentation ceiling.
- Step65: completed encounter-date derivation and quarantine QA.
- Step66: completed provenance-restricted ED ceiling, no actual ED
  procedure scan.
- **Step67: measurement-validity decision gate only; NO new clinical
  source pass, NO new regression, pending steward/clinical review.**

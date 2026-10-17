# Step 27: admission-level feasibility decision record

**Template; no approvals have been received.**
Use institution-approved storage for completed approvals. Avoid putting
names of individual patients, institution-private metadata, contract
terms or linkable details in the public GitHub repository.

## Current position (2026-10-17)

- Selected plan: **preserve the original hospital-admission
  imaging-disparity question if valid encounter-linked data exist**.
- Original Diamond source ZIP: only patient/date linkage was found in
  the inspected clinical CSV schemas. It does not verify a stroke
  hospitalization or common imaging episode.
- Full source and aggregate QC through Step 25 v2: **PASS** for
  engineering reconciliation, **FAIL/NOT ESTABLISHED** for
  admission-based scientific inference.
- Next permitted step: contact authorized data steward / custodians
  for schema, linkage semantics and data-use feasibility. No new
  patient-level extraction or modeling is approved.
- Existing public patient-level Parquet and historical I63
  complementary-suppression issue require separate governance review.

## Questions and decisions to document

| Decision | Current status | Required evidence | Approved determination / rationale |
| --- | --- | --- | --- |
| Institutional/TriNetX permitted use and public-repo data review | PENDING | DUA/IRB/data office guidance, Git history privacy review | [to be documented privately] |
| Encounter linked source or validated episode algorithm | UNKNOWN | Field-level schema, cross-table keys, inpatient status and date semantics | [to be documented privately] |
| Episode/transfer/ED handling and first eligible admission | NOT DECIDED | Clinician+data-steward episode specification | [to be documented privately] |
| Principal I63 coding, ICD-9/H34.1 and washout | NOT DECIDED | Stroke neurologist-approved codebook and lookback | [to be documented privately] |
| Primary young-stroke age range | NOT DECIDED | Prespecified 19-50 vs original 19-54 women/19-52 men, clinical rationale | [to be documented privately] |
| MRI, CTA, MRA, CT source capture and full codebook | NOT DECIDED | Facility/professional/claims modality definitions, approved code list | [to be documented privately] |
| Date range and imaging-to-admission assignment | NOT DECIDED | Index period and linked episode/ED boundary | [to be documented privately] |
| Race/ethnicity availability and missingness | NOT ACCEPTABLE FOR CURRENT RACE INFERENCE | Source provenance and defensible analysis plan | [to be documented privately] |
| Statistical estimands and adjustment | BLOCKED | Reviewed clinical covariates, site data, confounding and analysis plan | [to be documented privately] |
| NIS replication | SEPARATE HOLD | NIS source code, age strata and survey design provenance | [to be documented privately] |

## Proposed sign-off sequence

1. Data steward confirms encounter-linked claims/inpatient source is
   available (or documents that it is not).
2. Governance team verifies license, privacy and approved location
   for source/linkage validation and release of aggregates.
3. Clinical stroke lead and investigator approve target population,
   age, case definitions and imaging codebook **before full scanning**.
4. Technical analyst performs a **limited secure sample
   linkage/observability audit**. Team reviews aggregate consistency,
   completeness, unknown statuses and transfer reconstruction.
5. Investigator decides GO or STOP for a new full
   admission-based extraction. Without verified encounter linkage,
   the original manuscript remains on HOLD.

### Final decision (not filled in)

- Decision date: [pending]
- Authorized data source and study version: [pending]
- Hospitalization linkage demonstrated: [pending]
- Clinical codebook approval: [pending]
- Privacy/data-sharing clearance: [pending]
- Decision: [PENDING; do not mark GO based on passing pytest]
- Next step / person responsible: [pending]

## Scientific safeguards

Do not treat existing 8,713 CT-only / 44,760 no-listed-imaging
counts as admission rates, or the 86,902 provisional index patients
as confirmed stroke hospitalizations. Treat >75% unknown
race/ethnicity as a substantial barrier to population disparity
claims. Preserve the original question only if a suitable authorized
data source exists; otherwise return for an explicit study question
revision rather than changing the estimand silently.

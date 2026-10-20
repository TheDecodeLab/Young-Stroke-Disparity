# Step67 | Data steward and clinical validation contact packet

**Prepared 2026-10-19. Not sent.** No participant data,
cohort sizes, small-cell counts, images, or private ZIP/SQLite
files should be attached.

## Steward inquiry: suggested recipient

Penn State CTSI lists `ctsi@psu.edu` as the general technical
TriNetX contact and points researchers to its service request
channel: https://ctsi.psu.edu/services/research/trinetx .
Request routing to a TriNetX Research Network data steward
or research informatics expert, rather than assuming CTSI can
answer export-specific questions directly.

**Subject:** TriNetX Research Network procedure coding and encounter fields

Hi,

We are reviewing a de-identified TriNetX Research Network
dataset for a study of imaging after ischemic stroke in
younger adults. Before finalizing the analysis, I would
appreciate some clarification on the export fields.

1. Does a `procedure.csv` record represent a completed
procedure, an order, or a combination depending on the source?
2. For inpatient and emergency neuroimaging, how complete
are CPT, ICD-10-PCS, HCPCS and SNOMED mappings? Is there
a recommended codebook or a way to validate capture across
2016-2024?
3. Is `principal_diagnosis_indicator` consistently populated
for `IMP` encounters? How should missing values be interpreted?
4. Is there an approved way to assess HCO-level data
completeness or the continuity of ED-to-inpatient encounters
without identifying HCOs?

Could you please direct me to the appropriate person or
documentation for these questions?

Thank you!

Best,
Alireza

## Clinical collaborator review (stroke/radiology)

Use a separate review with the existing authorized study
clinicians, without assuming they have direct knowledge
of TriNetX ingestion:

- For confirmed acute ischemic stroke, distinguish expected
  **clinical use** of noncontrast CT head, brain MRI, CTA head/
  neck, MRA head/neck and perfusion, and timing before versus
  after hospitalization.
- Decide whether the scientific endpoint is *receipt of
  a completed scan*, *documentation of an imaging code*
  or another explicitly measurable construct.
- Distinguish routine CT comparator versus advanced
  vascular imaging; order/performance issues differ.
- Have a coding expert review any proposed PCS exact-code
  mapping **for every valid fiscal-year/discharge interval**.
  A clinical expert alone cannot validate source coding
  completeness.
- If the existing export lacks exam-result fields, discuss
  whether an approved de-identified audit/chart-validation
  sample or a different linked source is possible.

## Completion worksheet

| Question | Evidence presently available | Status | Action needed |
|---|---|---|---|
| TriNetX Research Network is EHR-derived, not primarily billing-claims | Official Penn State CTSI guidance | External documentation only | Confirm applicability to downloaded extract |
| Does a procedure code mean a completed scan? | Procedure name/date alone does not answer | OPEN, high impact | Steward + radiology/informatics |
| Exact PCS/SNOMED mapping 2016-24 | CMS versioned PCS is available, crosswalk unvalidated | OPEN, high impact | Clinical coder versioned mapping |
| CPT14 adequacy and procedure capture | Step62 measured code presence only | OPEN, high impact | Steward local-code QA / alternative source |
| P/S/blank diagnosis indicator semantics | Historic dictionary describes P/S, but local completeness unknown | OPEN | Export steward |
| HCO-adjustable capture / ED episode continuity | No verified site identifier | OPEN, high impact | Export steward, with HCO privacy policy |
| Demographic disparity regression | Outcome validity and confounding unresolved | BLOCKED | Wait for defensible endpoint |

## Use restrictions

This packet is **a draft only**. It does not send an email,
open a service ticket, grant access, or authorize release of
the research data. Avoid listing raw code values that are
private or source-derived and avoid attaching patient- or
encounter-level outputs.

If the recipients cannot validate imaging utilization, the
next study decision may be to reframe outcomes explicitly as
documented-code capture with acknowledged ascertainment
limitations or choose a more complete clinical imaging source.

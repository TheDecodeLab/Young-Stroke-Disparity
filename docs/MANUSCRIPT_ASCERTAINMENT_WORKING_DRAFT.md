# Working manuscript: Encounter attribution and documented neuroimaging-code capture among young adults with ischemic stroke

**Draft stage:** Methods/interpretation scaffold, NOT a submission manuscript.
All patient-derived numerical findings, figures and tables remain LOCAL ONLY
pending institutional cross-table disclosure review. Replace bracketed fields
only after the validated Step78 restricted results package is reviewed.

## Proposed title

**Recorded neuroimaging in young adults with ischemic-stroke codes depends on encounter attribution: a retrospective research-network ascertainment study**

Alternative (more neutral): **Encounter-level variation in documented neuroimaging codes among young adults with candidate ischemic stroke**

## Structured abstract (working text, not publishable yet)

**Background:** Large electronic health record research networks combine
procedure and diagnosis data collected under heterogeneous encounter
and coding practices. Differences in recorded neuroimaging codes may
reflect both care delivery and how records are attached to encounters.
We investigated the sensitivity of documented neuroimaging-code
capture to encounter definitions among young adults with inpatient
ischemic-stroke diagnosis codes.

**Methods:** We retrospectively constructed a provisional research
network cohort using candidate ICD-10-CM I63/IMP index encounters
from 2016 through 2024. The primary age-eligibility group was
18–50 years; a historical sex-dependent age definition was treated
as an overlapping sensitivity cohort. The primary outcome was
presence of one of 14 prespecified CPT codes on the patient's
index inpatient encounter within its start/end dates. We compared
this with separately defined same-day other-encounter,
reciprocally unique preceding emergency-encounter and
broader temporal capture screens. We examined the unvalidated
I63 principal-recording indicator P and patient-level
encounter-key quality. Descriptive year × quality-stratum
standardization quantified sensitivity to source mix.

**Results:** [Populate only from the completed, locally reconciled
Step78 table2, including cohort denominator and the
unstandardized/standardized contrast for each prespecified
encounter definition. Do not embed private results in GitHub.]

**Conclusions:** [Finalize after review.] Recorded
neuroimaging-code capture is sensitive to which encounter
records are linked to an indexed hospitalization and to the
mix of recorded diagnosis/encounter-quality categories.
These analyses do not verify performed radiology services
or inequalities in clinically appropriate imaging care.

## Introduction: working scientific argument

Administrative and EHR-derived analyses frequently operationalize
clinical services through procedure codes. The presence of such
a code is evidence of documentation in a given coding vocabulary;
its absence may also result from incomplete code coverage,
recording under another encounter, site-dependent source
participation or differences between inpatient and outpatient
systems. These issues matter when comparing patient subgroups
because an apparent utilization difference might instead be
partly attributable to how clinical records are represented.

Young adults with candidate ischemic stroke are a useful context
for examining this concern because emergency evaluation,
hospital admission and imaging can occur across closely
timed but separately represented encounters. Yet neither a
shared date nor a plausible preceding ED encounter guarantees
that two records belong to the same hospitalization or HCO.
We therefore focus on the *measurement of documented imaging
codes*, not the clinical appropriateness or actual performance
of neuroimaging.

The study asks whether recorded CPT14 neuroimaging capture
changes when broadening an index-inpatient definition to
other encounter contexts, and whether the resulting P
recording-group contrast changes under a common calendar-year
and patient-level encounter-key quality distribution.
Exploratory demographic comparisons assess additional
heterogeneity in recording, but cannot establish unequal
clinical care without HCO/case-mix and performed imaging
validation.

Public code definition basis: [CMS2010_MPPR], as indexed in
`docs/references/IMAGING_CODE_CITATION_REGISTER.md`.
Add method-reporting and research-network citations only after
the external literature reference audit.

## Methods (implemented analyses, precise working text)

### Data and provisional cohort

The data source is the TriNetX Research Network export
used in the completed private pipeline. Eligible candidate
index hospitalizations were `IMP` encounters beginning
between January 1, 2016, and December 31, 2024,
with the same patient/encounter linked to at least one
strict ICD-10-CM I63 or I63.* diagnosis dated within
the encounter's recorded interval. The I63-coded record
identifies a **candidate stroke encounter**, not a
chart-adjudicated acute cerebral infarction.

The main cohort used definite ages 18–50 based on
year of birth and admission year. Since precise
birth dates were unavailable, the birth-year
interval rule excluded ambiguous age-boundary
cases rather than assigning unobserved birthdays.
The earliest definitely eligible qualifying
hospitalization was indexed for each person.
An overlapping historical sensitivity cohort
used men's 18–52 and women's 18–54 eligibility;
these cohorts were not pooled or considered
independent.

Records with unassessable admission dates and
competing same-day qualifying index encounters
were conservatively excluded or held under the
frozen Step62 decision rules. The denominator
was determined independently of imaging-code
presence.

### Main documented-code outcome and modalities

We used the 14 exact CPT codes assigned to
noncontrast/standard head CT, brain MRI, CTA
head/neck and MRA head/neck in the frozen
Step62/68 codebook (see the manuscript
citation register for the exact public codes).
The main binary outcome indicated any matching
CPT code attached to the **same patient and
frozen indexed IMP encounter**, with code
date within the recorded inpatient interval.

CPT14 capture was a documented procedure-code
marker; the source procedures were not
independently confirmed as acquired/complete
radiology examinations. No missing CPT code
was interpreted as clinical absence of imaging.

### Distinct secondary encounter definitions

Prespecified, distinct alternative indicators
were any matching CPT14 code recorded for
the same patient on (1) **another encounter**
on the index admission calendar date; (2) a
reciprocally unique preceding EMER record
ending no more than one day before admission,
under Step63's conservative linkage contract;
or (3) the broad union of qualifying
ED and other-encounter code events during
the -2 to day-0 timing screen. All definitions
retained the frozen main-cohort denominator.
Overlaps were counted only once per indexed patient
within each individual definition.

The wider screens are tests of **recording
sensitivity**, not validated patient care episodes.
In particular, same-day other encounters were
not confirmed to be EMER or IMP, from the
same institution, or part of the same
stroke evaluation.

### Source-recording quality and comparisons

We retained an unvalidated indicator P that
a candidate I63 record on the indexed IMP was
marked principal. P=0 pooled secondary, blank
and other non-P diagnosis markers; neither P
category was an adjudicated stroke subtype.
Any-key encounter ambiguity indicated that
at least one EMER/IMP encounter key for that
indexed patient was quarantined by the earlier
source QA. This may or may not involve the index
encounter itself.

We report the crude P1–P0 percentage-point
difference in code capture for each outcome.
We also calculated direct descriptive
standardization using identical pooled
calendar-year × any-key ambiguity stratum
weights for P=0 and P=1. The weighted comparisons
require both P groups in every included stratum
and reconcile to the original population totals.
These are **descriptive case-mix checks**;
no causal interpretation is warranted.

### Demographic sensitivity and limitations of modeling

Age-year proxy, source sex, race and ethnicity
labels were grouped conservatively and missing
or unmapped categories remained explicit.
Exploratory grouped-binomial models included
calendar year, broad age-year proxy, sex, race,
ethnicity, P and any-key quarantine status.
They produced marginal standardized code-capture
percentage-point differences. Standard nominal
and inflated model-based confidence intervals
do not account for unobserved site/HCO clustering,
case-mix severity or differential source
code capture; they should not be described as
definitive racial/ethnic care disparities.
Model results are supplementary and subject
to separate review.

### ICD-10-PCS alternative code-system assessment

An independent, exact seven-character CMS
ICD-10-PCS imaging-title screen considered
fiscal-year releases and candidate CNS/upper
arterial CT/MR code families. It yielded
a PRIVATE review queue; titles were not
independently clinically validated and
source procedure rows could not establish
distinct CPT-negative newly imaged patients.
A mathematically generous source-row upper
bound assessed whether candidate index-IMP
PCS codes alone could close the P recording
contrast. **PCS codes were not added** to
the final CPT14 patient-level outcome.
This is a sensitivity/feasibility analysis,
not an adjudicated imaging-code expansion.

### Reproducibility and disclosure

All heavy source scans were completed once
in previously checkpointed, locally frozen
Step62/63/68 pipelines. Steps69–78 are
read-only, metadata-verified aggregations
of those checkpoints. Patient identifiers
and raw source rows are not exported.
All draft aggregate figures, tables and
Results prose remain internal until
cross-table institutional disclosure review.

## Results organization (source data from local Step78 only)

**Table 1:** Indexed candidate-stroke cohort by P recording
and patient-level any-key encounter ambiguity.

**Table 2 (main):** For each indexed encounter scope,
P-specific number with documented CPT14 codes, observed
percentages, crude P1–P0 difference, and pooled
year × ambiguity standardized difference.

**Table 3:** Source-quality cross-tabulation by P,
calendar year and patient-level ambiguity
(with small-cell suppression and cross-table review).

**Table 4 (INTERNAL-ONLY pending institutional review):**
Demographic completeness and descriptive recorded-code capture.
The completed Step79 audit found a disclosure risk in one or
more subgroup event or complementary-event counts derivable
from published denominators and category percentages.
Do NOT include P-group or imaging-capture rates by
demographic category in any proposed shareable version.
A category-completeness-only replacement remains subject
to independent complementary and cross-table suppression review.

**Table 5 (supplement only):** Exploratory grouped models
of code capture, marked as not cluster-robust and
not performed-imaging disparities.

**Figure 1:** Code-capture proportion by P group
and encounter definition.

**Figure 2:** Crude versus common-mix P differences,
highlighting the sensitivity of an apparent
same-day contrast to source-quality adjustment.
The current draft joins values across nominal
encounter-definition categories with a line;
a final figure should prefer separate points
without lines implying a continuous scale
or chronology. Both figures require private
workstation visual review, beyond PNG-file checks.

## Discussion: planned argument, no new claims yet

The core interpretive contribution is that changing
encounter attribution can change the direction and
size of subgroup contrasts in recorded imaging codes.
An index-IMP definition is reproducible and conservative,
but potentially misses procedures recorded under
other encounters. Broad same-day inclusion can
recover additional code records, but is not
validated as the same clinical episode and
can introduce its own ascertainment artifacts.
The evidence therefore challenges simple inference
from a missing inpatient procedure code to
missing medically appropriate imaging.

A second interpretation is that large differences
by the nonvalidated principal-code P indicator
are not resolved merely by adding the selected
review-only ICD-10-PCS source codes. This does
not establish a mechanism: differences in
hospital/source contribution, coding systems,
stroke diagnosis validation or HCO/episode
linkage may still explain substantial variation.

The study must acknowledge (i) candidate diagnosis
rather than clinical stroke confirmation;
(ii) procedure-code capture rather than completed
radiology; (iii) unverified same-hospital encounters;
(iv) unknown/unmapped demographic labels;
(v) unmeasured severity and clinical indications;
(vi) no reliable HCO-clustered inference;
(vii) overlapping age cohort definitions; and
(viii) provisional incomplete-year/source-network
coverage. Clinical-disparity language should be
avoided unless a separate, adequately validated
analysis becomes possible.

## Before submission

Step78 generated the **private** tables and figures,
and Step79's 745-test local run verified arithmetic,
nested outcomes and provenance, with one Table4
small-event/complement disclosure-risk category.
Review both graphics visually on the workstation,
withhold Table4 demographic code-capture/P percentages
from shareable drafts, and seek formal primary/
secondary and cross-table disclosure clearance.
Then freeze final main and sensitivity estimands,
verify clinical-code and methodological references,
and obtain statistical/clinical coauthor approval.
The internal Step78 results are not publicly
disclosure-approved by passing Step79.
Only after those gates replace the restricted
Results placeholders with approved aggregate
material in a shareable manuscript.

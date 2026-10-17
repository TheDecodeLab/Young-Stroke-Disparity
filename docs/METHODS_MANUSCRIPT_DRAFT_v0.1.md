# Internal manuscript draft v0.1: cohort selection and imaging-code ascertainment

**INTERNAL SCIENTIFIC DRAFT. Not approved for submission, redistribution
or clinical inference.** The uploaded Step 33 report passed internal
aggregate reconciliation. The raw TriNetX ZIP, patient-level SQLite,
and patient-level data must remain outside GitHub. Review the existing
public patient-level Git history before dissemination of any results.

## Working title

**How Cohort Construction, Procedure Code Selection, and Temporal Linkage Change Recorded Neuroimaging Patterns in a Diagnosis-Indexed Stroke Dataset**

Alternative shorter title: **Measurement Choices in Stroke Imaging Research Using Administrative Records**

## Structured abstract — working draft

**Background:** Observational studies of diagnostic procedures may
select participants based on the procedures under investigation.
Procedure code lists and temporal linkage rules can further change
the apparent frequency of recorded services. We examined these
measurement choices in a pre-existing administrative extract.

**Methods:** We reconstructed a patient-level denominator
independent of imaging from individuals with an earliest *observed
during 2018–2019* principal ICD-10-CM I63 diagnosis in the
available TriNetX Diamond extract. The analytic cohort used
approximate age 19–50, calculated from calendar year and year of
birth, and included patients with recognized recorded sex.
Recorded head CT, brain MRI, head CTA, and head MRA codes were
linked by patient and calendar date using same-day and ±1, ±3,
and ±7-day rules. We compared the historical nine-code CPT list
with an expanded 14-code list that distinguished intracranial
from cervical vascular studies. We described code matching
across broad age, recorded sex and index-year strata without
attempting to infer true imaging receipt.

**Results:** Of 962,351 individuals with an eligible-year principal
I63 diagnosis across all ages, 86,902 met the reconstructed
approximate-age and recorded-sex criteria. The historical nine-code
definition identified 8,713 CT-only patients within ±7 days who
were not represented in the legacy imaging-conditioned selection.
Within ±1 day, 39,774 patients matched at least one of the nine
codes versus 39,949 with the expanded head/neck-inclusive
14-code list, an increase of 175 patients (0.20 percentage
points of the cohort). Under the latter definition, 46,953
(54.03%) had no matched included code. Extending the expanded
time window from same-day to ±7 days changed any-code matching
from 43.01% to 48.68%. Code-match frequencies varied by
age band, recorded sex and index year. These were descriptive,
unadjusted associations with administrative records.

**Conclusions:** Diagnosis-first reconstruction revealed the
exclusion of CT-only patients under the historical
imaging-conditioned workflow. Temporal linkage choice altered
observed procedure-code matching more than the tested five-code
vascular expansion. The lack of encounter identifiers and
uncertain procedure capture prevent translating these patterns
into verified imaging utilization or healthcare access
disparities. Further research using encounter-validated data
would be necessary for clinical utilization claims.

## Introduction — working prose

Administrative health data permit large studies of diagnostic
services, but a billing or procedure-code record is not always
equivalent to a verified procedure during a particular episode of
care. The denominator, procedure codebook, and linkage window are
therefore integral to the scientific question. Restricting the
cohort to patients with selected imaging codes additionally makes
the outcome part of the eligibility criterion. Such a cohort
cannot estimate imaging receipt among all potentially eligible
patients.

Stroke imaging provides a useful example. Noncontrast head CT,
brain MRI and intracranial or cervical angiography have different
indications and may be used at different stages of evaluation.
Contemporary stroke imaging guidance does not require every
patient to undergo each advanced modality. Consequently, a
missing MRI, CTA or MRA code cannot by itself establish
inadequate care.

We revisited a historical young-stroke imaging workflow that
selected patients through MRI/CTA/MRA coding. Our objectives
were to reconstruct an imaging-independent denominator and
quantify how procedure definitions and temporal windows change
administrative code-recording patterns. We also evaluated
whether observed-code matching varied across broad patient
strata and documented limitations that prevent clinical
utilization or disparity interpretation.

## Methods — working prose

### Data provenance and research population

We used an existing TriNetX Diamond ZIP export with diagnoses,
procedures and demographic records. No additional vendor
records could be obtained for this study. The export's sampling,
patient observation, insurance coverage and participating-site
completeness are not established by the source manifest alone,
and it should not be described as a nationally representative
population. The available diagnosis and procedure records lack
an explicit encounter or admission identifier.

The reconstruction first identified the earliest principal
ICD-10-CM I63 code **observed within calendar years 2018 and
2019** for each patient, independently of imaging. Principal
status was determined from the exported indicator. This is
not necessarily a first-ever ischemic stroke, confirmed
inpatient hospitalization, acute stroke episode or clinically
adjudicated diagnosis. Patients were then linked to their
year-of-birth and recorded sex. The working analytic age was
year of index diagnosis minus year of birth, restricted to
19–50 and recognized recorded sex. It may differ from
actual age at diagnosis by up to one year. This common
age range differs from the original workflow's sex-specific
cutoffs (up to age 54 in women and 52 in men); legacy and
new population counts must not be directly compared as
otherwise equivalent cohorts.

### Procedure-code identification and matching

The historical code list comprised head CT 70450, 70460,
70470; head CTA 70496; brain MRI 70551, 70552, 70553;
and head MRA 70544, 70545. The 14-code sensitivity
definition additionally included cervical CTA 70498,
head MRA 70546 and cervical MRA 70547, 70548, 70549.
Exact coding-system identity was retained: we did not
map other systems to CPT by numeric similarity or claim
a complete imaging-code vocabulary.

We counted patients with at least one matched listed
procedure code at 0, ±1, ±3 or ±7 calendar days of
their selected diagnosis date. The **working primary**
definition used head/brain CT, MRI, CTA and MRA codes
within ±1 day; the expanded anatomic sensitivity
included cervical CTA and MRA. Patients with no
matching included code remained in the independent
denominator. Because patient-date proximity does
not establish a common hospital encounter, outcomes
are expressly termed *recorded procedure-code matches*
and not performed imaging.

### Analytic checks and reporting

Source-manifest record counts, a complete diagnosis-first
patient index, unique code-specific imaging receipts,
retention of legacy modality/day matches, mutually
exclusive imaging-pattern groups, nested code lists,
and time-window monotonicity were reconciled before
descriptive reporting. The original procedure file
contained 1,166,493,611 rows. The expanded private
derived SQLite stored 121,033 distinct code-specific
patient-day records associated with the fixed cohort;
this number is **not** a count of distinct people or
imaging services.

We reported counts and percentages using the same
86,902-person diagnosis-indexed denominator. For
patient strata, we used broad ages 19–29, 30–39 and
40–50; recorded male and female sex; and index years
2018 and 2019. Counts and crude percentages are
descriptive, without propensity adjustment, hypothesis
testing or causal interpretation. Overlapping
modality-specific patient counts were not summed as
different people.

The codebook was appraised against historical CMS
descriptors and published stroke imaging recommendations,
not signed off by an independent clinician. Aggregate
tables and graphics remain subject to institutional
data-use and cumulative small-cell disclosure review.

## Results — working prose

### Cohort reconstruction and imaging-conditioned exclusion

The diagnosis-first search identified 962,351 patients
with a principal I63 diagnosis during 2018–2019,
before approximate-age restriction. A total of
86,902 met the age 19–50 and recorded-sex criteria.
The reconstruction retained **8,713 people** with a
CT-head code but none of the additional historical
MRI/CTA/MRA codes within ±7 days. Those
CT-only cases were not represented by the earlier
notebook's MRI/CTA/MRA-conditioned final selection.
The number **does not quantify the entire effect of
historical selection on the submitted results** because
the age rules, index-date rules and eligibility
definitions also changed.

### Procedure codebook and temporal sensitivity

For the ±1-day window, the historical nine-code list
identified at least one matching code in 39,774
patients (45.77%). The revised 14-code head-only
definition identified 39,815 (45.82%), and the
head/neck-inclusive definition 39,949 (45.97%).
The five-code expansion therefore added only 175
patients with any matched listed code, corresponding
to 0.20 percentage points of the full denominator.
The head/neck-inclusive list left 46,953 patients
(54.03%) without a matching included code.

Head/neck-inclusive any-code matching rose from
37,379 patients (43.01%) on the index date to
39,949 (45.97%) within ±1 day, 41,097
(47.29%) within ±3 days and 42,300 (48.68%)
within ±7 days. The same-day versus ±7-day
difference was approximately 5.66 percentage
points. At ±7 days, 44,602 patients (51.32%)
had no matching included code. This category
does not imply absent clinical imaging.

### Recording patterns by broad strata

Within ±1 day, the *working primary head-only*
definition matched an imaging code for 52.35%
of people aged 19–29, 48.50% of those aged
30–39 and 44.09% of those aged 40–50.
The respective head/neck-inclusive percentages
were 52.60%, 48.68% and 44.22%.

For people with female and male recorded sex,
head-only matching was 47.56% and 43.55%;
head/neck-inclusive matching was 47.71% and
43.72%. Recorded-code matching was 43.53%
for 2018 and 48.73% for 2019 under the head-only
definition (43.70% and 48.87%, respectively,
under the expanded definition). These are
unadjusted source-recording frequencies;
differences may arise from observation,
coding, case mix, indications and other factors.

### Missingness and source limitations

Among the full principal-I63 index, 10.46%
had missing or invalid birth year. In the
age-eligible group, 77.90% of race values and
75.39% of ethnicity values were missing or
unknown. Missingness is too extensive to
interpret complete-case contrasts as population
race or ethnicity imaging disparities.

## Discussion — working prose

Three related observations emerged. First,
defining eligibility through MRI/CTA/MRA
made the historical selection incapable of
retaining CT-only patients. Rebuilding the
cohort independently of imaging resolved this
specific analytic defect. Second, codebook
expansion captured additional head/neck
vascular codes but changed overall any-code
matching only slightly. Third, the temporal
matching window produced much larger changes
than this particular CPT expansion.

This comparison demonstrates sensitivity to
measurement rules within the **available
administrative extract**, not a known error
relative to a clinical ground truth. It
does not reveal whether people without codes
were imaged elsewhere, not billed in these
fields, diagnosed outside an acute episode,
or truly not imaged. In the absence of
encounter identifiers, diagnosis and procedure
dates cannot establish imaging at the same
hospitalization. Recorded differences by age,
sex and year are susceptible to unknown
care pathways, observation periods, site
mix and clinical indications.

The methodological implication is that
code-based imaging analyses need an
imaging-independent denominator, an explicit
procedure-code definition, prespecified
time windows and clear distinction between
*not observed in the included code list*
and *did not receive a procedure*. Results
should be interpreted within the
observability of the dataset.

### Limitations and needed review

This extract cannot validate admissions,
actual imaging receipt, clinical indications,
first-ever stroke, complete CPT capture or
patient observation periods. It has substantial
missingness in birth year, race and ethnicity.
The data source's selection frame, site coverage
and code-system completeness remain unresolved.
The new age restrictions differ from those in
the original study; direct magnitude comparisons
to original effect estimates are not justified.
Codebook assessment is based on published
evidence, not independent clinician sign-off.
Cross-table disclosure and existing patient-level
Parquet exposure in public Git history require
institutional data-governance review before
any release.

## Conclusion — working prose

In this pre-existing administrative stroke
extract, diagnosis-first reconstruction
retained CT-only patients omitted by the
historical imaging-conditioned workflow.
Observed imaging-code matching was more
sensitive to the temporal linkage window
than to the evaluated five-CPT expansion.
The analysis illustrates measurement
and selection issues and does not
quantify clinical imaging utilization,
hospital admissions or care disparities.

## Internal figure and table plan

- **Figure 1:** Schematic of the imaging-conditioned
  historical workflow versus imaging-independent
  diagnosis-first reconstruction. Avoid direct
  numerical comparison of non-equivalent
  age/index populations.
- **Figure 2:** Same-day, ±1, ±3 and ±7-day
  any-code matches for historic nine,
  new fourteen head-only and new fourteen
  head/neck code lists.
- **Figure 3:** Separate panels (or separate
  files) for broad age, recorded sex
  and index year. Show descriptive
  head-only and head+neck code matching.
- **Table 1:** Cohort definitions, attrition
  and missingness; include only source
  aggregates after disclosure review.
- **Table 2:** Codebook and temporal
  sensitivity table.
- **Table 3:** Broad subgroup match
  counts and descriptive percentages.

The internal manuscript figure/table generator
is in scripts/step34_manuscript_exhibits.py.

## Selected supporting literature (bibliographic placeholders)

- Wintermark M, et al. *Imaging recommendations
  for acute stroke and transient ischemic
  attack patients.* AJNR. 2013.
  PMID 23907247. DOI 10.3174/ajnr.A3690.
- Powers WJ, et al. *2019 Update to the 2018
  Guidelines for the Early Management of
  Acute Ischemic Stroke.* Stroke. 2019.
  PMID 31662037. DOI 10.1161/STR.0000000000000211.
- Abedi V, et al. *Defining the Age of
  Young Ischemic Stroke Using Data-Driven
  Approaches.* J Clin Med. 2023.
  PMID 37048683. DOI 10.3390/jcm12072600.
- CMS historical imaging CPT schedule
  referenced in docs/STEP30_EVIDENCE_REVIEW_AND_AUTHORIZATION.md.

**References require final metadata verification and
formal citation management. No publication
or IRB/data-use approval is implied here.**

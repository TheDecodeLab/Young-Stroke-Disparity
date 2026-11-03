# Step 27: fixed-data salvage protocol (NO additional TriNetX data)

**Constraint confirmed by investigator:** The study cannot obtain any
additional source data from TriNetX. All proposed analyses must rely on
the original local Diamond ZIP, already completed private SQLite
indexes, existing project files, and aggregate outputs. Do not ask
for an encounter-linked TriNetX export as a prerequisite for action.
Do not imply hospitalization can be recovered from unvalidated
patient/date proximity.

**Status:** Proposed research design for coauthor/clinical review.
This is NOT an approved primary analysis protocol, manuscript-ready
result or permission to redistribute clinical artifacts. Draft PR stays
unmerged.

## A. What changed from the rejected manuscript

The prior manuscript targeted neuroimaging disparities among young
people **hospitalized** with ischemic stroke. The current original
ZIP schema lacks an encounter or admission identifier. The old
notebook also conditioned on receipt of MRI/CTA/MRA, losing CT-only
patients, and may have selected imaging-linked diagnosis dates.

An internally verified diagnosis-first reconstruction now preserves
all qualifying principal 2018–19 I63 diagnosis candidates independent
of imaging: 962,351 patient indexes, 86,902 approximate ages 19–50
with recorded male/female sex, and under the *incomplete historical*
nine-CPT-code set at ±7 days, 8,713 CT-only, 24,074 CT plus MRI/CTA/MRA,
9,355 MRI/CTA/MRA with no CT, 44,760 with no code among these modalities.

**Do not label the cohort hospitalized stroke patients, acute
stroke admissions, first-ever stroke, or receiving no imaging.**
Do not describe historical nine-code counts as comprehensive imaging
utilization. We must change the estimand, title, population language
and interpretation together, or abandon inferential claims.

## B. Fixed-data primary study question (proposed)

> Among young people in the existing TriNetX Diamond extract with a
> first *observed during 2018–2019* principal ICD-10-CM I63 diagnosis,
> what is the frequency of **recorded brain and vascular imaging codes**
> near the diagnosis date, and how do those code-recording patterns
> differ by age, recorded sex and calendar year?

A clearly scoped title might be:

**Recorded Neuroimaging Codes Around Cerebral Infarction Diagnoses
in Young Adults: A Retrospective TriNetX Diamond Study**

This describes **coding/recording patterns** rather than
hospital utilization or inequity in imaging access. It is a
different paper from the original admission-based disparities
manuscript. Potential scientific contribution depends on confirming
the source population and code completeness, not merely sample size.

### Proposed primary population

- One **earliest observed qualifying principal I63 diagnosis in
  calendar years 2018–19** per unique person. Do not use
  'incident stroke' without a sufficient prior-history assessment.
- Uniform **approximate age 19–50** and recognized binary recorded
  sex for the primary age/sex comparison, to avoid different sex
  eligibility ranges. Sex is recorded administrative data, not
  gender identity. Sex missingness is explicitly reported.
- Use a consistent denominator independent of CT/MRI/CTA/MRA coding.
  People with no matched codes remain in denominator, with category
  **'no identified code among included modalities'**, not 'no imaging'.
- Explicitly report index diagnosis code coverage and missing birth
  year. If age is missing, the person cannot be classified reliably
  under age-restricted eligibility.
- The source has a 'Diamond Data' cohort label but no demonstrated
  population sampling frame or full enrollment/claims coverage.
  Avoid 'nationally representative' and unqualified prevalence.

### Proposed outcomes and time rule

- Indicators of at least one documented CPT/other approved imaging
  code for **CT head, MRI brain, CTA head/neck, MRA head/neck** near
  index diagnosis. Define numerator as patients with a recorded
  matched code. Do not assume recorded CPT = performed service in a
  specific admission.
- **Proposed primary link window: index day ±1 calendar day** for
  a tighter temporal association, not confirmed episode linkage.
  Pre-specify a clinical justification. Use same day, ±3 and ±7 days
  as robustness checks. The existing Step 22 indicates large window
  sensitivity; these results do not decide the primary window by
  themselves.
- Report four **nonoverlapping coding-pattern categories**:
  CT only, CT + one or more MRI/CTA/MRA, MRI/CTA/MRA without CT,
  and none of the included imaging codes. Also report modality
  indicators, which can overlap and must not be summed as distinct
  patients.
- Existing SQLite stores only nine historical CPT codes:
  do **not** reuse it to claim newly expanded neck/head coverage.

### Proposed analysis, conditional on clinical approval

1. Describe original source, diagnosis index construction,
   demographic attrition, imaging coverage and all missingness.
2. Show modality-code prevalence and *code-recording* differences
   by year, age band, and recorded sex; include uncertainty
   intervals where suitable and never causal language.
3. If methodologically justified after codebook/data-capture review,
   fit exploratory age- and year-adjusted models for each modality
   recording outcome by sex. Clearly identify residual confounding
   from unobserved facility, severity, coverage and access.
4. Treat race and ethnicity **primarily as missingness/data quality
   findings**: missing/unknown race 77.9%, ethnicity 75.39% of
   age-eligible patients. Do not foreground adjusted racial or
   ethnic disparity effect estimates. A restricted descriptive
   complete-case appendix would require an explicit
   nonrepresentativeness and selection-bias argument.
5. Sensitivity: same-day, ±1, ±3 and ±7 days, 2018 vs 2019,
   diagnosis subcodes, and sex-specific historical age cutoffs
   (women 19–54, men 19–52) **only if expanded source linkage
   is rebuilt**. Do not assume saved 19–50 imaging database covers
   older ages.
6. Make no mortality, clinical outcome, admission, first-ever stroke,
   imaging indication, or access disparities inference not supported
   by the existing source.

## C. Two essential feasibility checks BEFORE another full procedure scan

**Check 1: diagnosis/index and source selection.** Review existing
cohort metadata and definitions for how the Diamond source population
was selected, whether it was prefiltered for stroke, how
'principal_diagnosis_indicator=P' is assigned, and whether any
patient-observation coverage, facility, or code-system identifiers
already exist in the local ZIP. This is source documentation review,
**not** a request for additional data. The prior header inventory
found no explicit encounter ID.

**Check 2: imaging codebook.** Obtain *clinical approval of
definitions*, not more TriNetX data. Historical CPT codes:

- CT head: 70450, 70460, 70470
- MRI brain: 70551, 70552, 70553
- CTA head: 70496
- MRA head: 70544, 70545

Candidate additions **for verification, not auto-applied**:
CTA neck 70498; MRA head 70546; MRA neck 70547–70549.
Review procedure code systems actually represented in the archive,
including HCPCS and ICD-10-PCS; not every code implies the same
service and codes may vary in precision. Specify how to handle
diagnostic vs procedural claim duplication and dates.

**Decision:** If an approved comprehensive codebook remains feasible
with the existing extract, implement ONE additional full
\`procedure.csv\` extraction, preserving original diagnosis-first
denominator, private data, and a strict source manifest check.
Store all approved event-level code/modality/date information privately
so subsequent window and sensitivity analyses do not require
further billion-row scans. Do not scan a second time before sign-off.

If the majority of people still have no covered procedure codes
after an approved expansion and source documentation cannot establish
what absence means, the research question may be too vulnerable to
incomplete capture for substantive imaging comparisons. Consider a
methods/data-quality paper instead, or decide not to use this
dataset for the revised analysis.

## D. Hard constraints and publication go/no-go criteria

- No new TriNetX records, encounters, admissions, dates,
  insurance enrollment or hospital identifiers will be assumed.
- No patient-level clinical data or ZIP contents in GitHub/ChatGPT.
  Analyze only in approved private local storage. Review existing
  sensitive Git history and authorized dissemination rules.
- No 'hospitalized' framing, causal access/equity claim,
  incident-stroke or complete-case race generalization.
- **Go/no-go 1:** Clinician and lead investigator approve the
  *new* research question, population, sex/age rules, diagnosis
  codebook, and primary time window.
- **Go/no-go 2:** Team documents reasonable imaging-code coverage
  and a rationale that recorded-code comparisons have meaning in
  this extract. Record how much may be missing.
- **Go/no-go 3:** Data-use/release restrictions and cumulative
  small-cell disclosure pass institutional review.

If these checks fail, do not invest in regression modeling or an
unqualified disparities manuscript. Preserve the completed
reconstruction as a reproducibility and selection-bias audit.

## E. Handoff

Please ask a stroke clinician/PI to review this **fixed-data** plan
and choose among: (1) qualified recorded-imaging analysis,
(2) methods/data-quality analysis, or (3) discontinue use of this
dataset for this manuscript. Record the decision in approved storage.
The PR remains draft.

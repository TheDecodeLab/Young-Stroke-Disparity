# Post-Step77 measurement decision and clinical code review protocol

**Decision date:** 2026-10-20  
**Status:** Step77 completed locally; exact PCS clinician adjudication and
final imaging outcome freeze **not yet completed**.

This is a research decision protocol, not a statement of established
patient-care inequity or a clinical coding approval. Source-derived
patient and procedure counts remain in investigator-controlled private
Step68/74/76/77 outputs. Do not commit or externally circulate
the observed-code list, counts, or model result tables without release
approval.

## What is now established

1. **The primary population is the uniform 18–50 indexed I63 cohort.**
   The earlier historical cohort uses sex-dependent age eligibility,
   overlaps with the uniform cohort, and is a sensitivity population,
   not a second independent sample.
2. **The original endpoint is a documented CPT14 procedure-code
   marker on the frozen indexed IMP encounter.** Absence of a code
   does not demonstrate absent imaging; presence of a code is not
   proof that a scan was performed, at a particular HCO, or as
   part of the stroke episode.
3. **P does not mean verified principal-versus-secondary stroke
   diagnosis.** P=0 includes secondary, blank and other
   unmarked records. Recording practice, diagnosis position
   and encounter attribution plausibly affect comparisons,
   but no mechanism has been causally established.
4. **Broader same-admission-calendar-day capture changes apparent
   P differences and is sensitive to quarantined encounter
   records.** It is NOT verified same-hospital or same-episode
   imaging and must be explicitly identified as an exploratory
   sensitivity rather than a substitute primary endpoint.
5. **Candidate ICD-10-PCS brain/head-neck procedure codes have
   nearly complete official B-section catalog matches**
   in the coarse FY-neighbor screen, but their clinical
   indications, discharge-date effectiveness, relationship
   to the index admission, and CPT14 overlap remain unverified.
6. **The Step77 impossible-to-exceed source-row ceiling shows
   that these particular PCS candidates alone cannot eliminate
   the negative P=1 versus P=0 inpatient CPT14 association.**
   The mathematical upper bound is NOT the observed rate
   after adding PCS codes. Other coding systems, source coverage,
   and encounter attribution are outside this bound.
7. Exploratory adjusted demographic coded-capture models
   are not validated care disparities. Race/ethnicity have
   substantial unknown/unmapped fields; hospital selection,
   severity, independent patient imaging completion
   and institutional coding variation remain unresolved.
   Working-binomial uncertainty was overdispersed and
   not HCO-cluster corrected.

## Working endpoint hierarchy pending final investigator approval

| Rank | Endpoint | Interpretation | Status |
|---|---|---|---|
| 1 | Indexed IMP CPT14 any neuroimaging code | Recorded code *on the frozen index inpatient encounter* | Working main descriptive endpoint, **not actual receipt of care** |
| 2 | Indexed IMP CPT14 by CT head, MRI brain, CTA head/neck, MRA head/neck | Recorded modality-specific code | Sensitivity and code-family analysis |
| 3 | Indexed IMP CPT14 **OR** other encounter on same calendar day | Any same-day recorded code; episode and HCO unverified | High-risk exploratory attachment sensitivity |
| 4 | Indexed IMP **OR uniquely linked preceding ED** CPT14 | Conservative linkage sensitivity; limited capture | Sensitivity |
| 5 | Clinically reviewed, exact-year PCS CNS/head-neck vascular code | Alternate inpatient code system, overlap with CPT unknown | **Not yet an authorized patient-level endpoint** |

Do not blend ranks 1–5 into a single imaging care rate
or claim that all ranking alternatives have equal validity.
When presenting any descriptive difference, label
the numerator as **documented CPT14 code capture** and the
comparison as between unvalidated P indicator groups.
Do not phrase the disparity models as differences
in performed imaging or appropriate stroke-care access.

## Operational clinical reviewer workflow

The restricted workstation-only worksheet created by Step77 is:

```text
results/phase1/full_reconstruction_private/
step77_decision_gate_private/
step77_clinical_code_review_LOCAL_ONLY.csv
```

It contains a source-derived list of candidate seven-character
codes and public CMS title variants. It does not contain person
identifiers or patient-level records, but it is **still restricted**
because the observed-in-source selection itself conveys
information about the private cohort. Keep it on the approved
workstation and do not upload to third-party services.

For each exact code, a clinically qualified reviewer should:

1. Verify the **seven-character code** in the public official
   CMS fiscal-year table(s) corresponding to the service
   period. Distinguish annual release validity from any
   October/April effective-date transitions and
   individual discharge-date validity.
2. Identify the actual **anatomic territory**. For B32/B33
   verify intracranial, carotid or vertebral circulation;
   do not automatically accept all upper-artery body parts.
   Check CNS B02/B03 body parts for brain/head relevance.
3. Determine **diagnostic acquisition versus adjunct,
   therapeutic, non-target, or unsupported procedure**.
   Assess whether contrast and angiographic method are
   truly inferable from the CMS title/code or remain unclear.
4. Mark **INCLUDE**, **EXCLUDE**, or **UNCERTAIN** in the
   private worksheet; supply a short reviewer rationale,
   initials/date, and official source-version evidence.
   Keep ambiguous codes out of an eventual primary
   definition until they can be adjudicated.
5. If reviewers disagree, preserve both interpretations
   and reconcile before locking the **public-only**
   codebook with official citations. Avoid using cohort
   outcome frequencies to decide code meaning.

The ultimate shareable codebook must be created from **public
CMS evidence**, including codes *not necessarily observed* in
the private data, and should not disclose which codes appeared
in the research-network source. It must contain exact code,
year-effective dates, clinical meaning, site, modality,
inclusion/exclusion rationale, and review provenance.

## Stop/go rule for any further source processing

**Default: STOP.** No new full-source procedure scan, cohort
rebuild, new PCS-inclusive patient classification or additional
demographic GLM simply because a code matches CMS.

A further targeted, checkpointed patient-level source
pass is scientifically justified only if ALL are true:

- A clinically reviewed year-appropriate codebook exists.
- A specific previously unanswered hypothesis requires
  distinct-patient code capture and CPT overlap.
- Existing private aggregates cannot already bound or answer
  that question.
- The expected decision value outweighs the high read cost
  and the source-access/privacy obligations are satisfied.
- The run is scoped, restartable, and has explicit baseline
  reconciliation and disclosure controls.

A strong standalone descriptive paper about code-ascertainment
and encounter attachment may be possible before clinical care
claims; the investigator should separately decide whether its
design, interpretation and source licensing support submission.

## Next action, not another code execution gate

Clinical/coding adjudication of the 40-code private worksheet,
or a **public-only** independent exact-code CMS mapping review,
followed by freezing the primary documented-code estimand.
The automated Step77 analysis itself is COMPLETE. There is
no pending command to rerun unless the workstation's
private reviewer worksheet needs restoration.

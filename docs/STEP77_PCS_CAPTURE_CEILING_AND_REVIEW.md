# Step77: PCS candidate patient-gain ceiling and clinician codebook worksheet

**Status:** Read-only script, fabricated-only tests, and private-review
workflow committed; investigator local execution pending. No procedure
source scan or additional demographic modeling.

## What completed Step76 actually established

The investigator's Step76 local run succeeded (six dedicated
synthetic checks and **721 total repository tests passed**).
It identified **40 exact ICD-10-PCS codes** and 5,670 review-only
source procedure row×cohort memberships:

| Context | Candidate source rows |
|---|---:|
| Index inpatient encounter | 5,575 |
| Other encounter on index admission day | 77 |
| Unique preceding ED linkage | 18 |

Modality-screen distribution across these contexts:
CNS CT 728; CNS MRI 1,253; upper-artery CT 3,133;
upper-artery MR 556. The two overlapping age cohorts
are **not independent**, and one person may contribute
multiple source procedure records.

**Crucial limitation:** Every Step76 entry passed the
anatomy keyword screen, but this is NOT an independent
clinical validation. Step74 had already preselected
B02/B03/B32/B33 titles mentioning brain, carotid,
vertebral, intracranial, head or neck, so many screen
results are circular. Individual exact code descriptions
and possible contrast must be reviewed by a human
with clinical/coding expertise and correct year-effective
CMS definitions. Neither imaging completion nor
same-hospital encounter attribution has been verified.

Step76 also observed candidate rows / total section-B
procedure rows of 11.02% in 2016–2018,
4.04% in 2019–2021, and 4.46% in 2022–2024.
This is a **source coding mix** change, not a time trend
in patient imaging utilization.

## New decision: an upper bound without rescanning

Before undertaking another ~993-million-row procedure
source scan, bound the **maximum** gain in original
same-index inpatient imaging-code capture.

Step68's primary uniform 18–50 cohort patient totals:
- `P=0`: n=43,727, original CPT14 n=18,031.
- `P=1`: n=20,994, original CPT14 n=4,172.

Step74's index-IMP PCS review-candidate **SOURCE
row memberships across both overlapping cohorts**:
- `P=0`: at most 4,119 such source rows.
- `P=1`: at most 1,456 such source rows.

The candidate source-row count across both overlapping
cohorts upper-bounds distinct patients newly CPT14-positive
within **either one** cohort: every newly captured
patient needs at least one candidate row, and one
source procedure can be counted in both cohorts.
This upper bound is intentionally generous because
it assumes *every* candidate code is clinically
correct, belongs to a distinct primary-cohort
patient, occurs on the relevant index, and was not
already CPT14-positive.

Thus the theoretical `P=1` ceiling is
`(4,172 + 1,456)/20,994 = 26.81%`;
the original `P=0` CPT14 rate remains
`18,031/43,727 = 41.24%`.
Even if `P=0` receives **zero** PCS improvement,
the negative `P=1` versus `P=0`
association cannot disappear from adding
ONLY these index-IMP PCS candidates.
This is a **mathematical source-count ceiling**,
not an observed expanded outcome or a causal
explanation of the P discrepancy. Other
systems (e.g., SNOMED/HCPCS), episode
attribution, and incomplete source capture
have not been ruled out. P=0 is not a
clinically confirmed secondary-stroke group.

## What the new Step77 script does

`scripts/step77_pcs_gain_ceiling_and_clinical_review.py`
reads only:
- Completed private Step68 aggregate JSON
  (`patient_cohort_aggregates`, patient-level
  original CPT14 capture);
- Completed private Step74 aggregate JSON
  (exact-code, year, P, encounter context
  *source row* counts);
- Step76 restricted private exact-code review
  queue (official CMS title variants and status).

The script independently checks P-specific
frozen denominators and code-review source
row totals, applies `min(n-CPT14, PCS_source_rows)`
to obtain an impossible-to-exceed **distinct-patient
gain upper bound**, and prints safe aggregate
rates and resulting smallest possible P0-P1
index-coded capture gap.

It saves one **LOCAL ONLY clinician-review CSV**
with 40 exact codes, their available official
CMS title variants and observed source service
years. Each row contains **blank/PENDING clinical
fields**, including anatomical site, method,
contrast (where actually determinable),
include/exclude decision, evidence/rationale,
reviewer and effective discharge-date check.
It does **not** assert any codes are clinically
approved, issue person-level capture flags,
or upload source-derived records to GitHub.
Private source frequencies are not included
in the clinician CSV; the **observed code list
itself** is still source-derived and restricted.

## One local run

```bash
(
  set -e
  git pull --ff-only origin analysis-rebuild-phase1-audit
  python -m py_compile scripts/step77_pcs_gain_ceiling_and_clinical_review.py
  python -m pytest -q tests/test_step77_pcs_gain_ceiling_and_clinical_review.py
  python -m pytest -q
  python scripts/step77_pcs_gain_ceiling_and_clinical_review.py
)
```

Script uses completed read-only private JSON files
with no source table reread, no external network,
and no CMS downloads. It is non-overwriting
for the private CSV so a completed adjudication
is never silently destroyed.

**Handoff: TERMINAL OUTPUT ONLY**; no ZIP, source
SQLite, private source-derived JSON, or CSV upload
is requested.

Private worksheet (do not share absent clearance):

`results/phase1/full_reconstruction_private/step77_decision_gate_private/step77_clinical_code_review_LOCAL_ONLY.csv`

## Next scientific gate

1. Clinician/coding reviewer adjudicates exact
   CNS/upper-arterial anatomic target and method,
   rejecting unrelated territories and unclear
   descriptions; document year-specific
   discharge-date validity and contrast ambiguity.
2. Freeze a public-only, reviewed and
   year-valid codebook (code,
   CMS description, modality, inclusion/exclusion,
   version dates, clinical rationale).
   Do not publish or commit any indication that
   a code was specifically observed in private
   TriNetX records without release review.
3. Treat ICD-10-PCS as a **secondary
   sensitivity**, not an automatic replacement
   of same-index CPT14: even the unrealistic
   code-only ceiling cannot resolve the
   central P recording mismatch.
4. Revisit a costly checkpointed patient-level
   source pass only if another explicitly
   justified code system/encounter hypothesis
   is likely to change the main conclusions,
   and the codebook has been reviewed first.
5. The current clinical imaging-disparity
   claims remain **not publication-ready**
   without HCO/episode, severity and
   performed-imaging validation. Descriptive
   CPT14 code-capture associations remain
   reportable only with accurate limitations.

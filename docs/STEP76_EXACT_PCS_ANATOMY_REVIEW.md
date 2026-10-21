# Step76: Exact ICD-10-PCS anatomy review, year trends and codebook decision

**Status (2026-10-20):** Completed on the authorized workstation:
all new synthetic checks and the full repository suite passed,
the Step74 exact-code profiles reconciled, and a LOCAL ONLY
source-derived exact-code review queue was generated.
No original procedure-source scan took place.

**Interpretation:** Candidates were preselected by Step74's
anatomy keywords, so a 100% positive repeat keyword screen
in Step76 is not independent clinical validation.
A marked change in candidate-code source-row fractions over
time is a source coding representation signal, not a
patient imaging utilization trend.

[Step77](STEP77_PCS_CAPTURE_CEILING_AND_REVIEW.md) computes an
unrealistically generous patient-gain upper bound and builds
the restricted clinician codebook-review worksheet.
The quantitative Step76 results and exact observed-source
code list remain LOCAL ONLY and require release approval
before public use.

## Step75 / Step76 source evidence for this gate

Step75 resolved the CMS imaging-section denominator issue and
demonstrated strong year-neighbor catalog matches among
syntactically well-formed section-B source rows.
Step76 then identified a restricted set of exact PCS codes with
plausible CNS/head-neck vascular titles, but the underlying
source procedure rows can duplicate people and occur in two
overlapping cohort definitions.

The exact source-derived candidate counts and source-row
time-profile evidence are retained in the completed
PRIVATE local Step74–Step76 reports. They are not
equivalent to distinct additional imaging patients.
No automatic expansion of the original frozen CPT14
imaging-code outcome is authorized by these screens.

## Independent public source rules

Official historic CMS ICD-10-PCS tables document:
- B02: CNS computerized tomography.
- B03: CNS magnetic resonance imaging.
- B32: upper-arteries computerized tomography,
  including carotid/vertebral/intracranial **and
  unrelated sites**.
- B33: upper-arteries magnetic resonance imaging,
  likewise with multiple body parts.

The code must be **an exact seven-character title**,
not merely a three-character family prefix.
A broad category such as B32 is not synonymous
with CTA of head and neck. The procedure-year FY
Y / FY Y+1 match remains provisional because
exact discharge dates and interim code versions
are unavailable from Step68's code-profile table.

Public references:
- https://www.cms.gov/files/document/2016-pcs-code-tables.pdf
- https://www.cms.gov/files/document/icd-10-pcs-2019-tables-and-index-pdf.pdf
- https://www.cms.gov/medicare/coding-billing/icd-10-codes

## What the read-only script does

`scripts/step76_exact_PCS_anatomy_review.py`:

1. Validates the *already cached* official FY2016–2025
   CMS ZIP hashes through the Step75 public-cache loader.
2. Compares EVERY Step74 locally stored exact candidate
   code, official title, procedure service year,
   unvalidated P label and encounter context
   with the cached code titles. Rejects changed
   titles or duplicated candidate records.
3. Adds rule-based **ANATOMY SCREEN ONLY**:
   brain/CNS CT/MR with brain/cerebral/intracranial/head
   wording; arterial CT/MR with carotid,
   vertebral arteries, intracranial arteries,
   or cervico-cerebral anatomy; otherwise
   `ANATOMY_UNRESOLVED`. Any description changing
   classifications between neighboring CMS years
   is explicitly flagged for manual review.
4. Reconciles exact-code source-row counts to
   the existing Step74 source-year×P×scope aggregates.
5. Uses a read-only query of the **saved Step68
   code-profile SQLite table**, NOT the original
   procedure file, to calculate the correct
   imaging-section B denominator by source year
   and context. Checks its all-PCS source totals
   independently against Step74.
6. Prints the candidate composition by modality
   family, year, unvalidated P group and scope,
   plus broad time trends of candidates per
   **B-section source row**. Small aggregated
   values are suppressed and exact code strings
   are NOT printed.
7. Saves a restricted private JSON queue with
   each candidate's observed exact code,
   official title, service years, source context,
   source row frequency and **PENDING CLINICAL
   APPROVAL** status. The candidate list is a
   source-derived record, not safe to commit
   or send absent appropriate institutional
   disclosure clearance.

The three FY blocks are **2016–2018,
2019–2021, and 2022–2024**. They are code
representation screens and not patient-level
imaging prevalence, because the denominator
is source procedures (not stroke patients).

The user-approved default:
**No TriNetX/CTSI email unless a specific
unresolvable detail proves essential.**

## One bundled run

```bash
(
  set -e
  git pull --ff-only origin analysis-rebuild-phase1-audit
  python -m py_compile scripts/step76_exact_PCS_anatomy_review.py
  python -m pytest -q tests/test_step76_exact_PCS_anatomy_review.py
  python -m pytest -q
  python scripts/step76_exact_PCS_anatomy_review.py
)
```

Synthetic tests must pass before local analysis.
No additional internet or source ZIP is needed.

**Handoff: TERMINAL OUTPUT ONLY.**
Do not upload code-profile databases, official cache
ZIPs, source files or the private JSON.

Private file, **not requested for upload**:

`results/phase1/full_reconstruction_private/step76_code_review_private/step76_exact_PCS_review_queue_LOCAL_ONLY.json`

## Decision gate after Step76

- Quantify how many candidate source rows have exact
  title support for stroke-relevant brain or
  carotid/vertebral/intracranial imaging and
  how many require manual anatomical review.
- Inspect time trends for coding-system drift,
  **without claiming trends in patient utilization**.
- Draft an exact-code public-only, year-valid
  review table; require a reviewed codebook
  before adding any non-CPT14 patient-level outcome.
- Determine if benefit and feasibility justify one
  checkpointed future source reprocessing pass.
  Step68 retained **source code frequencies** for
  PCS, not per-patient PCS imaging flags, so
  we cannot calculate distinct patient gains
  or CPT overlap from Steps74–76 alone.
- If additional codes are not sufficiently useful,
  retain original frozen CPT14 outcome and
  acknowledge incompleteness as a limitation.

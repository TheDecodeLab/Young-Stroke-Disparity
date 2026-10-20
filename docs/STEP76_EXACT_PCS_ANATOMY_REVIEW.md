# Step76: Exact ICD-10-PCS anatomy review, year trends and codebook decision

**Status:** Read-only code and fabricated-only tests committed.
The investigator has not yet executed Step76 locally. Uses only
completed Step68, Step74, Step75 local results and cached public
CMS FY2016–FY2025 catalogs. **NO source procedure ZIP rescan.**

## Step75 result that motivates this step

Step75 completed on the authorized workstation with seven dedicated
tests and **715 repository tests** passing. Section-B-specific,
year-adjacent CMS matching reconciled exactly to Step74.

The previous apparent CMS validity problem was a denominator
artifact: out of **447,495** indexed-IMP ICD-10-PCS source
row×cohort memberships, only **85,480** were imaging-section
B rows. **85,445 / 85,480 = 99.96%** were well-formed,
matching the FY Y or Y+1 code-title catalogs; 35 B rows
were malformed. ED and same-day non-index B rows were
100% matched among the source-year-neighbor catalogs.

The **5,575** inpatient source-row candidate tags
(718 B02 CNS CT, 1,236 B03 CNS MRI, 3,069 B32
upper-artery CT, 552 B33 upper-artery MRI)
are **NOT 5,575 new imaged patients**. They include
repeat codes, overlapping cohort membership, known
cross-system non-independence and uncertain same-HCO
episode linkage. Step75's broad B section includes
many imaging sites unrelated to stroke. Codebook
anatomy and specificity must be established first.

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

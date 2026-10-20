# Step69: Investigate same-day cross-encounter imaging-code attachment

**Status:** Read-only Python implementation and fabricated synthetic tests
committed. The real local execution has NOT yet been run.

## Why Step69 follows Step68

One complete procedure-source scan already established that the primary
same-IMP CPT14 capture rates differ sharply by unvalidated I63 `P`
indicator, while CPT14 recorded on a different encounter on the same
calendar day is substantially more common in the otherwise
inpatient-CPT-negative P-labelled cohort. The strict unique preceding
ED encounter explains only a small part of the discrepancy.

This is a potentially important **encounter-attachment / coding
representation artifact**, not evidence that one diagnosis group
received more imaging or better stroke care. Step68's other-encounter
time window is *same patient*, not necessarily same institution or
clinical admission. Step63 does not retain all other encounter
types, so the other-day0 event's hospital and encounter role
cannot be inferred from Step68 alone.

## Read-only scientific questions

`scripts/step69_same_day_attachment_diagnostics.py` takes
the already-completed, separate Step62, Step63 and Step68 SQLite
checkpoints, verifies their source signatures and original
same-IMP CPT14 numerator, and calculates at **one
patient per cohort**:

1. `P=0` versus `P=1` baseline code capture, additional CPT14
   on another encounter on **the index admission date**, and
   the combined exploratory rate. This tests whether the
   apparently lower P=1 inpatient-only code capture persists
   when encounters on the same day are included.
2. The **new same-day capture by presence/absence of frozen
   reciprocally unique ED link**. If the excess is largely
   among patients *without* that link, the strict ED pathway
   cannot by itself account for the finding.
3. The **new same-day capture by patient-level Step63
   quarantine status**. Differences may reflect unreliable
   key assignment or incomplete encounter semantics.
4. Exact overlap between ED code recovery and
   another-encounter same-day code recovery, plus -2d, -7d
   and +2d timing sensitivity. These are **patient-level
   unions**, not sums of partly overlapping windows.
5. Modality-by-P and year-by-P differences to identify whether
   vascular CT versus brain MRI or earlier periods dominate.
6. A **code-system discovery** screen using only the
   existing Step68 exact-code *row-frequency* table.
   It counts syntactically plausible seven-character
   ICD-10-PCS values beginning with `B`, broken down
   by P and context and, for indexed inpatient records,
   procedure-service year. Three-character family prefixes
   are printed only when aggregate row count is at least 11.
   These are **unreviewed candidate section-B source rows**,
   not clinically verified imaging codes or patient-level
   outcomes. A valid PCS section-B prefix by itself does
   not identify head CT, CTA, MRI or MRA.

No code profile, patient or encounter ID, private SQLite, or
exact source code strings are printed or transmitted. Console
aggregates remain subject to institutional disclosure review.

## One local run, no source scan

From the repository root:

```bash
(
  set -e
  git pull --ff-only origin analysis-rebuild-phase1-audit
  python -m py_compile scripts/step69_same_day_attachment_diagnostics.py
  python -m pytest -q tests/test_step69_same_day_attachment_diagnostics.py
  python -m pytest -q
  python scripts/step69_same_day_attachment_diagnostics.py
)
```

If compilation or tests fail, the fail-fast subshell stops without
starting the analysis. The new tests are not yet confirmed on the
investigator's workstation. This run **does not need the source ZIP**
and makes **no writes** to Steps62,63,68 or any clinical records.

Inputs, **stay local**:

- `results/phase1/full_reconstruction_private/step62_cohort_private/provisional_cohort_LOCAL_ONLY.sqlite`
- `results/phase1/full_reconstruction_private/step63_ed_sensitivity_private/step63_ed_feasibility_LOCAL_ONLY.sqlite`
- `results/phase1/full_reconstruction_private/step68_procedure_windows_private/step68_procedure_windows_LOCAL_ONLY.sqlite`
- `results/phase1/full_reconstruction_private/step68_procedure_windows_private/step68_aggregate_LOCAL_ONLY.json`

These should NOT be uploaded or committed.

**Requested next handoff: TERMINAL OUTPUT ONLY.** No ZIP or attached
result files needed. Use the command's aggregate stdout under
institutional disclosure requirements.

## Decision after output

If same-day non-index CPT14 is concentrated among unlinked patients
and persists across years/modalities, the key limitation is assigning
clinically related procedures to the index encounter. We may use
same-day/short-window code capture as an explicitly labeled
**sensitivity endpoint**, but not describe it as same-hospital
inpatient imaging. Compare primary CPT14 conclusions against
the window sensitivity before demographic inference.

If ICD-10-PCS B-prefixed source rows are frequent, follow the
existing Step67 literature-first path to identify **exact
year-specific clinically relevant codes**. No patient imaging
status should be assigned from candidate prefixes alone.
Expanding to code-system-defined patient outcomes will
require separate analysis planning because Step68 retained
non-CPT14 code *row counts*, not per-patient clinical classifications.

Do not claim evidence for a national care-quality disparity
without source/coding capture sensitivity and explicit HCO
participation limitations.

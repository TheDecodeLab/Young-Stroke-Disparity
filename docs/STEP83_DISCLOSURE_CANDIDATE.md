# Step83: Local-only disclosure-aware candidate tables

**Status (2026-10-25):** Verified on the investigator's authorized workstation. Nine targeted tests passed and the full suite passed **795 tests** with three previously observed warnings. The Step83 private candidate was generated successfully. It independently verified one frozen Step82 disclosure flag, applied **overall_only** sex display and **three_groups** patient-flow display, and reconciled every displayed category/denominator total. **This is numerical and preliminary disclosure screening, not institutional approval.** No source-derived table values or private files were committed to GitHub. See [Step84 publication release gate](STEP84_SUBMISSION_RELEASE_GATE.md).

## Motivation

Step82 on the investigator workstation passed 10 targeted tests, 786 total repository tests, and final selection / demographic reconciliations. It reported one preliminary small-cell/complement flag in SEX, P=1. The affected specific category and count are not needed for this step and must not be shared. Masking only that cell would permit reconstruction from the displayed category total and P=0 value.

## Reporting policy

1. Preserve the original Step82 private JSON untouched, as the source of truth.
2. Create new restricted `reporting_candidate_LOCAL_ONLY.json` and `.md` files using the Step82 **aggregate JSON only**. No ZIP/SQLite scan is performed.
3. Show sex categories overall only. Do **not** show P=0 or P=1 counts or percentages for *any* sex category, irrespective of which cell caused the flag. Overall sex categories still must independently pass the 11-event/complement screen.
4. For other dimensions, show overall, P=0 and P=1 only if all cells pass the 11-event/complement screen. If any subgroup cell is flagged, retain overall categories only if they are safe. If an overall cell is flagged, withhold the entire dimension. A fully withheld dimension remains marked as such in the internal candidate.
5. For the patient-flow table, start at **unique patients with retained I63-coded qualifying IMP keys**. Include the indexed group and a nonindexed group. Separate competing-index and no-eligible-index dispositions only when neither underlying group is small; otherwise collapse them into a single nonindexed category. Never treat admission-key counts as unique patient exclusions.
6. Validate independent sums, column denominators, source percentages, the full Step82 disclosure-warning set, and patient-flow partition before writing. Abort on any mismatch. Do not overwrite an existing output.
7. The 11-count screen is only an internal preliminary guard, not institutional authorization. Cross-table differencing against the original manuscript, supplement, figures or prior releases remains possible. An authorized institutional review of the proposed **complete output set** is mandatory before circulation, journal submission, or inclusion in a shared document.

## Run from the repository root

```bash
(
  set -e
  git pull --ff-only origin analysis-rebuild-phase1-audit
  python -m pytest -q tests/test_step83_disclosure_candidate.py
  python -m pytest -q
  python scripts/step83_disclosure_candidate.py \
    --acknowledge I_CONFIRM_INTERNAL_REVIEW_ONLY
)
```

The restricted result files are written only to:

```
results/phase1/full_reconstruction_private/step83_reporting_candidate_private/
```

The output directory is owner-only (0700), and the two files are owner-only (0600). Do not upload, email, share or commit these output files before approved disclosure review. **Only the terminal summary** should be returned for initial QC; it prints no row values or suppressed category identities.

## Remaining journal submission tasks

These candidate tables do not establish a complete source-to-cohort STROBE selection flow, an approved TriNetX extraction date, IRB status, participating-network release permissions, hospital-based imaging ascertainment, or population-level race/sex inequity. After approved aggregation, update the v1.5 manuscript and supplement through granular DOCX tracked changes while retaining Zotero fields. Independently approve the complete manuscript/figures/subgroup collection for cumulative disclosure.
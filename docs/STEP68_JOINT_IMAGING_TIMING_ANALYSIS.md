# Step68: One-pass ED-versus-inpatient CPT14 timing test and code discovery

**Status:** Python 3.9 synthetic-only implementation awaiting investigator
workstation tests. The new procedure source scan has NOT yet been run.
Do not run if tests fail. Outputs are strictly LOCAL ONLY and must never
be committed or uploaded without institutional review.

## Research hypotheses

**H1: Encounter attachment contributes to the unusual P contrast.**
Step62 grouped indexed ischemic-stroke-code admissions by whether
any I63 code was marked principal (`P=1`). `P=0` includes secondary,
blank and other unmarked indicators, NOT independently confirmed
secondary stroke. The 14-CPT same-IMP code-capture rates differ sharply
between those strata. H1 predicts that additional imaging codes
may occur on a *different* ED encounter close to admission, especially
for patients lacking same-IMP CPT14. The previous Steps64/66 were
hypothetical upper bounds. Step68 measures actual recorded CPT14
events on a frozen linked ED encounter.

**H2: Broader patient-relative windows reveal codes even without
a unique ED link.** Same-patient CPT14 code events in the -2 to -1
calendar days before admission, admission day (another encounter),
and -7 to -1 days (another encounter) are examined independently.
These are deliberate **sensitivity screens**, not verified care
transitions. We never call a procedure on a different encounter
part of an inpatient episode simply because the date is close.

**H3: Coding-system representation explains missing CPT14 capture.**
Within index IMP and uniquely linked ED stays, Step68 captures
source frequency counts for EXACT CPT/ICD-10-PCS/HCPCS/SNOMED strings
in a **private-only** SQL `code_profile` table, with context. This
makes a later public-codebook/availability review possible without a
second blind full procedure scan. Non-CPT14 codes are never
automatically classified as brain/vascular imaging.

## What the single procedure pass does

Script: `scripts/step68_joint_imaging_window_scan.py`

- Uses frozen Step62 indexed patients (both overlapping cohorts)
  and Step63 reciprocal-unique EMER-to-IMP candidate links.
- Checks Step62/Step63 fingerprints and Step63 link policy.
- Reads the single source `procedure.csv` inside the unchanged
  approved TriNetX ZIP with atomic SQLite batch checkpoints,
  full source row-count reconciliation, and resumption. Does NOT
  reread the completed diagnosis or encounter members as source.
- For CPT14 codes, stores only patient/cohort/modality bit masks
  indicating same-IMP stay, frozen ED stay, frozen ED with both
  critical linking date flags `F`, and patient-relative timing
  masks. One source row can set multiple masks and belong to both
  overlapping cohorts, but cannot inflate patient counts.
- Computes patient-cohort aggregate records by cohort, P, year,
  and year x P, preserving original Step62 denominators. A
  `new_ED` patient has a CPT14 on the unique ED encounter but
  NO CPT14 on the indexed IMP. Similarly `new_nonIMP_pre2`
  has a CPT14 on another encounter in the preceding 2 days but
  no original same-IMP CPT14.
- Performs independent same-IMP CPT14 baseline reconciliation
  against Step62's `image` table. If results differ, aborts
  final reporting rather than silently revising the primary
  outcome. The source ZIP, row counts and private DB signatures
  are frozen, and the scanner refuses changed data.
- Saves a **LOCAL ONLY** SQLite and aggregate JSON. The console
  prints aggregate patient-level `n`, `IMP_CPT14`,
  `ED_new`, `ED_F_new`, and non-index windows by group.
  Small groups are suppressed. The console output and JSON are
  still not disclosure-cleared.

Code-profile `n` means **source procedure rows × cohort memberships**
within an encounter/time context, not distinct patients, completed
scans, or modality classification. The `code_profile` table contains
raw source code strings and is PRIVATE; neither code frequencies nor
patient/encounter IDs belong in the GitHub source tree.

The broader windows are *not monotonic* with strict linked ED,
because date-only and encounter-associated scopes differ. Do not
interpret increments from separate overlapping windows as additive.
The date flag `F` is a conservative provenance rule only, not proof
that it matches a hospital record.

## One combined local run, after tests

Run the following from the repository root. The command deliberately
uses a fail-fast subshell: if **any** test fails the scan does not start.

```bash
(
  set -e
  git pull --ff-only origin analysis-rebuild-phase1-audit
  python -m py_compile scripts/step68_joint_imaging_window_scan.py
  python -m pytest -q tests/test_step68_joint_imaging_window_scan.py
  python -m pytest -q
  python scripts/step68_joint_imaging_window_scan.py \
    --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip" \
    --stage all \
    --acknowledge I_CONFIRM_EXISTING_PROTOCOL_PERMITS_LOCAL_COHORT_RECONSTRUCTION
)
```

The scan is of the **completed, previously source-verified
993,025,015-row** procedure file. This is a substantial one-time
I/O operation. It prints source checkpoint progress. On a crash or
interruption, rerunning `--stage all` picks up the last committed
checkpoint while decompressing to that source offset. Do not start
two writers at the same time, alter the ZIP or remove SQLite/lock files.
The completed Step62 and Step63 SQLite databases are never modified.

After completion, the requested handoff is **TERMINAL OUTPUT ONLY**.
Paste or attach the aggregate printed summary (which should be
reviewed under the institution's disclosure policy). No ZIP or raw
files requested at this stage.

## Private output paths

- `results/phase1/full_reconstruction_private/step68_procedure_windows_private/step68_procedure_windows_LOCAL_ONLY.sqlite`
- `results/phase1/full_reconstruction_private/step68_procedure_windows_private/step68_aggregate_LOCAL_ONLY.json`

They contain patient-linked research data or unreviewed
source-derived counts, respectively. Do NOT upload either file unless
specifically cleared by authorized institutional disclosure review.

## Decision after results

1. Test whether ED-coded imaging recovers significantly more
   otherwise-negative P=1 cases than P=0, both in absolute
   percentage points and among frozen linked-ED patients, stratified
   by year (particularly 2016-17) and F critical dates.
2. Compare strict ED with any encounter preceding by 0-2
   days and the wider 7-day window. If only the broad window
   recovers many codes, the mechanism remains uncertain and
   does not justify pooling disparate encounters.
3. Use the private exact code profile to prioritize official
   ICD-10-PCS / HCPCS / SNOMED codebook work against available
   code families. Approval of specific code mappings is a
   separate literature/coding decision; never report an
   unreviewed PCS or SNOMED match as clinically performed imaging.
4. Decide frozen primary coded-imaging outcome and sensitivity
   list before initiating disparity models. Adjusted disparity
   models must address missingness and uncontrolled HCO-level
   coding variability rather than claiming national causal effects.

# Step 64: Read-only upper bound for ED imaging-code augmentation

**Status:** Synthetic-only implementation pending local investigator test
verification. No clinical ZIP scan and no modification of Step 62/63.

## Decision question

Step 63 completed the conservative date-only, reciprocal-unique
EMER-to-IMP feasibility analysis. Before a second full scan of
the enormous Research Network procedure CSV, ask:

> Among original Step 62 indexed patients, how many who have NO
> recorded CPT14 code on their index IMP have a unique preceding ED
> encounter where new codes *could possibly* be found?

This is the **maximum possible incremental coded-imaging capture**
under the frozen Step 63 linkage, not a prediction and not evidence
of actual ED imaging.

## Data definitions

`scripts/step64_ed_capture_ceiling.py` opens the completed
Step 62 and Step 63 private SQLite databases in **read-only** mode and
joins on the exact cohort/patient. It does **not** read patient-level
ZIP rows, access a remote service, write a file, or print patient/
encounter IDs.

For each cohort and each outcome, including `ANY_CPT14` and six
separate imaging modalities:

- `baseline`: unique Step 62 indexed patients with the CPT14 outcome
  recorded on the same IMP encounter within its stay.
- `eligible_ED`: Step 63 indexed patients with a reciprocal-unique
  date-only ED link. All Step 62 indexed patients remain in the
  **original** denominator, including patients whose ED linkage is
  unassessable because encounter keys were quarantined.
- `max_new`: indexed patients with a unique ED link **and without**
  the specific inpatient outcome. Patients who already have an
  inpatient MRI, for example, cannot add a *new* MRI-positive patient
  through ED supplementation.
- `best_case_count = baseline + max_new` and
  `best_case_rate = best_case_count / original_indexed`.

No ED procedure data have been scanned by Step 64. The calculations
imagine that **every** eligible unique ED link among inpatient-negative
patients has the required code, an intentionally implausible
best-case upper bound. The actual incremental code capture must be
lower than or equal to this ceiling. The 14-code CPT set itself is
unvalidated as a complete measure of imaging delivery.

By-year and by-unvalidated-`P` aggregates are shown separately to
assess how the ED sensitivity could affect earlier coding disparities.
Cohort memberships overlap. Do not add their counts. This analysis
cannot repair unlinked imaging, other code systems, unvalidated
HCO/source identities, or undetermined `P` meaning.

## Run (authorized workstation only)

```bash
git pull --ff-only origin analysis-rebuild-phase1-audit
python -m py_compile scripts/step64_ed_capture_ceiling.py
python -m pytest -q tests/test_step64_ed_capture_ceiling.py
python -m pytest -q
```

If tests pass:

```bash
python scripts/step64_ed_capture_ceiling.py
```

Both completed private databases are expected under the existing
Git-ignored folders:

- `results/phase1/full_reconstruction_private/step62_cohort_private/`
- `results/phase1/full_reconstruction_private/step63_ed_sensitivity_private/`

The script checks the copied Step 62 snapshot, completed stage
checkpoints, frozen Step 63 link policy and index-matching
invariants before calculating rates. It prints only aggregate
figures, with no raw identifiers, but **not a disclosure-reviewed
release**; suppressing all potential secondary disclosures is outside
its scope. Share externally only after institutional authorization.

## Decision after run

Review `max_new_any14` as a percentage of the original cohort and
the `P=1` versus `P=0` ceilings, including year-to-year variation.

If the maximum is small compared with the roughly twofold differential
in Step 62 imaging-code capture, a 993-million-row ED procedure scan
is unlikely to resolve that validity concern under the current strict
linkage rule. Prioritize code-system completeness, principal-
diagnosis/encounter semantics and institutional/source interpretation.

If the upper bound is sufficiently large to plausibly change the
research conclusion, design a **separately checkpointed ED procedure
scan** using ONLY frozen unique ED links, strict CPT14 system/code
matches and dates within the ED stay, with source-row reconciliation,
no overwrite, synthetic tests, and a year/`P` comparison to Step 62.

Neither Step 63 nor Step 64 proves that an ED encounter is from
the same hospital, or that a procedure code is a performed scan.
Do not run adjusted race/sex/ethnicity disparity regression until
these concerns have been evaluated.

# Step 37: bounded encounter-linkage pilot (Research Network)

**Stage:** technical feasibility only. This stage preserves the original
young-stroke clinical imaging/disparities question as an objective, **not** as
a supported conclusion. The Research Network export has encounter IDs in
diagnoses and procedures and a separate encounter table, but linkage
integrity, inpatient type semantics and clinical imaging capture are unverified.

## Why a bounded pilot first?

The uploaded Step 36 metadata confirmed the following ZIP manifest counts:

| Table | Source manifest rows |
| --- | ---: |
| encounter.csv | 557,665,953 |
| diagnosis.csv | 1,376,280,235 |
| procedure.csv | 993,025,015 |

A full scan of these tables is expensive and unnecessary for a first check.
Instead, the new script reads **at most 50,000 data rows from the beginning
of each of those three tables**, no more than 150,000 event rows total by
default. The three prefixes are **not random or representative** and may
be sorted differently, so overlap across them cannot estimate true join
success or clinical encounter capture.

## Run locally from the cloned repository

First pull draft PR #1, then run:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step37_research_encounter_pilot.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip"
```

The script reads the existing
`results/phase1/step36_research_metadata_preflight.json` to
check that the ZIP table signatures match the passed Step 36 preflight.
It uses only the standard Python library.

Optional `--max-rows-per-table N` changes the bound up to
200,000 rows per table. **Do not increase it before reviewing the initial
pilot**, since these are nonrandom file prefixes and scanning more rows
does not by itself create a representative sample.

## Generated files: ONLY in the clone

```text
Young-Stroke-Disparity/
  results/phase1/
    step37_research_encounter_pilot.json
    step37_research_encounter_pilot_review.zip
```

Both are gitignored. The script refuses output paths outside this
repository's `results/phase1/` and does not copy or extract the
original ZIP. Review ZIP contains **only** the aggregate JSON report. The
script writes no patient ID, encounter ID, source ID, procedure/diagnosis
date, or individual clinical row to disk; IDs exist in temporary in-memory
prefix samples only. Generated files are private (0600). Directory
permissions on existing folders are preserved.

The script reports:

- Encounter ID, patient ID and (when present) source ID completeness in each
  bounded prefix
- Duplicate encounter IDs and conflicting patient/source IDs in the
  encounter prefix
- Coarse date bucket counts and restricted encounter type *label candidates*
- Presence of principal ICD-10-CM I63 and listed CPT imaging codes in the
  corresponding prefixes, without clinical interpretation
- Diagnosis/procedure prefix encounter ID overlaps with the encounter prefix,
  plus patient/source ID consistency **only among observed prefix matches**
- Explicit `ready_for_clinical_disparities_models: false` and other
  inferential stop flags

Small counts 1–10 are displayed as `suppressed_1_to_10`, but overlapping
margins can still disclose sensitive numbers by subtraction. **No report
should be made public or committed**; institutional cross-table disclosure
and data-use review remains necessary before sharing even this aggregate
review ZIP.

## Interpretation and next decision

1. **Good sample-level ID consistency** supports designing one carefully
   planned *full source* reconstruction, **not** claiming hospital admissions
   or imaging receipt.
2. **Low or zero overlap** is inconclusive, because the three prefixes may
   contain different patients and encounters. It must NOT be used as a
   stop signal or a population-wide join estimate.
3. **Unknown encounter type labels** require validating the Research Network
   terminology and inpatient semantics before hospital-based analysis.
4. **Very low apparent CPT imaging code frequency** in these prefixes is
   not proof of incomplete capture; it needs a comprehensive coding-system
   review and cohort-specific, encounter-linked denominators.
5. A full analysis is authorized only after deciding the event grain,
   source_id/HCO key scope, inpatient criteria, 2018–2019 cohort definition,
   imaging codebook, race/ethnicity missingness and approved private storage.
   Avoid reading all billion-row files more than once when feasible.

If permitted by the data steward, share only
`results/phase1/step37_research_encounter_pilot_review.zip`
through the conversation after reviewing it locally. Do not share or commit
the source ZIP, individual records, derived row-level cohorts or any
patient/encounter/source identifiers.

The public repository still contains historical patient-level files in
Git history. Institutional privacy/data-owner review remains a separate
precondition to external research disclosure and public release.

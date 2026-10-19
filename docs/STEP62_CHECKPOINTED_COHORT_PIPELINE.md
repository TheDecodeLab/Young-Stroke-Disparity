# Step 62: Checkpointed provisional young-stroke cohort (local only)

**Status:** New, independently implemented Python 3.9 pipeline. It has not
yet been run on real TriNetX data. It is distinct from the disabled old
Step45. Run synthetic tests before any local clinical-data stage.

The source-wide Step59 `DATEFIX_V2` and reconciled Step60 aggregates have
already been completed: encounter 557,665,953 rows, diagnosis 1,376,280,235
rows, procedure 993,025,015 rows. All three had zero invalid dates after
fixing the source's `YYYYMMDD` format. Those source-row totals do **not**
represent young-stroke cases, imaging exams or unique people.

## Scientific contract

- **Source:** TriNetX Research Network, not the distinct 2018–2019 Diamond
  dataset. Provisional index IMP admission starts **2016-01-01 to
  2024-12-31**. The unusually low 2025 counts across three tables make
  that year suspect; this does **not** formally approve 2024 as the cutoff.
- **Diagnosis:** Strict `ICD-10-CM` system with `I63` parent or dotted
  `I63.*` pattern, treated as **candidates only**. Do not treat undocumented
  dotless `I639`, retinal `H34.1` or ICD-9 as eligible cerebral stroke.
  Keep whether any qualifying diagnosis bears the unvalidated `P` label;
  **P is not required** in this provisional broad case-ascertainment pass.
- **Index:** Match diagnosis to the **same patient + encounter** and
  date within an `IMP` start/end interval. A missing/reversed encounter
  end date is not called imaging-negative; it is excluded as unassessable
  from this provisional index. Competing earliest same-day qualifying
  admissions are held, not selected arbitrarily.
- **Co-primary cohorts, evaluated independently:** All ages 18–50; and
  sex-specific men 18–52/women 18–54. Year of birth alone bounds age to
  `index_year - birth_year - 1` through `index_year - birth_year`.
  Require **definite** inclusion throughout that interval. Boundary
  uncertainty and missing/unsupported sex are omitted, with grouped
  candidate-admission audit counts; preserve missing/unknown in later
  sensitivity work. Cohort memberships can overlap; never add totals.
- **Index rule:** Earliest definitely eligible, same-encounter diagnosed
  IMP admission per patient **within each cohort**. This is provisional
  because an earlier age-ambiguous stay may exist, and procedure/encounter
  meaning and HCO coverage remain uncertain.
- **Primary imaging-code outcome:** Exactly 14 reference CPT codes, mapped
  to MRI brain, CTA head/neck, MRA head/neck and CT head, on **the same
  patient+IMP encounter**, with the procedure's date between the index
  start and end inclusive. It represents **documented code capture**,
  not a verified performed scan. No CPT perfusion or retinal case is
  silently added, and a different ED encounter is **never** counted.
- **ED sensitivity B and site/HCO adjustment:** Not run in this version.
  Those need separate date-only uniqueness QA and source semantics; no
  invented hospital link. No sex/race/ethnicity disparity model is run.

## Data processing and restart policy

Script: [`scripts/step62_checkpointed_cohort.py`](../scripts/step62_checkpointed_cohort.py).

Reads one ZIP table **per invocation**, using CSV streaming plus a
disk-backed SQLite database. The source CSV is **not extracted** and raw
clinical rows never enter GitHub. A batch of up to 20,000 source rows is
loaded into memory at a time; the database checkpoint and all inserts for
that batch commit atomically.

If an interruption occurs, rerun the **same stage** to resume from the
last committed source-row count, skipping earlier ZIP CSV rows. Skipping
still decompresses/reads the earlier part; this is **not random-access**
ZIP seeking and can be time-consuming, but it avoids duplicating already
committed state. A different ZIP, Step36 preflight or year policy is
rejected via a frozen fingerprint (ZIP table name, uncompressed bytes and
CRC plus preflight SHA). Competing patient demographics or same-key
qualifying encounters with inconsistent dates fail rather than silently
coalescing. The stage also checks the Step36 manifest's complete row
count before marking a stage done.

The SQLite database, its indices and the final aggregate report contain
sensitive de-identified encounter/person linkage information. They stay
within Git-ignored, owner-only (0700) private directory, with database
and report mode 0600:

`results/phase1/full_reconstruction_private/step62_cohort_private/`

Do not put the SQLite file, private reports, or clinical ZIP on GitHub.
A report exported externally needs a separate review of its aggregate
cell sizes; no source IDs appear in the report.

## Execution order (run **tests first**, then one source stage at a time)

From the GitHub draft branch:

```bash
git pull --ff-only origin analysis-rebuild-phase1-audit
python -m py_compile scripts/step62_checkpointed_cohort.py
python -m pytest -q tests/test_step62_checkpointed_cohort.py
python -m pytest -q
```

Do not begin a real scan if any test fails. Then run only **diagnosis**,
and inspect its completion summary before proceeding:

```bash
python scripts/step62_checkpointed_cohort.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip" \
  --stage diagnosis \
  --acknowledge I_CONFIRM_EXISTING_PROTOCOL_PERMITS_LOCAL_COHORT_RECONSTRUCTION
```

Subsequent local stages use the **same command** with the stage value
replaced in order:

```text
diagnosis -> encounter -> patient -> index -> procedure -> report
```

`index` and `report` operate on local SQLite (they only read ZIP
central-directory metadata for the source fingerprint). The diagnosis
stage must read the entire 1.376-billion-row diagnosis table on the
workstation, but stores only strict `I63` candidates. Encounter,
patient and procedure stages also require complete local source scans;
Step59's aggregate summaries **cannot replace encounter-level linkages**.
Each source stage commits **partial private SQLite state at checkpoints**, but is marked complete only after its source-row reconciliation. Later stages are blocked until the preceding stage completes.

For the final **aggregate-only** report, after all stages complete:

`results/phase1/full_reconstruction_private/step62_cohort_private/aggregate_review_LOCAL_ONLY.json`

This report lists provisional index counts by cohort/year, `P`-label
counts, age boundary audit counts, and CPT14 code-capture counts. It does
not validate the phenotype, actual imaging delivery, participation by
site, unknown-sex case treatment, or health disparities. A documented
methods review and internal validation still precede inferential results.

## Synthetic-only tests and CI

[`tests/test_step62_checkpointed_cohort.py`](../tests/test_step62_checkpointed_cohort.py)
constructs fabricated CSV source ZIPs, Step36 metadata and rows to test:
date parsing, `I63` screening, uncertain YOB eligibility, distinct age
cohorts, competing same-day index stays, strict same-IMP imaging windows,
ED exclusion, SQLite permissions, checkpoint resume, frozen provenance,
and stage ordering. GitHub Actions
[`step62_synthetic.yml`](../.github/workflows/step62_synthetic.yml)
runs these tests with Python 3.9, no connection to clinical data.

**Open scientific tasks:** Confirm `IMP` and `P` semantics; determine
performed-versus-ordered codes; confirm site/HCO participation and end-year;
quantify diagnosis/encounter linkage and missing age by stratum; develop
verified non-CPT imaging mapping and uniquely linked ED sensitivity;
then design adjusted disparity models after outcome validation.

**Never use the old Step45 clinical scanner.** PR #1 stays draft pending
separate historic-Git governance review.

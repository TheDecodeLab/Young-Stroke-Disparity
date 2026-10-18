# Step 45: Guarded full-cohort reconstruction (NOT EXECUTED)

**Implementation status:** executable, disk-backed staged pipeline and synthetic tests committed to draft PR #1. **No full Research Network clinical scan has been run or authorized by this commit.** Default invocation is *read-only metadata planning*, and the scan is blocked unless institutional and clinical approvals are recorded locally.

## TWO co-primary definitions (explicit study decision)

The manuscript will have **two parallel, overlapping primary populations**, not a primary plus sensitivity analysis:

| Cohort | Eligibility |
|---|---|
| `uniform_18_50` | ages 18 through 50 for everyone |
| `original_sex_specific_18_52_54` | males 18–52; females 18–54 |

The source provides **year of birth**, not verified date of birth. Exact age on admission is not known at boundary years. Conservatively require the **entire possible age interval** to meet the relevant rule. Report boundary-uncertain patients separately as data-quality exclusions. The uniform cohort may include people with unknown sex; the historical sex-specific definition cannot classify those people until a policy is signed off. The same patient may appear in both cohorts; do not assume independent samples or pool their denominators.

## Workflow and derived-data grain

The implementation lives in `scripts/step45_full_cohort_reconstruction.py`; it uses only the Python standard library (`zipfile`, `csv`, `sqlite3`). The source ZIP is **read-only** at the operator's existing external path; it is not extracted. Clinical rows are never saved to GitHub, and logs/export files never include patient/encounter IDs.

Six **explicit** stages, each separately requested after approvals, with a private SQLite database and a completion marker only after the entire source member is exhausted:

1. **diagnosis** – ONE complete `diagnosis.csv` pass. Select principal ICD-10-CM I63 diagnoses occurring during 2018–19. Requires the clinical reviewer to certify that the observed principal-diagnosis flag `P` means principal. Store only selected candidate patient/encounter/date triples in the private database. Imaging is never used for eligibility.
2. **encounter** – ONE complete `encounter.csv` pass. Verify candidate patient+encounter keys and provisional `IMP` inpatient semantics (must be signed off), date proximity and conflicting repeated encounters. Uses a fixed 64 MiB Bloom filter only to reduce database probes; an indexed patient+encounter lookup remains the final truth.
3. **patient** – ONE pass over `patient.csv` matching admissions for sex, race, ethnicity and year of birth. Duplicate/conflicting demographic rows abort.
4. **index** – local database-only processing. Select earliest **definitely eligible** admission per patient independently under *both* co-primary rules. Exclude uncertain age boundaries. Do not use imaging in index selection.
5. **procedure** – ONE complete `procedure.csv` pass. Look up only exact pairs from a separately **reviewed frozen performed-procedure codebook**. Match patient AND encounter, then check timing. The primary outcome is **recorded performed-code during an encounter with known start AND end dates**. An explicitly labeled same-encounter ±7-day flag is retained for sensitivity. Missing end dates do not count as documented within-stay imaging.
6. **report** – private aggregate descriptive counts under both age definitions, stratified by sex and race separately. No clinical models, adjusted associations, publication figures, or externally shareable outputs are automatically produced.

Stages can restart **at table boundaries**, not at an arbitrary clinical row offset. A failed stage has no completed marker; partial stage records are cleared when that stage is intentionally reattempted. Previous completed table scans are skipped if unchanged. The source table sizes/ZIP CRCs, Step 36 metadata, approvals, age policy and frozen codebook hashes are locked to the run, preventing changes between stages. A modified approval/codebook requires a separately governed new private run; do not reset data blindly.

Only candidates and final index flags are held in private disk-backed SQLite, not all billion-row source records in memory. A fixed prefilter and batch commits reduce unnecessary work. The expected resource need is substantial: **budget at least 16 GiB of free encrypted local storage** for execution, plus potentially many hours/days for billions of CSV rows. This is an estimated minimum, not an upper bound. The code intentionally makes no guarantee of running within a particular time or disk budget.

## Path rule (user-requested)

**All generated files, including templates, the private SQLite database, journal/temporary files, and final private aggregates, are inside the cloned repository's Git-ignored `results/phase1/`.** Specifically:

```text
Young-Stroke-Disparity/
  results/phase1/
    step36_research_metadata_preflight.json
    full_reconstruction_private/  [0700 permissions required]
      approvals_LOCAL_ONLY.json
      imaging_codebook_APPROVED_LOCAL_ONLY.csv
      reconstruction_STAGE_PRIVATE.sqlite
      co_primary_cohort_aggregates_LOCAL_ONLY.json
```

The original Research Network ZIP **remains external** where it already is. No input ZIP is copied inside the clone. The private stage directory must be chmod 700, and individual generated files are chmod 600. It must be on institutional-approved **encrypted** storage; the code cannot independently verify disk encryption and requires an explicit authorization field.

**Do not commit, upload, share or synchronize any SQLite database, codebook, approval records, or derived row-level stages.** Aggregate JSON is *also private*, with small-cell and complement suppression, but complementary and cross-table disclosure review is still required before release. No automatic ZIP of outputs is created.

## Commands now safe to run: metadata only

From the cloned repository:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step45_full_cohort_reconstruction.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip"
```

With **no `--stage`**, the script performs only a Step36 ZIP metadata/signature check and prints the six-stage plan. It does NOT read clinical rows, open the SQLite database, or start extraction.

To create **unapproved** private templates, also safe (does not read the clinical ZIP):

```bash
python scripts/step45_full_cohort_reconstruction.py --init-templates
```

This command refuses to overwrite existing approval/codebook templates. All approval booleans are deliberately `false`; the imaging codebook contains only a header.

## Future execution, NOT for running now

After clinical/data-steward review and institutional approval only, edit the two private files. The approval JSON must document data-use permission, encryption, principal `P` semantics, `IMP` admission meaning, encounter key scope, **both** age definitions and DOB-boundary policy, a reviewed imaging codebook, and small-cell/privacy release restrictions, including reviewer name/date and institutional reference. This is an explicit attestation, not approval granted by the software. The codebook CSV columns are `code_system,code,category,record_meaning,reviewer,review_date`; only reviewed `performed` codes in `MRI_BRAIN,CTA_HEAD,CTA_NECK,MRA_HEAD,MRA_NECK,CT_HEAD` are accepted.

Execution requires an explicit `--stage`, `--execute-full-scan`, and the exact typed `--confirm I_ACKNOWLEDGE_FULL_TRINETX_CLINICAL_SCAN`. Each call checks the approvals, codebook, disk space and source. **Do not issue those flags until sign-off.** This prevents a casual plan/test command from starting a full scan. If the source or approvals change mid-run, a different reviewed private staging run is required.

## Limitations and next scientific checks

A recorded code does not always prove imaging completion; source semantics require validation. This implementation creates the **descriptive technical starting point**, not an analysis-ready disparities paper. Before making scientific claims, also examine severity/comorbidity confounding, site coverage, coding source differences, race missingness, YOB-related selection, between-definition overlap, inpatient/transfer semantics, and possible undercapture of inpatient imaging due to missing end dates. The report is explicitly local and not institutionally disclosure-cleared.

The public repository's legacy Git history includes unresolved derived TriNetX records. PR #1 must remain **draft and unmerged** until the data steward/owner resolves that separate governance issue.

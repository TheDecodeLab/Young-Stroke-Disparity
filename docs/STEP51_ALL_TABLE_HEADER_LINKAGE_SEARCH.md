# Step 51: All-table CSV header-only linkage field search

**Purpose.** Step50 reported **no explicit hospital/HCO or parent-episode column in the `encounter.csv` headers**; `source_id` still has unverified meaning. Step51 checks whether a separate Research Network CSV has relevant hospital, care-site, parent-encounter, or episode column names.

**Scope is tightly limited:** the script opens the *existing local ZIP read-only*, inspects its central directory, and consumes **only the CSV header line** in each CSV member. It does **not** iterate, parse, count, link or export any clinical data rows, and does not decompress/extract whole source tables. The ZIP library can internally buffer bytes during header reads, so the accurate guarantee is **zero clinical records processed**, not zero bytes buffered beyond a header line. No patient IDs, encounter IDs or row values appear in output. Even a matching column name is NOT proof of HCO/site validity.

## Run one chained command on the study workstation

```bash
git pull origin analysis-rebuild-phase1-audit

python -m pytest -q && \
python scripts/step51_all_csv_header_linkage_search.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip"
```

Unlike Step50, **this does open the original ZIP**, but only for file metadata and first-line CSV headers. It does not perform a full clinical row scan or modify the archive. Run only within the existing institutionally permitted research environment.

The script compares the ZIP's four core-table filenames, uncompressed sizes and column headers with the locally saved `results/phase1/step36_research_metadata_preflight.json`. Duplicate table basenames, a changed ZIP core signature, or invalid Step36 provenance abort.

The single output is a mode-0600 private JSON under the existing mode-0700 private directory:

`results/phase1/full_reconstruction_private/site_linkage_review/step51_all_csv_header_linkage_hints_LOCAL_ONLY.json`

If the report exists, the script **refuses to overwrite** it.

## Interpretation

- **Possible `hco_id`, `facility_id`, `parent_encounter_id`, `episode_id` (etc.) in a separate table:** potential lead only. We still require steward verification of meaning, scope, missingness, uniqueness and whether it can link ED and inpatient visits.
- **Only `source_id`:** do not reinterpret this as a valid HCO identifier; earlier source/encounter table `source_id` differences have unresolved semantics.
- **No plausible field names anywhere:** the exported headers alone cannot establish same-hospital or parent-episode linkage. Next choices are (a) request a data dictionary/parent-episode/HCO mapping from the TriNetX administrator, or (b) preregister an explicitly **provisional date-only sensitivity** based on same patient, ED end to IP start calendar gap 0/1 days, conservative ambiguous-match handling and site-unknown limitations. This latter method must NOT be described as verified same-hospital transfer.
- **Clinical-source row validation:** requires separate institutional authorization for real-data analysis; the Step45 source-wide clinical pipeline remains disabled.

The study retains **both overlapping co-primary age cohorts**, ED-before-IP imaging as a relevant outcome, imaging-codebook clinical review, and the broad/cerebral-only stroke-phenotype sensitivity strategy. Step51 does not grant approval for any of these data-processing stages.

**Data protection:** keep this JSON under the cloned repository's ignored `results/phase1/`. Even ZIP member names and header names are restricted metadata until data-owner review. Share the terminal's summarized field-name clues only if permitted. Do not publish raw metadata, patient records or clinical codebook files to GitHub. Draft PR #1 remains unmerged pending historical repository governance review.

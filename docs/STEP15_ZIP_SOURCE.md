# Step 15: inventory original TriNetX ZIP without extraction

## Location supplied by study team

From the cloned repository root, the existing approved local export is at:

`../../../../datasets/TriNetX/dataset_64b01b62c6dca15375ae9828_stroke.zip`

This ZIP may contain the source diagnosis, procedure, demographic and
encounter tables referenced in the historical notebook. The ZIP's internal
contents have **not yet been examined**. The original standalone Parquet
exports were deleted to save storage space.

## Run from the repository root

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step15_zip_inventory.py \
  --zip ../../../../datasets/TriNetX/dataset_64b01b62c6dca15375ae9828_stroke.zip
```

The script does NOT extract the archive. It examines the ZIP directory
and reads at most the first line of each CSV/TSV member, stopping after
64 KiB per header and 2,000 members by default. It reports archive
member names, column names, possible table roles, encounter-ID column
candidates, sizes, and data formats.

Default output: `results/phase1/zip_source_inventory.json`, ignored by Git.
Review filename and schema metadata locally before sharing. Do not
upload the ZIP, original TriNetX records, patient-level Parquet data,
or rows from the CSV files.

Possible outcomes:

1. **Original CSV diagnosis/procedure/demographic tables present.**
   Use their actual ZIP member names to develop a streaming,
   chunked source reader using `zipfile.ZipFile.open` and
   `pandas.read_csv(chunksize=...)`. Validate original index diagnoses,
   CT eligibility, encounter linkage, and non-CT imaging outcomes.
   Do NOT select on imaging before index cohort construction.
2. **Parquet or nested ZIP members present.** Step 15 only lists
   these extensions. We need a format-specific plan before reading
   them, rather than unpacking unknown or large files.
3. **No suitable tables.** Confirm whether the archive is a
   TriNetX clinical export versus a cohort summary or metadata.

## Scientific rules for the next development phase

- Reconstruct index principal ischemic-stroke diagnosis/admission
  BEFORE checking for CT, MRI, CTA, MRA.
- Confirm the first eligible event and its relation to procedure
  timestamps using encounter identifiers when available. A
  patient-only join is not equivalent to an encounter join.
- If the study restricts to CT-imaged stroke cases, apply that
  CT condition at the index-event level and retain **CT-only**
  records with zero additional imaging.
- Independently verify the ischemic-stroke diagnosis codebook,
  exclusions, imaging code definitions and time window.
- Clinical covariates should come from validated pre-index
  records, rather than the sex-containing CHA2DS2-VASc score.
- All previous regression and utilization estimates are on
  an outcome-selected cohort and not publication-ready.

## IHME-GBD is not needed for this repair

The separate IHME-GBD stroke files may support ecological context or
a different research question, but cannot identify individual
imaging utilization, stroke index admissions, or CT-only patients
in TriNetX. Do not merge those unrelated data sources into the
primary cohort construction.

## Privacy, storage and reproducibility

Keep the original ZIP inside approved institutional storage.
No patient-level data are copied to the public GitHub repo.
Streaming from ZIP can avoid large disk extraction, but processing
may still require RAM and/or small locally secured intermediate
files for event linkage. Design this after actual member schemas
and table sizes are known. Verify institutional and TriNetX sharing
permissions for earlier publicly tracked patient-level files.

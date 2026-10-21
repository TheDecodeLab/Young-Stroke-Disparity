# Step 13 status: original sources not located

The collaborator's Step 13 `source_readiness.json` reports
`not_found` for all three filenames: `diagnoses.parquet`,
`procedures.parquet` and `demographics.parquet`.
There are **no schema, event, diagnosis-code or encounter-linkage
findings** in that report. Those names were example placeholders
in our instructions, not verified paths on the study workstation.

## Step 14: find candidate original exports

Run the metadata-only discovery command from the repo root:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step14_discover_sources.py --root .. --max-depth 4
```

This searches only within the explicitly selected parent directory
and reports likely original source tables based on CSV headers and
Parquet schemas. If it finds nothing, repeat in another **authorized**
local data directory that may contain the original TriNetX exports:

```bash
python scripts/step14_discover_sources.py \
  --root ~/works --max-depth 6 \
  --output results/phase1/source_candidates_works.json
```

The utility reads **column names and Parquet metadata only**. It
does not read patient rows, index dates, identifiers or location values.
It avoids hidden and generated directories and does not follow
symlinks. It will stop after 2,000 candidate CSV/Parquet files unless
the limit is explicitly raised.

The local outputs are ignored by Git:
- `results/phase1/source_candidates.json`
- `results/phase1/source_candidates_works.json` if the second run is needed

The JSON contains *relative filenames*, schema column names and
Parquet row counts. Review names for sensitive information before
sending the report. Filesystem locations should not be committed to
public GitHub as absolute institutional paths.

A schema match is **not proof** of an original unfiltered source
export. Also, this scanner may miss unusual formats or very deeply
partitioned Parquet datasets.

## If no candidate exports are present

The saved `df_merged_age.parquet` is an already joined,
imaging-conditioned intermediate. It cannot alone recover qualifying
stroke admissions that never linked to an imaging procedure and it
does not preserve unambiguous original encounter linkage.

The correct next step is to retrieve or re-export the authorized
source diagnoses, procedures, demographics and encounters from
the original study data source. Do not fit revised models on the
imaging-selected intermediates.

## After finding files

Use the actual paths with Step 13, for example:

```bash
python scripts/step13_source_inventory.py \
  --diagnoses /actual/approved/path/diagnosis_data.parquet \
  --procedures /actual/approved/path/procedure_data.parquet \
  --demographics /actual/approved/path/patient_data.parquet
```

The input paths are examples; substitute the local candidate paths
only after checking that they are the appropriate original exports.
We must establish principal ischemic-stroke index encounters
independently of MRI/CTA/MRA receipt and verify CT eligibility,
imaging windows, and data governance before analysis.

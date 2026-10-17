# Step 36: Research Network stroke export feasibility (metadata only)

**Status: preflight, not a clinical result.** The investigator wants to retain the original neuroimaging disparities research question where the available data permit it. The Research Network stroke export may include `encounter_id` in diagnoses and procedures plus a separate `encounter.csv`. This requires verification using the specific original local ZIP. An encounter ID column alone does **not** establish valid hospital admissions, encounter-linked imaging, or population representativeness.

The previous Diamond analyses (Steps 25–35) remain a separate administrative-record sensitivity audit. The Research Network export is a candidate **new primary source**, not a replacement for NIS validation or a clinical truth standard. Do not transfer count or rate estimates across exports.

## What the preflight reads

`scripts/step36_research_zip_preflight.py` inspects the ZIP central directory, one CSV header per selected table, and up to 2 MB from each of three **aggregate export metadata files** (`manifest.csv`, `dataset_details.csv`, `cohort_details.csv`). It does not read patient rows, extract ZIP members, create patient-level files, or run large table scans. Reports include table names, headers, uncompressed table sizes, manifest counts, coarse export/cohort metadata, and warnings. They contain no source patient IDs or patient records. The operator must still review sharing permissions and the metadata before upload.

No GitHub Actions job accesses local data. No raw ZIP, private SQLite, individual patient identifiers, or stratified clinical counts should be committed to this PUBLIC repository or pasted in a PR.

## On the study workstation

From the repository root, after pulling the draft branch:

```bash
python -m pytest -q tests/test_step36_research_zip_preflight.py
python scripts/step36_research_zip_preflight.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip"
```

The output JSON and ZIP are created by default under the cloned repository `results/phase1/`, which is Git-ignored. Outputs are owner-readable/writable (0600); existing parent directory permissions are unchanged. The ZIP contains exactly one file: `step36_research_metadata_preflight.json`. Any explicit output path outside the repository `results/phase1/` is rejected. The input source ZIP remains in its original location and is never copied into the repository. No third-party Python packages are needed for the script.

Review the metadata ZIP locally before sharing. If institutional rules permit it, upload **only** the review ZIP and the test summary. Do **not** include the original dataset ZIP, private SQLite, row-level subsets, ZIP members beyond the metadata JSON, or other source files.

## Go/no-go stages

1. **Step 36 structural readiness:** presence of `patient.csv`, `encounter.csv`, `diagnosis.csv`, and `procedure.csv`; headers show shared IDs. Check export cohort provenance, row counts, and warnings. Schema readiness is not linkage validation.
2. **Step 37 private encounter audit:** locally quantify nonmissing encounter IDs, patient/encounter join integrity, inpatient encounter-type definitions, diagnosis-to-encounter linkage, imaging-code crosswalk and relative dates, and the 2018–2019 eligible population. Prepare and review a separate data-use-compliant aggregate report; do not scan full clinical tables without an approved efficient plan.
3. **Clinical publication decision:** proceed with adjusted sex/race imaging analyses only if the hospital-based population, imaging ascertainment, covariates, missingness, and governance support the intended estimand. Otherwise use strictly qualified recorded-code analysis or a methods paper.

The existing public Git history contains unresolved patient-level TriNetX data/disclosure issues. Seek institutional data steward and privacy/compliance guidance before public distribution, history rewriting, or merging PR #1.
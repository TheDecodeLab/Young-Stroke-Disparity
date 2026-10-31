# Steps 85-86: Remaining scientific reporting gates

**Status (2026-10-30):** Source code and synthetic tests added to the existing analysis-rebuild-phase1-audit branch. **The investigator's frozen Step69 aggregate has not been run here; no real stratum support or figure-regeneration result is claimed.** All private clinical-source outputs remain on the authorized workstation. This public document contains no cohort-derived cell counts.

## Step85: standardization-support sensitivity from frozen indexes only

`scripts/step85_p_standardization_support.py` reads the already frozen Step62, Step63 and Step68 checkpoint SQLite databases in read-only mode. It uses the tested Step69 aggregation of existing indexed-patient code-presence flags. It does **not** reopen the original TriNetX ZIP or repeat the very large procedure scan.

The analysis separately examines each year × encounter-key ambiguity × P recording stratum. It confirms original full-cohort common-weight standardization against Step70, then evaluates:

- Whether both P-group denominators meet prespecified thresholds of 11, 30, 50 and 100.
- The retained-population coverage and descriptive effect when strata below each threshold are excluded. This changes the target population, so none of these comparisons is a drop-in replacement for the original estimate.
- A three-calendar-year-era pooling sensitivity, retaining the ambiguity distinction.
- Leave-one-year-out estimates. Changing the represented years also changes the target population.
- All stages remain descriptive. No HCO clustering or clinical-care validity can be inferred.

**Output:** an exclusive, owner-readable `results/phase1/full_reconstruction_private/step85_standardization_private/support_sensitivity_LOCAL_ONLY.json`. Only yes/no thresholds, sign consistency and coverage status are printed to the terminal. Do not commit or externally distribute the private output.

Supported workstation command, when the investigator wishes to close this restricted evidence gate:

```bash
git pull --ff-only origin analysis-rebuild-phase1-audit
python -m pytest -q tests/test_step85_p_standardization_support.py tests/test_step86_figure1_from_frozen.py
python scripts/step85_p_standardization_support.py --acknowledge I_CONFIRM_INTERNAL_REVIEW_ONLY
```

The v1.9 main manuscript **does not present** the standardized P differences as primary results. It preserves the original observational crude P contrasts in Table 1 and retains the exploratory standardized values in Supplementary Table S3. This claim-narrowing is justified without pretending the sensitivity diagnostic has already run.

## Step86: reproduce manuscript Figure 1 from frozen Step68

`scripts/step86_figure1_from_frozen.py` reconstructs the four published modality panels from Step68 `MODALITY_P` counts: inpatient code present and newly code-positive on another same-day encounter. The script derives both P denominators from frozen data at runtime and checks they sum to the primary cohort. It creates the plotted Figure 1 **without a redundant internal title**, with identical group and modality ordering to the v1.8/v1.9 manuscript. The program can check rounded percentages against Supplementary Table S4 in a local DOCX, if supplied.

```bash
python scripts/step86_figure1_from_frozen.py \
  --supplement "/private/path/Young_Stroke_Supplement_v1.9_clean.docx" \
  --acknowledge I_CONFIRM_INTERNAL_REVIEW_ONLY
```

By default the plot stays under a gitignored restricted results directory and refuses to overwrite an existing figure. If the live output disagrees with S4, investigate the frozen-source provenance and **do not replace** the manuscript figure by eye.

The v1.9 DOCX retains the v1.8 scientifically derived figure while its explicit source-backed repository regeneration awaits the authorized run. No figure was created from fabricated clinical data.

## Annual coding source provenance: what is and is not verified

- CMS provides year-specific **Physician Fee Schedule relative value files** covering every index year in this study (2016-2024): https://www.cms.gov/medicare/payment/fee-schedules/physician/pfs-relative-value-files
- AMA publishes annual CPT Professional Edition coding references, including detailed official descriptors and guidelines: https://www.ama-assn.org/practice-management/cpt/cpt-code-set-basics-and-resources
- AMA controls copyright and licensing for CPT codes and descriptors. A CMS PFS file is not a substitute for licensing official AMA codebook descriptions: https://www.cms.gov/license/ama

**Evidence status:** the analysis-defined CPT14 codes are frozen in `scripts/step62_checkpointed_cohort.py` and disclosed as short research labels in Supplementary Table S1. The official archive's availability is verified. The complete 14 × 9 annual descriptor/status audit, annual coding-context equivalence and independent validation of completed imaging **have not been completed**. Do not claim otherwise. Annual codebook review can be performed against approved licensed sources without a clinical-data rescan. Avoid copying full copyrighted descriptors into public repository files.

## Word revision and remaining author checks

The author-facing v1.9 Word files retain the previously verified empirical cohort and main outcomes, live Zotero fields, and tracked local prose changes relative to v1.8. The main Table 1 standardized column was **structurally removed** and its values remain fully available in Supplementary Table S3. This physical table-column removal is documented here separately from Word's granular tracked text changes.

Prior to journal submission, confirm the study-specific ethics/protocol determination and the approved application's actual dissemination terms, funding, conflicts, contributions, and data/code availability statements. Repair the Zotero library item's publication-date metadata for reference 9, then refresh the live Word bibliography. No duplicate data-access application or default CTSI contact is requested. Final target journal and STROBE/RECORD checklists remain pending.

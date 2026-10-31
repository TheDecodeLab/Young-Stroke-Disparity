# Step 50: Site and parent-episode identifier preflight (metadata-only)

**Status: implementation added, not yet run against the local Step36 report.** It uses the **existing Step36 CSV headers**, not the Research Network ZIP or any clinical rows. It cannot determine whether an identifier is a valid hospital, HCO, or ED→IP episode key.

## Why this matters

Step49 now has a synthetic-tested provisional ED→inpatient date rule using the **ED end date** and **inpatient start date**. An unverified `source_id` is not proof of hospital identity or an episode. We need a reliable key or a documented institutional policy before patient-level transfer reconstruction.

The Step36 structural preflight already recorded the header names for encounter, patient, diagnosis and procedure tables. Step50 reuses those same local metadata without reopening the source ZIP. It distinguishes column names that might represent HCO/site/parent-visit keys from generic source identifiers. Even suggestive names like `hco_id`, `facility_id`, or `parent_encounter_id` remain **UNVERIFIED**.

## Execute this safe one-time bundle

From the cloned branch on the study workstation:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q && python scripts/step50_site_linkage_metadata_check.py
```

Outputs are created only under Git-ignored `results/phase1/full_reconstruction_private/site_linkage_review/`:

- `step50_site_linkage_metadata_LOCAL_ONLY.json`: table field-name hints and explicit `actual_hco_id_verified: false`, `true_ED_IP_episode_linkage_verified: false`, `clinical_rows_read: 0`.
- `site_linkage_steward_review_LOCAL_ONLY.json`: an **UNSIGNED/BLANK** local worksheet for site/episode key definitions, entity scope, source-ID semantics, ED/IMP code meanings, and confirmed transfer policy. Its boolean fields remain false.

The script refuses to overwrite files that might contain review annotations. Output files are owner-only (0600), inside an owner-only (0700) directory. No clinical source is read; no patient or encounter identifiers are captured. Review any output for governance requirements before sharing externally.

If the preflight JSON does not exist locally, do **not** create fake metadata or set approvals. Use the Step36 metadata-only command with the real source ZIP path only after verifying data-steward authorization, or provide the previous Step36 safe status report. The original ZIP stays outside the repository and read-only.

## Interpretation

- Finding a column called `hco_id` is **not validation**: we do not know the value's scope, missingness, longitudinal stability, or whether it is harmonized across sites and tables.
- If only `source_id` is present, Step50 does **not** declare a hospital mapping. The source IDs were previously observed differing across tables.
- If no plausible same-hospital or parent-episode column is present, that is **a structural limitation of these four headers**, not proof that reliable mapping is impossible; other tables or export documentation may provide one.
- Date-only proximity (0, 0–1 or 0–2 calendar days) creates **candidate** ED→IMP links, never verified transfers. Multiple possible candidates, overlapping stays, cross-HCO transfers, and missing dates remain ambiguous.
- The final linkage rule may need a protocol deviation: an authorized audit of a site key, a reviewed probabilistic candidate sensitivity analysis, or an inpatient-only sensitivity. **Do not silently equate date-adjacent episodes with same-hospital admissions.**

**No full data scan, clinical-code approval, manuscript disparity inference, or external reporting is authorized by this step.** Step45 remains hard-blocked from real source execution. Draft PR #1 remains unmerged pending the earlier restricted-data governance review.

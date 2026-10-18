# Steps 46–47: Chained clinical imaging-codebook review and validation

> **Current authority:** For Research Network analysis, follow the [active 2026 study plan](ACTIVE_RESEARCH_NETWORK_STUDY_PLAN.md) and [canonical code-to-reference register](references/IMAGING_CODE_CITATION_REGISTER.md). Earlier stage text below is historical/provisional and must not override the agreed A-primary/B-sensitivity policy, Diamond-only 2018–2019 distinction, source-code meaning limitations, and hard-blocked full scan.


> **Historical workflow only for year-specific local signoff.** The investigator clarified that **2018–2019 is Diamond's period, NOT an automatic Research Network restriction**. For Research Network, use the literature-reviewed exact CPT core and private adjudication in [Steps54–55](STEP54_55_LITERATURE_CODEBOOK_REVIEW_AND_RESEARCH_NETWORK_PERIOD.md). Do not use this workflow's hardcoded `valid_for_2018_2019_yes_no` as Research Network all-year evidence, and do not run Step47 `finalize` for the Research Network using this stale time assumption. Clinical coding meaning can be reviewed from literature, but TriNetX clinical event completion semantics remain unverified.

**Status:** A safe reviewer-preparation workflow. **No clinical data read, no imaging codes auto-approved, and no full clinical scan started.** This follows the Step 45 plan-only validation (275 previously passing tests).

The goal is to prepare **one clinician/data-steward handoff** for the manuscript's imaging definitions, then produce a Step45-compatible codebook **only after explicit documented clinical sign-off**. This eliminates repeated assistant/user exchanges for individual CPT codes.

## Confirmed co-primary cohorts

- Uniform 18–50 years (all sex categories)
- Historical sex-specific: men 18–52, women 18–54

Both are primary and overlapping. Imaging ascertainment rules must be documented for *both*.

## Step 46: Safe one-time preparation

On the study workstation, from the cloned branch:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q && python scripts/step46_47_imaging_review_bundle.py prepare
```

The script only reads the **existing local** Step 42 reference candidate CSV and aggregate status JSON. It does **not** reopen the Research Network ZIP or read `patient.csv`, `encounter.csv`, `diagnosis.csv`, or `procedure.csv`.

It checks the Step42 stage, row count, discovery-reason and candidate-category reconciliation. It then preserves all discovered entries and prioritizes the historical **14 CPT anchors** plus up to five additional entries per category (default). This is a *convenience first review*, never the complete/validated code list.

All generated files are kept inside the cloned repository's Git-ignored `results/phase1/full_reconstruction_private/imaging_review/`:

```text
all_reference_candidates_LOCAL_ONLY.csv
clinical_review_priority_LOCAL_ONLY.csv
imaging_reviewer_brief_LOCAL_ONLY.md
imaging_review_signoff_LOCAL_ONLY.json
imaging_review_preparation_status_LOCAL_ONLY.json
```

These are owner-only files (mode 0600; directory 0700). Do not upload, publish, commit, or email the CSVs outside a data-owner-approved secure collaboration workflow. The reference data might itself be covered by data-use restrictions.

**The existing Step45 `approvals_LOCAL_ONLY.json` and `imaging_codebook_APPROVED_LOCAL_ONLY.csv` are NEVER modified by Step46.** If any Step46 file exists, preparation aborts rather than overwriting clinical annotations. Do not rerun `prepare` over a clinician-edited file.

## How the clinician reviews the packet

Open `clinical_review_priority_LOCAL_ONLY.csv` alongside the brief and the full inventory. The sheet shows the exact Research Network code system, code, source description, original candidate category, and the reason for its selection. Reference descriptions are the input to human review, **not evidence** of actual performed care.

Only edit these designated review columns:

| Column | Required response for an included code |
|---|---|
| `clinician_decision_INCLUDE_EXCLUDE_DEFER` | `include`, `exclude`, or `defer` |
| `reviewed_category` | MRI_BRAIN, CTA_HEAD, CTA_NECK, MRA_HEAD, MRA_NECK, or CT_HEAD |
| `performed_procedure_confirmed_yes_no` | `yes` with justification |
| `valid_for_2018_2019_yes_no` | `yes` based on period-valid coding |
| `anatomy_resolved_yes_no` | `yes` with technique/anatomy verified |
| `clinical_rationale` and `evidence_reference` | Explicit clinical explanation and source |
| `reviewer`, `review_date` | Actual reviewer and ISO date |

Use `defer` if the code refers to an order, reported finding, history, mixed head/neck code, or another unresolved concept. CPT anchors are **not** automatically approved. The Step42 list may omit local or otherwise valid clinical codes. An empty decision is not approval.

For comprehensive review, the authorized reviewer may edit `all_reference_candidates_LOCAL_ONLY.csv` instead of the small priority sheet. The later `finalize` command accepts either, while preserving provenance by per-row hash.

The reviewer should also confirm **IMP inpatient status**, principal-diagnosis indicator **P**, encounter/source identifier scope, and limitations of missing imaging capture. These require separate data-steward/clinical decisions and are not resolved by this codebook.

## Step 47: Optional AFTER clinical sign-off (do not run now)

A designated investigator/clinician must review the full candidate inventory scope, procedure coding semantics, 2018–2019 applicability, and anatomy conflicts, document an institutional clinical-review authority, and deliberately change the *local* `imaging_review_signoff_LOCAL_ONLY.json` fields from false to true **only where supported by actual review**.

Only then run:

```bash
python scripts/step46_47_imaging_review_bundle.py finalize
```

To use the completed **full inventory** instead of the priority sheet:

```bash
python scripts/step46_47_imaging_review_bundle.py finalize \
  --review-file results/phase1/full_reconstruction_private/imaging_review/all_reference_candidates_LOCAL_ONLY.csv
```

Step47 fails closed if signing is incomplete, the exact Step42 source CSV or its aggregate report has changed since packet preparation, a code/system identity or protected reference field is altered, an included code lacks performed-procedure/anatomical/year evidence, its code is duplicated, or the Step45 approved-codebook template has been edited or already filled.

On documented successful validation, it populates **only the existing empty**
`results/phase1/full_reconstruction_private/imaging_codebook_APPROVED_LOCAL_ONLY.csv`
using the exact columns expected by Step45. It also writes a private
`imaging_review_validation_status_LOCAL_ONLY.json` inside the imaging-review folder. The codebook and validation status are **not shareable clinical outputs**.

**Step47 does not and cannot grant institutional data access approval.** It never flips any of Step45's `approvals_LOCAL_ONLY.json` flags, reads source clinical files, runs the source-wide scan, or publishes cohort results.

## Decision after the review

The other Step45 gates remain: institutional data-use permission, encrypted local storage, inpatient and principal-diagnosis meanings, source/encounter key semantics, the *two* co-primary age protocols and YOB boundary policy, and a disclosure/quality plan. After they are documented, audit the pipeline readiness with local clinicians/stewards **before** issuing any full-scan confirmation flags.

No merged PR or clinical source-wide scan is appropriate yet. The existing public-repository legacy TriNetX Git history still needs separate institutional review.

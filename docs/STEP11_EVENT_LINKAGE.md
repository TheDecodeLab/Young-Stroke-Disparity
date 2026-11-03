# Step 10 reconciliation results and Step 11 event-linkage audit

## Findings from study-team aggregate Step 10 output

The legacy imaging-selected table (30,619 unique patients) is a
**complete patient-ID subset** of the CT-retaining candidate (52,893).
The candidate contains 22,274 additional IDs. This is a membership
fact, not validation that the records share the same stroke event.

Among the 30,619 shared patients, the CT-retaining file classifies:
- 29,104 as CT-positive and MRI/CTA/MRA-positive;
- 723 as CT-positive but without MRI/CTA/MRA;
- 792 as MRI/CTA/MRA-positive but without recorded CT.

These categories add to 30,619. Consequently, the 1,515 difference
between legacy patients and candidate CT-plus-advanced patients
is explained by the 723 + 792 shared patients who are assigned a
different modality combination in the CT-retaining file.

Other shared-record disagreements:
- MRI procedure count differs for 564 patients.
- CTA differs for 270; MRA differs for 155.
- Diagnosis year and age-at-stroke differ for 179.
- Sex and stroke labels agree for all shared patients.

Discrepancy groups can overlap; do not add their counts as though
they are disjoint. The results demonstrate **index-date or modality
attribution disagreement**, but do not identify the mechanism.
Potential causes include different earliest-date rules, imaging windows,
or data production versions. We must test, not assume, the cause.

In the common age 19-50 candidate, there are 40,356 patients,
including 30,560 CT-positive, 8,471 CT-only, and 9,796 with advanced
imaging but no recorded CT. The corresponding selected legacy cohort
has 23,232 patients. No corrected imaging rate should be published
using either denominator until index eligibility and event linkage
have been verified.

## Step 11: check the pre-exclusion imaging-to-diagnosis linkage

From the repository root:

```bash
git fetch origin
git switch analysis-rebuild-phase1-audit
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step11_event_linkage.py
```

Inputs default to approved LOCAL files one directory above the clone:

- `df_merged_age.parquet`: imaging-to-diagnosis event rows saved
  before CT rows were removed.
- `df_trinetx_total_young_wCT.parquet`: CT-retaining candidate.
- `df_trinetx_total_young.parquet`: legacy selected table.

The script reads just the columns needed for diagnosis/procedure
linkage checks. It does not save patient rows or identifier values.

**Output:** `results/phase1/event_linkage_audit.json`, an aggregate
report. Inspect for sensitive content before sharing.

The script reports:
- How many patients have more than one diagnosis date with imaging
  already linked in the intermediate file.
- How often the same patient + CPT code + procedure date links to
  multiple diagnosis dates.
- CT-only versus CT-plus-advanced modalities at the **earliest
  imaging-linked diagnosis date**.
- Patients with CT-only at their earliest linked date but advanced
  imaging at a different linked date (and the reverse).
- Disagreements between this provisional first linked diagnosis
  and the candidate/legacy saved years and modality-receipt flags.

## Major limitations and stop rule

**These dates are NOT established admissions.** The historical
notebook joined imaging procedures and principal diagnoses primarily
by patient ID and then retained a +/-7-day window. One procedure can
therefore link to more than one qualifying diagnosis. Also,
`df_merged_age.parquet` contains only diagnosis rows which already
matched some imaging, so the earliest *linked* diagnosis need not be
the earliest clinical stroke.

The results from Step 11 must be used only to diagnose the failure
mode and decide how to reconstruct an index cohort. We should use
original diagnosis and procedure source tables, including encounter
IDs and original event dates where available, to establish eligible
index stroke events **before selecting imaging**. Retain CT-only
patients with an explicit left join for MRI/CTA/MRA.

Do not refit imaging utilization models, rewrite manuscript results,
or merge this draft PR until this source-level work is complete.

## Data handling

The local inputs may contain pseudonymous patient identifiers and
geographic data. Do not upload any row-level files, record excerpts,
notebook outputs, or unsuppressed small-cell patient tables to the
public repository or to this conversation. Share only approved
aggregate audit JSON after checking it locally.

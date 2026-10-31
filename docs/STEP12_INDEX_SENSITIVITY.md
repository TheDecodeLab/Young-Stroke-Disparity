# Step 11 reviewed: choose the provisional index before rebuilding any cohort

## Step 11 findings (aggregate output, October 16, 2026)

- `df_trinetx_total_young_wCT.parquet` matches earliest **imaging-linked**
  principal ischemic-stroke diagnosis in the intermediate: all 52,893
  shared patient IDs match for diagnosis year and binary MRI/CTA/MRA
  receipt. This confirms internal derivation consistency, **not** true
  first clinical stroke or correct encounter linkage.
- The original imaging-selected manuscript cohort contains 30,619 of
  these patients but differs from the earliest imaging-linked diagnosis
  in diagnosis year for 179 patients, MRI receipt for 564, CTA receipt
  for 270, and MRA receipt for 155.
- Of 385,823 people with at least one imaging-linked principal ischemic
  diagnosis, 40,307 have multiple linked diagnosis dates.
- Among first imaging-linked diagnoses, 96,907 patients have CT without
  MRI/CTA/MRA, and 199,283 have CT with one of these modalities.
- Another 5,279 people have CT-only imaging at the earliest linked
  diagnosis but advanced imaging at another diagnosis date. In the
  reverse direction, 4,305 have advanced imaging without CT at their
  earliest linked date but CT at another linked date.
- Step 11 reports **zero** repeated procedure linkage keys. This is
  **not evidence of a clean encounter join**: historical notebook cell
  9 already removed duplicates by `patient_id, code_px, date_px`
  before saving `df_merged_age.parquet`. That operation necessarily
  hides cases where one procedure originally joined multiple diagnoses.

## Scientific implication

We now understand that the CT-retaining candidate is reproducible
relative to the earliest **imaging-linked** diagnosis. The original
analysis altered the selected date by removing CT events before
choosing an earliest surviving date. An index selected after imaging
can introduce selection bias and attribute imaging to the wrong
ischemic-stroke episode.

However, neither saved file can establish the earliest genuine
hospitalized stroke without access to original diagnosis and
encounter records. The linked intermediate contains only diagnoses
with at least one matching imaging event.

## Step 12: quantify sensitivity to the index rule

Run locally from the repository root:

```bash
git fetch origin
git switch analysis-rebuild-phase1-audit
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step12_index_sensitivity.py
```

Default input: `../df_merged_age.parquet`

Default output: `results/phase1/index_definition_audit.json` (ignored)

The script compares, using only event information already stored in
the intermediate:

1. Earliest diagnosis with **any imaging** linked.
2. Earliest diagnosis with **CT** linked.
3. Earliest diagnosis with **MRI, CTA or MRA** linked among people
   who have CT at *some* diagnosis date.

It reports aggregate CT-only and CT-plus-advanced counts for the
first CT-linked diagnosis, and how often the first advanced-linked
diagnosis differs from the first CT-linked diagnosis, including
direction and year differences. It keeps patient IDs and actual
dates in local memory and writes only aggregate counts.

This is **not** the definitive CT-index cohort, since the procedure
and diagnosis intermediate was already derived from an unverified
patient-only join and an imaging requirement. The script must not
create publication rates or adjusted sex/race models.

## Next decision

- If index definitions diverge substantially, prioritize obtaining
  the original authorized diagnosis, encounter, and procedure records
  and building an index stroke cohort **before** linking imaging.
- Even if they agree, source-event verification is still required.
- Use an encounter identifier if available; otherwise document
  limitations of patient/date matching and explicitly audit ambiguous
  diagnosis-to-imaging links.
- Preserve CT-only eligible patients with a left join of non-CT
  modality events. Validate denominators, patient/year selection,
  missingness, and code sets before statistical modeling.
- NIS analyses remain separate and blocked pending design verification.

Do not upload row-level data or identifiable dates. The existing
public repository requires a data-sharing compliance review.

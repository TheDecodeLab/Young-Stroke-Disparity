# Step82: Paired demographic sensitivity to imaging-code encounter attribution

**Status (2026-10-21):** investigator Step82 run COMPLETED: eight
synthetic tests and the full **765-test** suite passed with three
previously observed warnings; the restricted no-rescan local analysis
finished successfully. Recorded-code demographic contrasts vary
substantially with encounter attribution. Detailed local outputs are
investigator-held only; no demographic estimates or counts are committed.

**Quality issue discovered after first run:** the P1-only model's
overlap diagnostic was inherited from Step73 and required records
at P=0, although P=0 is structurally excluded in that subset.
This forced every P1 adjusted estimate to be incorrectly marked
WITHHELD. Step82 now uses explicit scope-specific P and ambiguity
strata: quality=(P0,P1)x(held0,held1);
P1=P1x(held0,held1); clean=(P0,P1)xheld0.
The test suite now includes fabricated regression cases for
structural absence versus truly sparse intersections.
**Corrected P1 results are NOT yet verified on the workstation.**
Run Step82 again before using P1 results or finalizing a
demographic-scientific positioning decision. Normal disclosure
and no-HCO limitations remain unchanged.

## Scientific question and design

Among patients **definitely age 18–50** with an indexed I63-coded inpatient
encounter, does the observed sex, race or ethnicity difference in a
documented neuroimaging CPT code change when the definition broadens
from the indexed inpatient encounter to any same-day encounter?

This question examines **measurement sensitivity**. It does not
establish actual imaging receipt, inequity in clinical care, or the
true reason for differences. Index I63 coded as principal is an
unvalidated *recording flag*, not an adjudicated acute stroke subtype.

## Source and procedure safeguards

- Reuses Step62 person/index data, Step63 patient/ED metadata and Step68
  frozen **CPT14 patient/cohort/modality mask** only.
- Reconciles every grouped primary-cohort denominator and both any-code
  numerators to frozen Step68 aggregate totals, after checking source
  signatures and completed procedure-scan progress.
- Does **not** access the original 993,025,015-row source
  procedure member or medications, nor export patient IDs or person rows.
- All subgroup computations remain **on the approved workstation**.
  Nothing is committed to GitHub, emailed or cleared for external
  sharing.

## Endpoints and contrasts

Five outcomes, each under two *nested* definitions:

1. Any among the 14 recorded imaging CPT codes.
2. Head CT CPT codes.
3. Brain MRI CPT codes.
4. Head CTA CPT code.
5. Advanced imaging, any brain MRI or head/neck CTA/MRA CPT code.

Definitions: indexed IMP encounter during indexed stay, and indexed
IMP or another encounter on the index date. Each person contributes
at most once per endpoint. The additional same-day window is
**not** assumed to represent the same hospital or clinical episode.

Primary comparisons: male vs female, Black/African American vs White,
Hispanic vs non-Hispanic. These are fields as *recorded/mapped* in
the EHR; their missingness and category mapping are important
limitations. Unknown/unmapped groups remain in the adjusted model
as covariates, but are not the reported main comparisons.

## Uncertainty, gates and limitations

- The crude pairwise difference at each definition is reported
  with a **nominal 95% interval for the contrast in newly added
  patient codes**; because the indicators are nested, each
  patient's addition is its own 0/1 paired outcome. This
  captures paired within-person changes without misusing
  two independent-definition confidence intervals.
- Grouped-binomial models estimate adjusted **marginal percentage
  point differences** with 95% *delta-method nominal intervals*,
  conditioning on the fitted model and treating patients as
  independent.
- Primary models include year, coarse age-year band, P,
  ambiguity status and the other recorded demographics.
  Additional fits use P=1-only and ambiguity-free subsets
  as restricted sensitivity analyses.
- Each displayed crude comparison requires denominator, event,
  non-event, newly added event and complement at least 11
  in *both* compared groups, plus at least 11 patients
  in every group/P/ambiguity support cell. Adjusted contrasts
  have event/complement and support checks.
  These are conservative **internal rules**, not complete
  cross-table disclosure certification. No subgroup n,
  events, or demographic rates are displayed.
- No available hospital identifier supports clustered
  standard errors. The reported intervals assume independent
  patients and **must not be treated as definitive tests of
  inequity or practice differences**. Clinical severity,
  hospital mix, treatment indication, encounter quality and
  outcome coding are not comprehensively adjusted.

## Mechanism and treatment positive-control questions

The metadata retained by Step63 contain *EMER* and *IMP*
encounter types, but the extra Step68 same-day imaging
masks have **lost their original procedure-bearing encounter
ID and type**. The frozen databases therefore do not identify
whether added same-day codes were on radiology, outpatient,
ED or other encounter types. A definitive encounter-type
breakdown would require separately justified, permissioned
processing from retained raw sources; it is not inferred here.

Patient-level thrombolysis or thrombectomy indicators were
not retained. Step68 aggregate frequencies of non-imaging
procedure **source rows** cannot establish treatment patients
or their overlap with imaging. Do not infer validation of
imaging from published stroke imaging rates.

## Execution

```bash
(
  set -e
  git pull --ff-only origin analysis-rebuild-phase1-audit
  python -m py_compile scripts/step82_demographic_definition_sensitivity.py
  python -m pytest -q tests/test_step82_demographic_definition_sensitivity.py
  python -m pytest -q
  python scripts/step82_demographic_definition_sensitivity.py
)
```

Return **TERMINAL OUTPUT ONLY** for internal scientific assessment.
Do not upload source data, SQLite files, private report packages,
patient/encounter identifiers or source exact-code profiles.

## Interpretation decision

If pairwise demographic differences depend materially on
encounter attribution, preserve the measurement-led combined
paper with the demographic sensitivity in a secondary
section. If source-quality overlap, sparse cells, or
model instability prevent interpretable demographic
contrasts, retain them internally and move forward with
a methods paper. Do not rewrite the paper or claim a
clinical disparity before this gate.

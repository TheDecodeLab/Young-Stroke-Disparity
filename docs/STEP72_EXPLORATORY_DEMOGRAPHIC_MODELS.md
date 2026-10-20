# Step72: Exploratory adjusted associations in documented imaging-code capture

**Status:** Read-only implementation and fabricated tests on the analysis
branch; the investigator has NOT yet run Step72 locally. No source ZIP
scan. No patient/encounter-level results saved.

## Why this is an exploratory modeling screen

Step71 completed locally with 696 tests passing. On the primary
uniform ages 18–50 cohort, the previously frozen CPT14 inpatient
outcome and same-day another-encounter sensitivity capture very
different proportions across demographic groups. Race/ethnicity
have substantial unknown/unmapped fractions. Some groups, notably
NHPI, exhibit large differences in the unvalidated I63 P marker,
patient-level encounter-key quarantine, and outcome definition.
Thus crude code-capture percentages cannot be directly interpreted
as differential receipt of medically indicated neuroimaging.

Step72 makes the next analysis concrete without relaxing outcome
definitions. It fits a **descriptive association model** for
predefined *documented CPT14 imaging code outcomes*, NOT a
causal model, patient-care quality metric, or validated performed
radiology measure.

## Design and repeated measures

- Index grain is **one patient per frozen indexed cohort**,
  years 2016–24. The uniform age 18–50 cohort is the primary
  cohort; the sex-dependent historical age limits are analyzed
  separately as sensitivity. Their denominators overlap and
  must **never** be added or treated as independent.
- All patient identifiers and unrecognized raw demographic labels
  are stripped **before modeling**. Covariates and outcome
  numerators are aggregated in memory into finite combinations;
  no sensitive model-input data are saved or committed.
- Sex, race and ethnicity are separate categories, conservatively
  mapped with the exact reviewed Step71 dictionary. Missing
  demographic categories remain explicit in the main model.
  `OTHER_OR_UNMAPPED` is NOT a scientifically defined race.
- Age uses index year minus year of birth, grouped in coarse
  `UNDER25`, `25TO34`, `35TO44`, and `45PLUS`
  **age-year proxy** bands. Birth date is unknown (age ±1
  year), so these are not actual birthday-derived age bins.
- Calendar-year category (2016–2024) is adjusted as a factor.
- `P` is the unvalidated binary principal I63 marker;
  `P=0` includes S/blank/non-P. Encounter quality `held`
  is 1 if **any** patient's EMER/IMP encounter key was
  quarantined in Step63, not necessarily index encounter.
  These two are covariates in sensitivity models, not confirmed
  clinical confounders.
- No HCO identifier or reliable clustering is available.
  This prevents a defensible site-adjusted care-quality
  or multilevel causal inference; **no p-values, model-based
  confidence intervals or national representation claims**
  are emitted.

## Outcomes, from the frozen 14 CPT procedure codes

- Inpatient `ANY_CPT14` on index IMP within encounter date span.
- Inpatient *advanced CPT14* composite: brain MRI, CTA head/neck
  or MRA head/neck. CT HEAD excluded from advanced composite.
- Exploratory `ANY_CPT14` on index IMP OR a different encounter
  on the same index admission calendar date. This is a
  code-capture screen, not verified same-hospital episode.
- Analogous expanded same-day *advanced CPT14* composite.
- For the uniform cohort, three additional inpatient-coded
  modality checks: CT HEAD, MRI BRAIN and CTA HEAD.

No ICD-10-PCS/SNOMED/HCPCS code is classified as imaging here.
An exact year-valid broader codebook is a **separate**
evidence review; Step69's source-row B-prefix frequencies
must not be interpreted as imaging.

## Model and estimand

Python `statsmodels` grouped binomial GLM with exact
aggregated numerator/denominator and `var_weights=n`.
Covariates are year, coarse age-year proxy, sex, race and
ethnicity; the additional measurement-quality model
also conditions on P and patient-level Step63 quarantine.
For each focal demographic category, create the model's
predicted probability **as if** all cohort covariate
combinations had that label (same pooled distribution),
average predicted probabilities weighted by each stratum's
count, and report **standardized percentage-point
difference from a reference label**.

Reference categories: male for sex; white for race;
not-Hispanic/Latino for ethnicity. These are comparison
anchors, not normative or causal reference choices.

Primary quality-adjusted models are fit for the 4 principal
outcomes in both age cohorts. Additional primary-cohort
inpatient and same-day models are fit under:
- demographic/year/age alone (no P or quarantine);
- no patients with ANY quarantined encounter key;
- complete recognized sex/race/ethnicity categories, with P
  and quarantine retained.

Modality-specific inpatient CT HEAD, MRI BRAIN and CTA HEAD
receive the primary quality-adjusted model only.

Models must converge, have bounded coefficients and show
supported reference/focal demographic categories. Failures
are surfaced rather than silently replaced with estimates.

**Interpretation:** These are GLM model-based **associations
in coded procedure capture conditional on measured variables**,
not actual differential radiology use, equal clinical
eligibility/appropriateness, or absence of unmeasured
disease severity and hospital selection effects.
Replacing a person's demographic label in a marginal
prediction is an *analytic standardization operation*,
not an intervention, and is especially extrapolative
for sparse P/quarantine combinations.

## Input integrity

The script opens Step62, Step63 and Step68 private databases
in query-only read-only mode, verifies frozen snapshots
using the independent Step64 checker, and reconciles both
cohort denominators and original inpatient/same-day
`ANY_CPT14` patient counts to Step68.
All demographic variables and outcomes are extracted
through the fixed Step71 code-mapping and outcome rules.

It processes no source ZIP and never saves a patient-
level or aggregated modeling table. Printed group n
and estimates are not institutionally disclosure-cleared.

## One bundled local run

```bash
(
  set -e
  git pull --ff-only origin analysis-rebuild-phase1-audit
  python -m py_compile scripts/step72_exploratory_demographic_models.py
  python -m pytest -q tests/test_step72_exploratory_demographic_models.py
  python -m pytest -q
  python scripts/step72_exploratory_demographic_models.py
)
```

Stop on **any** failing synthetic/full test. The script reads
private checkpoint databases; no source ZIP needed.

**Requested handoff: TERMINAL OUTPUT ONLY**.
No ZIP, SQLite, JSON, model coefficients or patient data files.
If a model is unavailable, the output prints the count of failed
models and returns nonzero. Report the terminal output and the
failure status rather than restarting frozen source pipelines.

## Decision gate after the results

Evaluate whether demographic standardized code-capture
differences:

1. persist for the frozen same-IMP primary outcome;
2. materially shift for an unverified same-day
   another-encounter definition;
3. attenuate when conditioning on P/quarantine or
   removing quarantined patient keys;
4. change with complete-case selection, especially given
   missing race/ethnicity;
5. appear across CT vs advanced modalities and both
   overlapping cohort definitions.

If robust **code-capture associations** remain, freeze
a clearly named primary estimand and sensitivity hierarchy,
then develop final statistical reports with appropriate
site/case-mix limitations. Do not represent this step's
point estimates as confirmed clinical care disparities.

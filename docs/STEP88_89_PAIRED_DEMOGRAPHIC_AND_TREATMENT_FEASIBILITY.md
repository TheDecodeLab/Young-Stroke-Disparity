# Steps 88-89: Paired demographic risk differences and treatment-source feasibility

**Status:** Added code and synthetic-only unit tests. No study-specific regression estimate has been generated in this environment. The author must run the analysis on the approved workstation using the existing frozen Step62/63/68 checkpoints. No TriNetX ZIP scan is needed for Step88. Step89 opens ZIP *headers only* and reads an already saved aggregate code profile.

## Scientific question and estimand

The primary measurement question remains: how does the recorded presence of a qualifying CPT code change when the same indexed patient is evaluated under two nested encounter rules?

For each prespecified source demographic contrast, Step88 estimates:

1. Model-standardized risk difference (RD) in *any eligible code present* under Rule 1 (index inpatient only).
2. The corresponding RD under Rule 2 (index or other same-day encounter).
3. The **difference of the two RDs**, using the same patients, covariates and reference population within each analytic scope.
4. Paired 95% patient-bootstrap percentile intervals for all three values, computed by resampling the **joint** three-state outcome (neither rule, Rule 2 only, both rules) together with its covariate stratum.

The multinomial resampling is exactly equivalent to a nonparametric patient-level bootstrap of the observed grouped `(covariates, Rule1, Rule2)` records. Since the outcome under Rule 1 is nested in Rule 2, there is no `(Rule1=1, Rule2=0)` state. The grouped data retain all information needed for the pair. We do not model the two rule outcomes as independent binomials and we do not use the adjusted effect from a separate gained-code logistic model as a substitute for the difference between two separately fit standardized risks.

The original Step82 fitted separate adjusted code-presence models, but did not produce paired CIs for the difference between the rule-specific RDs. The original Step83 gain model estimates a related but not numerically identical adjusted quantity because the logit link is nonlinear. This distinction must be stated in the manuscript.

## Data and models

- The script uses the Step82 source-to-aggregate `stream()`, `group_rows()`, and `verify()` helpers to read only frozen indexed patient/modality flags. All demographic, age-year, and source P/ambiguity mappings remain identical to Step82.
- Prespecified demographic comparisons: female versus male; Black versus White; Hispanic versus non-Hispanic.
- A grouped-binomial logit model adjusts for the other demographics, calendar year, birth-year age band, the principal-I63 recording flag P, and encounter-key ambiguity. A common standardized population within each model scope is used for both rule-specific estimates.
- Outcomes: any CPT14 and advanced CPT14 (which excludes plain head CT). Full-cohort and complete-demographics-sample analyses use the same outcome definitions but **different samples**.
- Nonzero event, nonevent, incremental-event, and complementary-cell minima and P-by-ambiguity overlap gates must pass before any contrast is exported. All outputs remain **restricted aggregate artifacts**.
- The default resampling count is 399 with a fixed seed. This is a configurable Monte Carlo accuracy parameter, not a study observation or a prespecified sample-size justification. Review the uncertainty and numerical convergence before any manuscript use.
- Design-effect factors 1, 2, 5, and 10 simply inflate the paired-bootstrap standard error as hypothetical clustering sensitivity. They are **not HCO-cluster CIs** or substitutes for hospital labels.

**Important limitations:** Neither GLM adjustment nor patient-resampled CIs identify a causal demographic disparity. Hospital-level clustering, clinical severity, availability of codes across sources, imaging indication, and true performed examinations remain unobserved. The complete-case population differs from the full analysis population, so changes across these samples are not a paired within-sample effect.

## Safe local execution

From the GitHub project root, on the workstation that holds the frozen checkpoints:

```bash
(
  set -e
  git pull --ff-only origin analysis-rebuild-phase1-audit
  python -m pytest -q tests/test_step88_paired_demographic_rule_contrasts.py tests/test_step89_treatment_source_feasibility.py
  python -m pytest -q
  python scripts/step88_paired_demographic_rule_contrasts.py \
    --bootstrap 399 \
    --acknowledge I_CONFIRM_INTERNAL_REVIEW_ONLY
)
```

The new internal JSON will be written to:

`results/phase1/full_reconstruction_private/step88_paired_demographics_private/paired_rule_contrasts_LOCAL_ONLY.json`

No public repo upload is permitted for this output. When the author confirms that the publication-result subset can be shared, the author may provide that aggregate JSON through the approved channel for targeted manuscript revisions. Only one scoped and date-labeled output should be incorporated into the manuscript, without suppressions that can be undone by table subtraction.

## Treatment and encounter source feasibility (Step89)

**Step89 is metadata-only.** It checks `medication_drug.csv`, `medication_ingredient.csv`, and `encounter.csv` header fields in the original Research Network ZIP and confirms the size/header fingerprints of the four established Step36 source members. It queries the existing Step68 `code_profile` for *source-row* evidence concerning CPT 61645 and 37184. It does **not** access a source clinical row, calculate treatment prevalence, or demonstrate imaging receipt.

CPT 61645 is a candidate intracranial mechanical thrombectomy code. CPT 37184 explicitly represents **nonintracranial** mechanical thrombectomy and must not be counted as an intracranial stroke-treatment positive control. Before using either medication or procedure codes for a clinical plausibility analysis, verify service-year versions and the medication *administration* status rather than treating orders/mentions as administered therapy.

The clinical rationale for treatment-enriched imaging is plausible, but no gold standard of performed imaging is available. Any treatment-defined cohort is a select subgroup, cannot independently establish sensitivity or specificity, and cannot establish the accuracy of Rule 2. Exact additional same-day encounter-type attribution would require the source code-bearing encounter ID, which Step68 collapsed into patient-level masks. Step63 retains `EMER` and `IMP` encounter metadata only. A full additional procedure pass remains **deferred**, not automatically justified.

To run the bounded metadata check:

```bash
python scripts/step89_treatment_source_feasibility.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip" \
  --acknowledge I_CONFIRM_INTERNAL_REVIEW_ONLY
```

The command prints only broad availability and code-presence flags. A missing candidate code in Step68's *narrow temporal profiling scope* is not proof that the source never records it elsewhere. Do not initiate a new source scan until these feasibility results are reviewed.

## Manuscript decision gates

- **Table 2:** Replace the isolated adjusted new-code gain comparison with rule-specific marginal RDs and the within-patient change plus paired CIs **only after Step88 runs and the outputs reconcile**. Keep old gain-model values in an appropriately labeled historical sensitivity table if needed for audit. Do not combine adjusted effects from different model specifications as if algebraically interchangeable.
- **Supplementary Table S8:** Replace the missing intervals with paired-model nominal CIs and a clear note that the two scopes compare different target populations. Verify the reported sign reversal against the new fit rather than importing old point estimates.
- **Overall capture:** The current observed index-only and same-day totals remain primary. The descriptive P flag and historical Diamond context may move largely to supplement after the new modeling results are reviewed. Do not infer that Rule 2 is clinically correct simply because it records more codes.
- **Clinical check:** Do not call CPT 61645 or unverified medication mentions a validated positive control. Require a year-specific medication/procedure coding protocol and a recorded-administration check before any new clinical claim.
- **Declarations:** Fill the actual ethics/protocol, funding, conflict-of-interest, data/code access, and generative-AI-use disclosures from real institutional and journal records. Do not fabricate approved language.
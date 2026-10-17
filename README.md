# Young Stroke Neuroimaging: Reproducibility and Re-analysis

This repository supports an observational study of brain MRI and vascular
imaging selection among adults hospitalized with early-onset ischemic stroke.
The prior notebook `disparity_young-claen.ipynb` remains **unchanged as the
legacy reference**. New work uses documented, tested Python scripts.

## Selected next path: preserve original hospitalization question (Step 27)

The research team chose to **seek an encounter-linked inpatient source**
rather than silently relabel diagnosis-date matches as hospital admissions.
No suitable common encounter key has been established in the original
Diamond ZIP. The 123-test Step 25 v2 run validated only aggregate
reconciliation and retained the historical disclosure warning.

Read these **review-only** documents, in order:
1. [Admission-level feasibility and episode-first protocol](docs/STEP27_HOSPITALIZATION_FEASIBILITY.md)
2. [Ready-to-edit data-steward request](docs/STEP27_ENCOUNTER_DATA_REQUEST.md)
3. [Approval and GO/STOP decision record](docs/STEP27_APPROVAL_RECORD_TEMPLATE.md)

**Do not start another billion-row ZIP scan or fit disparity models.**
First ask the authorized data steward whether shared admission keys,
episode dates, inpatient status, encounter-linked diagnoses/procedures
and reliable imaging capture are available. Request **schema and
field definitions only**, never private clinical data through email.
If encounter-linkage cannot be established, the original admission
study remains blocked and a distinct research question must be
formally approved.

## Next local step: safe candidate imaging-codebook preflight

The fixed-data plan now has a **14-code, clinically unapproved**
[CPT candidate catalog](dataset/imaging_codebook_candidate_v1.csv),
plus a [Step 28 review-gated extractor](docs/STEP28_IMAGING_CODEBOOK_PREFLIGHT.md).
The five candidate additions are CTA neck 70498 and MRA head/neck
70546-70549, supported by older CMS code lists but **not**
approved by a stroke clinician for the study protocol.

The next command is ONLY a metadata preflight. It does **not**
reprocess the source ZIP clinical rows or begin the 1.17-billion
procedure-row scan.

```bash
python -m pytest -q && python scripts/step28_imaging_extract.py --plan   --zip "$TRINETX_ZIP" --private-dir "$TRINETX_PRIVATE"   --output results/phase1/step28_codebook_plan.json
```

A future --execute requires separately documented investigator,
clinical and data-use review. The committed
[approval template](docs/STEP28_APPROVAL_TEMPLATE.json) has
decision=NOT_APPROVED and must NEVER be treated as actual approval.
No new TriNetX data will be requested. Do not merge or publish
unvalidated clinical results.

## Data availability constraint and study redesign

**Investigator confirmation (2026-10-17): No additional TriNetX data
can be obtained.** The current Diamond ZIP and completed private
SQLite indexes are the data ceiling. Do not propose an encounter-linked
TriNetX export as the next step. The existing ZIP has no verified
encounter or admission identifier; therefore the original hospitalized
ischemic-stroke imaging-utilization estimand is **not identifiable**
from these source tables.

See [Step 27 fixed-data salvage protocol](docs/STEP27_FIXED_DATA_SALVAGE_PLAN.md).
The proposed fallback question is **recorded imaging procedure codes
within a prespecified temporal window of the first observed 2018–19
principal I63 diagnosis**, NOT imaging during a verified admission or
access-to-care disparities. This redesign still requires investigator
and clinical sign-off, source capture/codebook validation, disclosure
review, and a deliberate go/no-go decision before any further
billion-row procedure scans or models.

## Latest validation: Step 25 reconciled, clinical inference BLOCKED

The study team's `step25_readiness_gate.json` reports **all prior
aggregate counts reconciled**, with no clinical ZIP or patient-level
SQLite records reread. The provisional diagnosis-first cohort has
962,351 principal I63 index patients and 86,902 age-eligible
patients. Of these, 8,713 have a CT-only code and 44,760 have none
of the historical nine-code matched modalities. Race missingness
is 77.9% and ethnicity missingness is 75.39%.

**Stop before additional billion-row rescans or demographic modeling.**
See [Step 26 protocol decisions](docs/STEP26_CLINICAL_PROTOCOL_DECISIONS.md)
for the study-denominator and encounter-validation alternatives,
original sex-specific age cutoffs (54 women / 52 men), incomplete
modality codebook, missingness and governance blockers. This is a
**review proposal, not approved methods**. A previous fine-grained
I63 subgroup report remains subject to disclosure review even though
its repaired replacement uses coarser groups.

## Status

**CRITICAL SCIENTIFIC STOP: The current derived cohort omits CT-only
stroke patients.** The Step 7 results show that all 23,232 age 19-50
patients received MRI, CTA or MRA. Review of the historical notebook
shows CT rows are removed before aggregating patient imaging.
Therefore Steps 2-7 currently describe an imaging-selected subset
and MUST NOT be used to estimate population MRI/vascular imaging rates
or clinical disparities. Reconstruct the index stroke cohort using the
upstream diagnosis, encounter and procedure data while retaining CT-only
patients. See [cohort selection audit](docs/COHORT_SELECTION_FINDING.md) [Step 9 recovery instructions](docs/STEP09_RECOVERY_PLAN.md), and [Step 10 reconciliation](docs/STEP10_RECONCILIATION.md), and [Step 11 event-linkage findings](docs/STEP11_EVENT_LINKAGE.md), and [Step 12 index-sensitivity audit](docs/STEP12_INDEX_SENSITIVITY.md), and [Step 13 source readiness](docs/STEP13_SOURCE_READINESS.md), [Step 14 source discovery](docs/STEP14_SOURCE_DISCOVERY.md), and [Step 15 original ZIP inventory](docs/STEP15_ZIP_SOURCE.md), and [Step 16 ZIP preflight](docs/STEP16_ZIP_PREFLIGHT.md), and [Step 17 provenance review](docs/STEP17_PROVENANCE.md), and [Step 18 diagnosis-first indexing](docs/STEP18_DIAGNOSIS_INDEX.md), and [the chained Steps 18–21 workflow](docs/STEP19_21_CHAINED_RECONSTRUCTION.md), and [Step 22 temporal validation](docs/STEP22_TEMPORAL_QC.md), and [Steps 23–24 exclusion and code audit](docs/STEP23_24_ELIGIBILITY_CODE_QC.md), and [Step 25 readiness and disclosure review](docs/STEP25_READINESS_GATE.md), and [Step 26 clinical protocol decisions](docs/STEP26_CLINICAL_PROTOCOL_DECISIONS.md), and [Step 27 hospitalization feasibility](docs/STEP27_HOSPITALIZATION_FEASIBILITY.md).



**Step 12 confirmed a second limitation:** among 208,867 imaging-linked
patients with CT and non-CT imaging in the larger event file, the earliest
CT-linked and earliest non-CT imaging-linked diagnosis dates differ for
9,584 patients (4.59%). These are not encounter-validated admissions.
Steps 01-12 are diagnostic, not valid final population estimates.
Next, locate the original diagnosis/procedure/demographic exports and
run the Step 13 source readiness audit before reconstruction.

**Latest source inventory:** Step 13 returned `not_found` for diagnosis,
procedure and demographic example paths. The study team subsequently
identified the original TriNetX ZIP archive in local approved storage.
Step 15 identified original `diagnosis.csv`, `procedure.csv`, and
`patient.csv` archive members. Step 16 confirmed YYYYMMDD source dates,
ICD-9/ICD-10 and CPT/HCPCS code systems, and no identifiable
encounter ID anywhere in the ZIP headers. The `reason_for_visit`
field is descriptive, not an encounter ID. Run Step 17 to review
archive cohort and dataset metadata before attempting a full scan.
Step 17 verified Diamond-wide export provenance (4.29 million
patients, 92 HCOs, 1.43 billion diagnoses and 1.17 billion procedures).
Step 18 begins a *staged*, imaging-independent principal I63
diagnosis index directly from the ZIP in an owner-only SQLite
directory outside Git. Run synthetic tests and a limited smoke test before starting the
large full scan. The new staged workflow chains diagnosis,
demographics, imaging and CT-only QC with checkpointing; complete
scans alone do not validate hospital admissions or clinical coding. The study remains blocked for
publication inference until codebook, age, admission and temporal
imaging-linkage rules are validated.

**Original source scan completed, provisional cohort only.** The 2018–19
principal I63 diagnosis index has 962,351 patients; 86,902 meet approximate
age 19–50 and recognized-sex eligibility. Within a ±7 day window,
8,713 have CT only, 24,074 CT plus additional imaging,
9,355 additional imaging without CT, and 44,760 none of the four
historically coded imaging groups. These are *not hospital utilization
rates* because source encounter IDs and a complete imaging codebook
are absent. Step 22 can audit time-window sensitivity by reading
only the completed private SQLite files and does NOT rescan the ZIP.

**Phase 1: data provenance and baseline audit (in progress).**
No new adjusted association or manuscript finding has been validated.
Do not interpret imaging frequency as quality or equity of clinical care.

## Requirements

Python >=3.9 (3.10+ recommended). The reconstruction tests were exercised by the study team with Python 3.9.18. In the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

## Fast post-scan quality checks (no ZIP scan)

After the full chain has successfully completed, use the same
owner-only private storage directory for read-only temporal validation:

```bash
python scripts/step22_temporal_qc.py \
  --private-dir "$TRINETX_PRIVATE" \
  --compare-audit results/phase1/chained_reconstruction_audit.json
```

See [Step 22](docs/STEP22_TEMPORAL_QC.md). This does not construct
a validated admission cohort, and published rates/models remain blocked.

## Combined post-scan exclusion and code-family audit

Step 22 reproduced all original reconstructed counts and showed that
time-window choice substantially affects imaging assignment. It also
reported 77.9% unknown/missing race and 75.4% unknown/missing ethnicity.
To investigate cohort eligibility and why patients lack matching imaging,
run the combined Steps 23–24 audit with the **existing completed private
SQLite files** and only original patient.csv, not the much larger
diagnosis/procedure members:

```bash
python scripts/step23_24_eligibility_qc.py \
  --private-dir "$TRINETX_PRIVATE" \
  --zip "$TRINETX_ZIP" \
  --compare-step22 results/phase1/step22_temporal_qc.json
```

Do not treat the output as encounter-verified admissions or manuscript rates.
Review the aggregate report for small-cell and complementary disclosure.

**Step 23-24 disclosure correction:** A rare I63 code group in the
initial fine-grained JSON was withheld, but its size can be inferred
by subtracting other visible groups from the total. Do not redistribute
the earlier report without disclosure review. The revised script reports
only `I63.9 family` vs `Other I63 codes`, with all-or-none suppression.
Step 25 checks cross-report consistency using only aggregate JSONs;
it does not scan patient records or certify that manuscript modeling is
ready.

## Step-by-step execution

```bash
python scripts/step01_audit.py
python scripts/step02_prepare.py --max-age 50
python scripts/step03_describe.py
python scripts/step04_audit_nis.py
python scripts/step05_missingness.py
python scripts/step06_minimal_models.py
python scripts/step07_modality_patterns.py
python scripts/step08_cohort_integrity.py
# Local recovery audit; source files are stored one directory above repo:
python scripts/step09_audit_recovery.py --files ../df_merged_age.parquet ../df_trinetx_total_young_wCT.parquet
# Reconcile the CT-retaining and legacy young-stroke tables:
python scripts/step10_reconcile_cohorts.py
# Audit original linked imaging/diagnosis dates before reconstruction:
python scripts/step11_event_linkage.py
# Compare provisional CT-index and advanced-imaging-index dates:
python scripts/step12_index_sensitivity.py
# Locate actual local source files before Step 13:
python scripts/step14_discover_sources.py --root .. --max-depth 4
# Better: original TriNetX archive is available; inspect it without extraction:
python scripts/step15_zip_inventory.py --zip "$TRINETX_ZIP"
# Step 16: inspect all ZIP headers and a bounded first-row sample:
python scripts/step16_zip_preflight.py --zip "$TRINETX_ZIP" --sample-rows 10000
# Confirm archive metadata and cohort scope before costly full scans:
python scripts/step17_zip_provenance.py --zip "$TRINETX_ZIP"
# Steps 18-21: set TRINETX_PRIVATE to owner-only approved storage OUTSIDE this repo.
# The following explicitly runs a smoke test THEN the large full scans.
# python -m pytest -q && \
# python scripts/step19_21_reconstruct.py --zip "$TRINETX_ZIP" \
#   --private-dir "$TRINETX_PRIVATE" --smoke \
#   --output results/phase1/chained_smoke_audit.json && \
# python scripts/step19_21_reconstruct.py --zip "$TRINETX_ZIP" \
#   --private-dir "$TRINETX_PRIVATE" --full --min-age 19 --max-age 50 \
#   --output results/phase1/chained_reconstruction_audit.json
# Step 13 requires original secure source paths (not intermediate cohorts):
# python scripts/step13_source_inventory.py --diagnoses PATH --procedures PATH --demographics PATH
```

### What each script does

| Script | Purpose | Local output |
| --- | --- | --- |
| `step01_audit.py` | Validate schema, missingness, imaging counts and patient uniqueness | `results/phase1/trinetx_audit.json` |
| `step02_prepare.py` | Restrict to common ages 19-50; derive **binary receipt**, procedure counts and vascular modality combinations | `results/phase1/cohort_age50.parquet` |
| `step03_describe.py` | Aggregate denominators and percentages by sex, race and ethnicity | `results/phase1/descriptive_age50.csv` |
| `step04_audit_nis.py` | Inspect previously published NIS summary CSV strata against manuscript values | `results/phase1/nis_stratum_audit.csv` and `.json` |
| `step05_missingness.py` | Evaluate selection associated with known/unknown race and ethnicity by sex/year | `results/phase1/missingness_age50.csv` |
| `step06_minimal_models.py` | **Preliminary** age/year-only binomial GLM and standardized sex risk differences | `results/phase1/minimal_models_age50.csv` |
| `step07_modality_patterns.py` | Descriptive, mutually exclusive CTA/MRA pathways by sex, year, and age bands | `results/phase1/modality_patterns_age50.csv` |
| `step08_cohort_integrity.py` | Critical selection check: detect absence of CT-only patients | `results/phase1/cohort_integrity_age50.json` |
| `step09_audit_recovery.py` | Audit local pre-exclusion Parquet candidates without sharing record-level data | `results/phase1/recovery_candidate_audit.json` |
| `step10_reconcile_cohorts.py` | Reconcile CT-inclusive and legacy derived young-stroke tables by aggregate patient overlap and imaging-count concordance | `results/phase1/cohort_reconciliation.json` |
| `step11_event_linkage.py` | Check event-date linkage, first imaging-linked diagnosis and discordance with saved tables (audit only) | `results/phase1/event_linkage_audit.json` |
| `step12_index_sensitivity.py` | Compare earliest any-imaging, CT-linked, and advanced-imaging-linked diagnosis dates (audit only) | `results/phase1/index_definition_audit.json` |
| `step14_discover_sources.py` | Identify likely original-source exports using only local CSV headers and Parquet metadata | `results/phase1/source_candidates.json` |
| `step15_zip_inventory.py` | Inventory an original local TriNetX ZIP from its central directory and CSV/TSV headers without extraction | `results/phase1/zip_source_inventory.json` |
| `step16_zip_preflight.py` | Inspect ZIP member headers and **first 10,000 rows only** of diagnosis, procedure and patient tables to validate formats | `results/phase1/zip_preflight.json` |
| `step17_zip_provenance.py` | Check ZIP manifest, dataset and cohort metadata without reading clinical rows | `results/phase1/zip_provenance.json` |
| `step18_diagnosis_index.py` | Build local private SQLite index of earliest 2018–19 principal I63 diagnosis directly from ZIP, independently of imaging; supports safe smoke mode | `results/phase1/step18_smoke_audit.json` or `step18_diagnosis_index_audit.json` (aggregate only) |
| `step19_21_reconstruct.py` | **Chained** demographic eligibility, original CPT date linkage and CT-only integrity audit using approved private SQLite indexes | `results/phase1/chained_reconstruction_audit.json` (aggregate only) |
| `step22_temporal_qc.py` | Read-only QC of completed reconstruction: ±0/1/3/7-day windows, CT-only partition, missingness and broad strata | `results/phase1/step22_temporal_qc.json` (aggregate only) |
| `step23_24_eligibility_qc.py` | Check reason for diagnosis-index exclusion and I63 code patterns across imaging classifications; scan only original `patient.csv` | `results/phase1/step23_24_eligibility_qc.json` (aggregate only) |
| `step25_readiness_gate.py` | Reconcile Steps 18–24 from aggregate JSON alone and list scientific gates blocking publication | `results/phase1/step25_readiness_gate.json` (aggregate only) |
| `step13_source_inventory.py` | Inspect original diagnosis, procedure and demographic source schemas and provisional code coverage (audit only) | `results/phase1/source_readiness.json` |

### How to interpret

These steps provide descriptive checks only. They **do not**
verify the original diagnosis date linkage, principal-diagnosis
eligibility, CT restriction, CPT code completeness, hospitalization
structure or NIS survey design. See [the Phase 1 audit guide](docs/PHASE1_AUDIT.md), [the initial results review](docs/PHASE1_RESULTS.md), [the missingness review](docs/MISSINGNESS_RESULTS.md), and [the preliminary model review](docs/STEP06_RESULTS.md) for discrepancies, unresolved questions and stop conditions.

The original sample used sex-specific <=52/<=54 age limits.
This saved derived dataset cannot support a true common <=55 analysis
or analysis of younger patients previously excluded. New source
extraction would be needed.

## Data governance

**Warning:** This repository is public and already includes a tracked
patient-level derived parquet file and notebook outputs with
pseudonymous identifiers and geography. TriNetX data may have
contractual distribution restrictions. Confirm institutional and
provider permissions promptly and assess whether tracked files
and Git history require remediation. The analysis scripts do not
write patient identifiers into audit summaries. Nevertheless, any
row-level derived output remains sensitive and is locally ignored
via `results/`; do not push it, publish it or attach it to issues.

## Development principles

- Preserve the original notebook and data unchanged for traceability.
- Do not hardcode manuscript values as replacement results.
- Validate schemas, inclusion criteria and missingness before modeling.
- Distinguish procedure **receipt** from procedure **counts**.
- Run scripts and tests before interpreting estimates.
- Produce all tables and figures with code acting on actual authorized data.
- Use pull requests to review methodological and code changes.

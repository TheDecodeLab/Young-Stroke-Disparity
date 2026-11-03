# Step 31: Completed expanded procedure scan and scientific feasibility

**Status:** Existing Diamond ZIP extraction completed under an
investigator-authorized, literature-reviewed *research-only* pathway.
NO admission validation, independent clinician sign-off or publication
inference authorization is implied.

## Aggregate engineering validation

The uploaded preflight and full extraction audit agree on codebook
SHA-256 and cohort size. The program scanned all **1,166,493,611**
procedure.csv records and reconciled the manifest. The
**86,902-person** approximate-age 19-50 principal-I63
diagnosis-first denominator is unchanged. All **97,872** historical
patient/modality/day imaging matches were retained. The new local
private database contains **121,033** distinct code-specific
patient/day records, whose uniqueness differs from the old count.
No source encounter IDs exist in this workflow.

## Primary +/-1-day temporal association window

| Recorded-code modality | Original 9 CPT | New 14 CPT, head only | New 14 CPT, head + neck |
| --- | ---: | ---: | ---: |
| CT head | 29,687 | 29,687 | 29,687 |
| Brain MRI | 24,464 | 24,464 | 24,464 |
| CTA | 15,372 | 15,372 | 15,799 |
| MRA | 6,880 | 7,261 | 7,780 |
| No included imaging code matched | 47,128 | 47,087 | 46,953 |
| **Any included imaging code matched** | **39,774** | **39,815** | **39,949** |

These are overlapping imaging-code modality indicators, NOT
confirmed imaging performed during a hospital encounter. All
columns share the same 86,902 patients.

Compared with the original code list, five new vascular CPT codes
and updated head MRA coverage increase the *number of patients
with any matched code* by only **175** under +/-1 day, or
**0.201 percentage points** of the total cohort.
**54.03% still have no matching included procedure code.**

## +/-7 day sensitivity

| Recorded-code measure | Historical 9 CPT | 14 CPT head + neck |
| --- | ---: | ---: |
| CTA code | 16,888 | 17,380 |
| MRA code | 7,921 | 8,970 |
| No included imaging code | 44,760 | 44,602 |
| At least one included imaging code | 42,142 | 42,300 |

At +/-7 days, the expansion adds 158 people with any included
code, **0.182 percentage points** of the same cohort.
**51.32% still have no matched included code**. The code expansion
improves observed vascular coding but does not explain the large
unmatched category.

## Feasibility decision

- The original imaging-selected cohort had a fatal CT-only
  exclusion problem; diagnosis-first reconstruction corrects
  that engineering flaw.
- Even after the extended CPT scan, missing-code capture,
  principal-diagnosis clinical validity and admissions remain
  unresolved. Absence of a CPT record is **NOT** no imaging.
- Race unknown/missing (77.90%) and ethnicity unknown/missing
  (75.39%) prohibit generalizing complete-case analyses as
  race/ethnicity access disparities.
- The defensible next direction is a **methods/data-quality
  study** of cohort selection and measurement sensitivity;
  a narrow recorded-code descriptive study is possible only
  with appropriate source-observation qualifications. Neither
  is approved for full clinical inference as of this document.
- No further billion-row scan is warranted from these results.

## Zero-source-scan Step 31 reconciliation

The new script checks the historical Step22 JSON against
the expanded Step30 JSON and preflight: codebook fingerprints,
source row count, denominator, preserved modality/day events,
head/neck nesting, all four time windows and nonoverlapping
code-recording classes. It reads *only aggregate JSONs*,
without opening the private SQLite or original Diamond ZIP.

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q && \
python scripts/step31_expanded_reconciliation.py \
  --preflight results/phase1/step30_literature_codebook_preflight.json \
  --expanded results/phase1/step30_literature_imaging_audit.json \
  --legacy-step22 results/phase1/step22_temporal_qc.json \
  --output results/phase1/step31_expanded_reconciliation.json
```

The Step28 source JSON key named
'approved_codebook_sha256' is a *fingerprint*, NOT an
independent physician/IRB approval. The recorded review basis
is published evidence only. ALL aggregate tables still need
cross-window/cross-report disclosure review before publication.

Only share institutionally reviewed aggregates. Retain the ZIP
and patient-level SQLite in authorized private storage outside
Git. Legacy patient-level Parquet in public Git history needs
institutional data-governance remediation.

**Status: manuscript inference remains blocked, draft PR unmerged.**

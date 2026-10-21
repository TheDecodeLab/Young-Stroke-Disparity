# Steps 23–25: eligibility, disclosure repair and readiness decisions

## Executed Step 25 result and important disclosure clarification

The study team ran the aggregate readiness gate and returned
`all_prior_aggregate_counts_reconciled: true`,
`ready_for_manuscript_inference: false`, zero ZIP records read,
and zero patient-level SQLite records read. The 962,351 diagnosis-index
and 86,902 age-eligible totals reconcile. This does **not** lift the
clinical/methodological hold.

The first version of Step 25 incorrectly returned
`historical_fine_diagnosis_group_report_requires_disclosure_review: false`
when the **current** Step 23-24 input was the repaired coarse report.
That boolean confused current reporting with the **earlier** report,
which suppressed a small I63 category without sufficient complementary
suppression. This has now been fixed to retain a persistent historical
review warning and separately expose the current input's suppression
status. The earlier Step 25 JSON should not be construed as authorizing
release of the old fine-grained report.

The actual scientific decisions are summarized in
[Step 26 clinical protocol review](STEP26_CLINICAL_PROTOCOL_DECISIONS.md).
Please do not launch additional billion-row scans or statistical models
before reviewing the study denominator, encounter availability,
clinical codebooks and missingness with collaborators.


## Validated aggregate findings

The local Steps 23–24 audit reconciles all **962,351** patients in the
principal ICD-10-CM I63 diagnosis index. The mutually exclusive eligibility
classification (with missing/invalid birth year first, then unrecognized sex)
is:

| Classification | Patients |
| --- | ---: |
| Age >50 | 771,843 |
| Missing or invalid birth year | 100,654 |
| Age <19 | 2,722 |
| Unrecognized sex, after birth-year exclusion | 230 |
| Age 19–50, recognized sex | 86,902 |
| **Total** | **962,351** |

The prior Step 19 reported 270 records with unrecognized sex **before
exclusion precedence**. The present 230 is a mutually exclusive reason
after assigning missing/invalid birth years first. They are not directly
interchangeable numbers.

I63.9 represents **61,057/86,902 (70.3%)** eligible indexed
patients. Nearly half of this diagnosis group have no matching imaging
using the nine historical CPT codes. Missing imaging is also prevalent
in other I63 categories, so it cannot be explained by I63.9 alone.

Unknown or missing race is **67,700/86,902 (77.9%)** and ethnicity is
**65,517/86,902 (75.4%)**. High missingness occurs in every imaging
classification. The 44,760 patients without matching CPT codes do not
necessarily lack clinical imaging; the source has no encounter ID and
the nine-code set is incomplete.

## Important disclosure correction

The original fine-grained I63-family report suppressed one very small
subgroup but included all other subgroup totals and the full denominator.
A reader could reconstruct the suppressed group size using subtraction.
**Do not share or commit that earlier JSON outside an authorized
disclosure-review process.**

The Steps 23–24 script now reports only two pooled groups:
`I63.9 family` and `Other I63 codes`. It withholds **both**
pooled groups when any positive cell is below 11, rather than
publishing all complementary counts. This is a risk-reduction measure,
not certification of disclosure safety; assess outputs across all
related released tables before publishing.

## Step 25: zero-source-scan readiness gate

`scripts/step25_readiness_gate.py` checks that the original
reconstruction, temporal sensitivity and eligibility audit all
reconcile. It opens only **three aggregate JSON files**, not private
SQLite databases, source records, or the original ZIP.

From the local repository root, use the **same** approved original
ZIP and private database directory as before:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q && \
python scripts/step23_24_eligibility_qc.py \
  --private-dir "$TRINETX_PRIVATE" \
  --zip "$TRINETX_ZIP" \
  --compare-step22 results/phase1/step22_temporal_qc.json \
  --output results/phase1/step23_24_eligibility_qc_v2.json && \
python scripts/step25_readiness_gate.py \
  --reconstruction results/phase1/chained_reconstruction_audit.json \
  --temporal results/phase1/step22_temporal_qc.json \
  --eligibility results/phase1/step23_24_eligibility_qc_v2.json \
  --output results/phase1/step25_readiness_gate.json
```

The only source member scanned again is `patient.csv`, about
311 MB uncompressed. No diagnosis/procedure billion-row rescans.
Review the new aggregate output for any remaining complementary
disclosure risk before sharing. Do not send raw clinical ZIP or
patient-level SQLite records.

## Blocking scientific decisions before another large source scan

1. **Target population:** Are we studying index *diagnoses*,
   CT-imaged stroke pathways, or verified ischemic-stroke
   **admissions**? With no encounter IDs, the current source cannot
   verify hospitalization or admission-level imaging.
2. **Clinical index codebook:** Which ICD-10-CM I63 subcodes, prior
   ICD-9 diagnoses, H34.1, pre-index exclusions, principal `P`
   definition and first-stroke lookback are clinically appropriate?
   Review with physician collaborators.
3. **Imaging definitions:** The historical nine CPT codes exclude
   CTA neck, MRA head/neck variants, other imaging billing codes
   and non-CPT coding systems. Approve a full modality codebook
   *before* an expensive second procedure scan.
4. **Data limitations:** Birth year is missing/invalid in 10.5% of
   the full diagnosis index; race and ethnicity are missing for
   over three-quarters of the age-eligible cohort. Review how this
   constrains selection and disparity modeling.
5. **Data use:** Review permission to redistribute earlier
   patient-level artifacts already tracked in the public repository
   and clean Git history if appropriate.

**A successful Step 25 is an engineering reconciliation, not
clinical validation or authorization to publish.** Keep the PR
in draft. Do not substitute these values for hospital imaging
utilization rates or effect estimates.

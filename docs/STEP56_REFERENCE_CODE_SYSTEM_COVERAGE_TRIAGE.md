# Step 56: Evidence-based imaging terminology coverage triage

**Status:** private reference-terminology analysis only. The workstation confirmed **481 tests passed, three known warnings** and Step55 completed on **3,270** reference terms. It located all **14/14** published core CPT modality codes; the status distribution was 3,240 non-CPT/unverified, 13 other CPT requiring research, 2 excluded and 1 separate CT-perfusion term.

**Scientific interpretation:** 3,240 *reference candidates* are not 3,240 actual Research Network procedure records, and do not imply that CPT coding is necessarily uncommon. The export's reference terminology may contain unused concepts; a procedure-row code-system distribution is unknown and cannot be inferred from this file. This distinction is essential to avoid calling a technically correct CPT core a *complete* imaging measurement.

The investigator confirmed that **2018–2019 applies to Diamond**, while Research Network's *proposed* index admission window starts in 2016 and ends at the last sufficiently complete observed calendar year, still requiring authorized source coverage assessment. Do not misstate the end year. Primary imaging remains same-IMP (A); provisional date-only ED plus IMP remains sensitivity-only (B).

## Code-mapping priorities

1. Keep the **exact CPT14** [published meaning registry](STEP54_PUBLIC_CPT14_LITERATURE_CODE_MEANING_REVIEW.csv) as the high-specificity Research Network core; code meaning does not establish a completed scan.
2. Independently inspect the **13 remaining CPT** terms with version-appropriate CMS/AMA coding evidence before deciding include/exclude/defer. Step56 makes a *small private queue*, preserving original reference descriptions and automated lexical category, so one can research the actual codes rather than speculate.
3. Count the **3,240 unverified non-CPT** *reference* terms by source code system and lexical category, locally. Only expand SNOMED, HCPCS or ICD-10-PCS with an exact, release-valid concept interpretation, patient-encounter recording semantics, and no orders/history/administrative-only concepts. Never infer performed imaging from text alone.
4. Before claiming completeness or interpreting racial/sex differences, a separately **authorized** actual procedure-row check will be needed for **code-system use rates, procedure date completeness, CPT14 observation rates and source/HCO coverage**. None has been performed or is approved by this step. Data-source capture differences can mimic disparities.

## One safe chained command

```bash
git pull --ff-only origin analysis-rebuild-phase1-audit
python -m pytest -q && python scripts/step56_reference_vocabulary_coverage_triage.py prepare
```

Step56 reads only the existing **Step46 private reference inventory** and **Step55 private literature-disposition files**. It checks the original Step46 inventory/status SHA-256 against Step55 provenance, reconciles every review ID, full entry counts and literature status distribution, and does not open the clinical ZIP or any patient/encounter/diagnosis/procedure source file.

It creates an owner-only directory within Git-ignored study results:

`results/phase1/full_reconstruction_private/imaging_review/literature_adjudication/coverage_triage/`

- `step56_reference_system_coverage_LOCAL_ONLY.json`: reference count distribution by code system, literature status and auto-candidate label; **not** patient or procedure frequencies.
- `step56_deferred_CPT_reference_queue_LOCAL_ONLY.csv`: focused *private* 13-CPT review queue with code, original reference meaning and explicit pending evidence fields.

The command prints only counts by code system and the number of deferred CPT entries. It does not print the private per-code descriptions to the terminal. It never overwrites existing review annotations. The output contains no patient identifiers, but terminology/code descriptions may still be license- or data-use-restricted. Do not upload these source-derived files to GitHub, email, or other unapproved systems.

Step56 **does not** modify the Step46 or Step47 review worksheet/signoff, Step45 codebook or any institutional approval flag, and **does not** re-enable the superseded clinical scan. Draft PR #1 must remain unmerged pending the preexisting potentially restricted Git-history review.

## Further validation required

The CPT14 code meanings are supported by the cited CMS coding materials in [Steps54–55](STEP54_55_LITERATURE_CODEBOOK_REVIEW_AND_RESEARCH_NETWORK_PERIOD.md). A true *performed-imaging* claim requires source validation of event meaning. A clinically complete imaging definition also requires an empirical assessment of available code systems and sensitivity definitions, including optional separately measured CT perfusion and (from 2026 onward, if covered) dual-site CPT 70471, not silent incorporation into the historical 14-code core. Both co-primary age populations remain independent.

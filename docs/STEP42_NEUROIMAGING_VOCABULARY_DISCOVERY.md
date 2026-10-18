# Step 42: Research Network neuroimaging vocabulary discovery

**Goal:** identify candidate MRI / CT / CTA / MRA codes for clinical review **before** scanning billion-row encounter, diagnosis, or procedure tables again. This is reference metadata work, not a clinical result.

## Findings prompting this step

The uploaded Step 41 technical report showed matching patient keys among observed encounter links, but no sampled provisional inpatient encounter contained *both* a recorded I63 diagnosis and an imaging CPT14 code in the three independent 50,000-row file prefixes. This does **not** imply that stroke patients lacked imaging, because corresponding rows can be located outside the unrelated truncated prefixes.

Research Network procedures include CPT, SNOMED and additional vocabularies. The historical CPT14 set is not a validated complete MRI/CTA/MRA ascertainment codebook.

## What is read

The script `scripts/step42_neuroimaging_vocabulary.py` streams **only** `standardized_terminology.csv` from the Research Network ZIP; it never reads clinical rows. Caps: 3,000,000 reference records and 20,000 discovered candidate entries. It matches tentative **MRI brain**, **MRA head/neck**, **CTA head/neck**, **CT head**, and ambiguous head/neck categories using explicit anatomical/technique terminology. The 14 historical CPT codes are included only as reference anchors. Discovery covers candidate CPT, HCPCS, SNOMED, ICD-9-CM, and ICD-10-PCS entries; other systems, local codes and synonyms could still be missed.

This is a **lexical candidate list**, requiring clinical review. The terminology reference is not evidence that a clinical procedure occurred, was completed, or is captured consistently across HCOs.

## Run locally

From the cloned repository:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step42_neuroimaging_vocabulary.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip"
```

Generated files live **only** in the repo's Git-ignored `results/phase1/`:

```text
step42_neuroimaging_codebook_LOCAL_ONLY.csv
step42_neuroimaging_vocabulary_status.json
step42_neuroimaging_vocabulary_status_REVIEW.zip
```

The **local CSV** contains raw terminology codes/descriptions, unapproved category suggestions and empty review fields. **Do not upload or commit it** without authorization. The review ZIP contains **only** aggregate status JSON, no codebook, patient identifiers or records. Outputs are mode 0600, and output paths outside the cloned repository are rejected.

## Next major study step

Review the private imaging codebook with a neurologist/neuroradiologist or imaging informaticist. Agree on what counts as recorded versus completed imaging and validate modality/anatomic coverage across all relevant procedure code systems. Then finalize, **before another full scan**, a single memory-bounded, private encounter-linked reconstruction:

1. Diagnosis-first, imaging-independent ICD-10-CM I63 eligibility with validated principal diagnosis position and 2018–2019 index dates
2. Clinically accepted inpatient encounter definition (IMP remains provisional) and validated encounter/patient/source key scope
3. Predeclared age rules, acknowledging that year of birth alone limits exact age
4. Same-encounter neuroimaging primary outcomes and clearly labeled ±7-day timing sensitivity checks
5. Race/ethnicity missingness, confounding, site/capture variability and institutional data governance

We must not estimate MRI utilization or clinical sex/race disparities from the Step 41 nonrandom prefixes. The public repository's historic patient-level TriNetX exposure remains unresolved. Keep PR #1 draft and unmerged.

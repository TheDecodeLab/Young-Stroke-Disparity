# Step 58: Approved-Workstation Technical Pilot (NOT Research Results)

**Investigator statement, 2026-10-18:** The Research Network dataset is already available under an **approved Penn State research protocol or data-use agreement covering this study**. Therefore the project does **not** require a new generic approval request merely to plan the analysis. This is an investigator attestation, **not** a copy of an IRB determination or a blanket authorization for data publication, sharing, code release or exceeding any agreement restrictions. Keep the formal approval and scope documentation in the approved institutional environment.

## Immediate analysis step

Use [the Step58 technical pilot](../scripts/step58_authorized_local_prefix_qa.py) to verify that the actual Research Network source archive still matches the prior metadata preflight and that real CSV field values can be parsed according to the anticipated schema. This is **different from the obsolete Step45 full cohort reconstruction**, which remains disabled.

The script reads a **maximum of 500 clinical rows per table by default** (hard cap 1,000) from patient, encounter, diagnosis and procedure tables; it does not extract the ZIP or publish rows. This is a **convenience prefix**, not a random or representative sample. A ZIP decompressor may internally buffer bytes, but the CSV parser processes at most the row cap per table.

No patient IDs, encounter IDs, actual procedure codes or free-text clinical descriptions go into the output. For diagnoses/procedures, it groups only known code-system labels (CPT/SNOMED/HCPCS/ICD-10-PCS/ICD-9-CM/other). For encounters, it groups `IMP`, `EMER` and other. Reports count missing expected fields, invalid ISO dates, CPT14 code-record hits within this bounded prefix, and any observed calendar years only as **prefix technical clues**. It does not establish source-wide imaging frequency, case ascertainment, site coverage, actual HCO linkage, completed-vs-ordered procedure meaning or the last complete year.

The script requires **an existing local Step36 metadata-only preflight** whose source table sizes/headers match the actual ZIP, plus a deliberate local-use acknowledgment. It writes only a private mode-0600 JSON to the Git-ignored owner-controlled `results/phase1/full_reconstruction_private/`, refusing to overwrite prior results and refusing external output destinations.

### Run on the Penn State workstation

```bash
git pull --ff-only origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step58_authorized_local_prefix_qa.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip" \
  --max-rows-per-table 500 \
  --acknowledge I_CONFIRM_APPROVED_LOCAL_BOUNDED_CLINICAL_QA
```

If the archive has been moved, substitute its current local path. The intended source is the **same original Research Network ZIP** used in Step36, not the Diamond source or a subset. The acknowledgment confirms the user is operating under their existing approval; it does **not** modify approval flags in any file.

This is **not a request to upload or paste the generated JSON**. The report derives from clinical source data and remains local unless a formal disclosure review allows sharing. The terminal prints only a status and private output path, not clinical counts. If the command fails, sharing the exception message is generally more appropriate than sharing source values, but review any errors for private identifiers first.

## What happens after the pilot

If the pilot parses successfully, the next scientific phase is an independently designed **bounded-memory, source-wide aggregate QA pipeline**, to run locally **only within the existing protocol's processing conditions**, not the superseded Step45 scanner. It will need whole-data annual encounter coverage, actual code-system usage in procedure records, date completeness, consistent patient/encounter ID scope, and an HCO/site identifier policy. Decisions about whether code records document performed care should follow source documentation; observing CPT14 terminology alone cannot settle them.

The year window is **Research Network proposed 2016 onward until the last validated complete full calendar year**, separate from **Diamond 2018–2019**. Maintain the primary A same-inpatient imaging definition and ED-inclusive B as a provisional date-only sensitivity. The two co-primary age definitions remain overlapping and must be analyzed separately.

Keep [the research plan](ACTIVE_RESEARCH_NETWORK_STUDY_PLAN.md), [coding source/citation register](references/IMAGING_CODE_CITATION_REGISTER.md) and [original technical/governance checklist](RESEARCH_NETWORK_PRE_RECONSTRUCTION_GATE.md) for scientific audit. The generic data-steward request is **optional**, to be used for any unresolved source semantics; it is not a new mandatory administrative prerequisite. PR #1 remains unmerged pending the separate historical repository privacy review.

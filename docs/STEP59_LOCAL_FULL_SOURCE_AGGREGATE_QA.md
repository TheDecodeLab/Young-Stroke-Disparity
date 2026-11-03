# Step 59: Local whole-table AGGREGATE QA (not cohort reconstruction)

> **Investigator status update, 2026-10-18:** The encounter, diagnosis and
> procedure stages all completed on the approved Penn State workstation.
> The three resulting files remain private. **Do not repeat scans** for
> Step60; use the [existing-report-only private review](STEP60_PRIVATE_SOURCE_QA_REVIEW.md).
> Completion does not validate calendar-year coverage, source codebook
> sensitivity, linkage or performed imaging.


**Current decision:** Step58 finished successfully on the investigator's approved Penn State workstation (reported 2026-10-18). No Step58 private clinical-derived report was shared or read in GitHub. The local repository previously passed **569 tests, 3 existing warnings** at commit `a9c5de4`.

The [Step59 script](../scripts/step59_full_source_aggregate_qa.py) is a **new, separately guarded, stage-by-stage streaming aggregate quality check**, NOT the superseded Step45 clinical reconstruction. It does not select patients, link encounters, compute sex/race imaging disparities, or establish that billed/recorded codes equal completed exams. It does not grant new approval. It may run only when the existing institutional protocol/DUA **actually permits the proposed local full-table aggregate QA**.

## Questions this stage can begin to answer

| Stage | Source input | Local-only aggregate counters | Important limitation |
|---|---|---|---|
| `encounter` | `encounter.csv` | Encounter rows by `start_date` calendar-year bucket; `IMP`/ `EMER`/other labels by year; missing start/end date and IDs | Does **not** validate hospitalizations, distinct patients, admission completeness, or HCO/site representation |
| `diagnosis` | `diagnosis.csv` | Diagnosis rows by service year, recognized code-system label and whether principal indicator is exactly `P`; missingness | Does **not** identify strokes or validate `P` clinically; no diagnosis codes in output |
| `procedure` | `procedure.csv` | Procedure rows by service year and code-system label; recorded CPT14, 70471, and CT perfusion code-row counts | Does **not** count studies/patients, validate performed vs ordered, connect procedures to stays, or prove CPT coverage is adequate |

The procedure stage is particularly relevant because the **reference vocabulary** contains many SNOMED entries, but their frequencies in *actual procedure records* were not known. Step59 counts actual **recorded source rows**; it still does not claim that a code means a scan was done.

The code recognizes dates from their first 10 ISO-8601 characters. It groups years before 2016, missing/invalid dates and post-current-year dates separately. A year with observed rows **does not imply** complete capture; the final Research Network end year **remains unknown** pending full-calendar-year and HCO participation review. Different tables have different grains, so never divide e.g. CPT code rows by hospitalization counts and call the result an imaging rate.

## Safeguards and execution cost

- Requires explicit `--stage`, local ZIP path and exact user-approved-use acknowledgment. If you cannot confirm your protocol/DUA covers a whole-table **aggregate** read, do not run Step59.
- Requires Step36 **metadata-only** preflight that matches the selected member size, header and, if available, manifest **row count**. It reads one entire CSV member per stage, checks completion, and only then writes the report.
- Uses streaming counters with memory bounded by predefined calendar years/code-system groups, and **does not retain patient IDs, encounter IDs, free text, individual code strings, records or source ZIP bytes**.
- Writes a new mode-0600 report under Git-ignored `results/phase1/full_reconstruction_private/source_wide_qa/`. Reports remain **clinical-derived private research data**, not approved for uploading to GitHub/ChatGPT. No overwrite.
- **A single stage can take hours/days on a very large ZIP**, particularly `procedure.csv`. There is no within-file resume or time estimate; do not run all stages concurrently. Interrupting a stage means that stage must be restarted from its beginning. Plan adequate local I/O access and workstation time before invoking.
- This **does not** change any `approvals_LOCAL_ONLY.json` or frozen codebook flags, does not touch the legacy Step45 full-scan CLI, and does not authorize publication or PR merging.

## First action: validate with synthetic tests (no real source read)

```bash
git pull --ff-only origin analysis-rebuild-phase1-audit
python -m pytest -q
```

Previously verified: 569 tests. With 12 new synthetic Step59 cases the expected total is **581**. Confirm locally before running even the first source stage.

## First real stage (only if whole-table aggregate QA is covered by your approval)

Run **encounter first**, and do not launch procedure/diagnosis until its successful completion and runtime are known:

```bash
python scripts/step59_full_source_aggregate_qa.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip" \
  --stage encounter \
  --acknowledge I_CONFIRM_EXISTING_PROTOCOL_PERMITS_LOCAL_FULL_SOURCE_AGGREGATE_QA
```

Use the same Research Network archive that passed Step36/Step58, not Diamond. The script prints only stage completion and private report location, not clinical numbers. **Do not share or paste the private report.** You can report merely whether the command succeeded, runtime, or a reviewed non-identifying exception/status.

After local review and resource planning, the other two stages can be invoked separately with `--stage diagnosis` and `--stage procedure`, using the same explicit acknowledgment. No patient source data are sent to this assistant. Wait to choose a final study year or run models until clinical coding, encounter/HCO scope and ascertainment have been independently validated.

## Next research decision after QA

Analyze whether the calendar-year differences or coding-system changes make the proposed 2016+ period and CPT14 code-only ascertainment scientifically defensible; separately review HCO/episode provenance and what a procedure record means. The two overlapping co-primary age cohorts, A same-IMP primary and B provisional ED-inclusive sensitivity are unchanged.

Relevant documents: [active plan](ACTIVE_RESEARCH_NETWORK_STUDY_PLAN.md), [code-to-reference crosswalk](references/CODE_TO_REFERENCE_CROSSWALK.csv), and [clinical data semantics checklist](RESEARCH_NETWORK_PRE_RECONSTRUCTION_GATE.md). Draft PR #1 remains unmerged while historic Git data governance is unresolved.

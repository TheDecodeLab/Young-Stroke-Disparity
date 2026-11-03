# Step 63: LOCAL ONLY ED-to-inpatient encounter feasibility

**Status:** Synthetic-only code pending investigator workstation verification.
This is an extension of the active Research Network study plan, **not**
a reinterpretation or modification of Step 62. This first phase runs an
encounter scan and a database-only linkage step. **It does not scan ED
procedures, estimate imaging use, establish transfer continuity, infer
HCO identity, or calculate health disparities.**

## Why

Step 62's primary recorded-code outcome is deliberately limited to 14
CPT codes from the same inpatient encounter during its start/end dates.
The approved sensitivity B asks whether a *different* emergency
encounter ending zero or one calendar days before inpatient start could
plausibly contain additional imaging records. Source-wide EMER/IMP
counts establish only the existence of records, not linked episodes.

In Step 63, **the index admission denominator remains frozen from
completed Step 62**. Imaging availability never determines ED selection.

## Encounter and uniqueness contract

- Use only patients indexed in either Step 62 age cohort, while reading
  **every** row from the source encounter table to identify their
  EMER and IMP encounters. Retain all eligible IMP candidates belonging
  to these patients, not just the selected index IMP. Source-year
  filtering is not applied to the ED precursor, so a 2015-12-31 ED
  ending before a 2016-01-01 index is not accidentally excluded.
- Require matching patient, different ED and IMP encounter IDs,
  `type=EMER` versus `type=IMP`, valid start/end dates and
  ED end <= IMP start <= ED end + 1 **calendar day**. This is a
  **date-only candidate relationship**; no HCO/site/transfer assertion.
- Quarantine a patient/encounter key if relevant EMER/IMP duplicate
  rows disagree on type or dates, or have malformed/missing/reversed
  dates. An excluded key can never re-enter from a later duplicate row.
  Rows of other encounter types are **not exhaustively examined for
  type collisions**, an explicit limitation.
- Require **reciprocal uniqueness** of the candidate pair against all
  retained EMER and IMP encounters of the indexed patients: a
  candidate ED must link to just one IMP and the selected index IMP
  must link to just one ED. Reject ambiguous competing EDs or
  competing non-index IMPs, even where one candidate appears favorable.
- Before linking, check every Step 62 index key against the retained
  Step 63 encounter subset. A retained index key with discordant type/dates
  is a **fatal integrity error**. An index key missing **without documented
  quarantine** is also a fatal error. However, an indexed key missing
  because Step 63 quarantined it is **unassessable for ED sensitivity**;
  never silently drop the patient from Step 62 or call ED imaging absent.
- Because an ambiguous EMER/IMP source key anywhere within an indexed
  patient's encounters could conceal a competing ED or IMP, the **strict
  reciprocal-uniqueness feasibility subset excludes the entire patient
  whenever ANY encounter key was quarantined**, even if the index key
  itself is retained. Such patients remain in the original Step 62
  denominators and are explicitly counted as ED-linkage-unassessable.
  This is conservative and may exclude substantially more than the
  directly quarantined index keys. We report both counts and the
  restricted *evaluable* denominator, including distributions by
  admission year and the unvalidated `P` label. No zero/absent ED
  link in this feasibility report proves that imaging was not performed.
  Quarantine reasons were not individually retained during the V1
  encounter pass, so its causes cannot be decomposed without further
  source investigation.
- Store the source's `derived_by_TriNetX` and start/end derived fields
  as **uninterpreted private strings** for later review. Disagreement
  in duplicate provenance flags is marked `MIXED`. The columns' value
  semantics are not presumed. **Do not interpret `source_id` as HCO**.
- Neither the absence of a unique link nor the absence of recorded CPT
  codes means no ED care or no imaging; incomplete coding and source
  coverage are unresolved.

## Provenance, checkpointing and privacy

Script: [`scripts/step63_ed_encounter_feasibility.py`](../scripts/step63_ed_encounter_feasibility.py)

Synthetic tests:
[`tests/test_step63_ed_encounter_feasibility.py`](../tests/test_step63_ed_encounter_feasibility.py)

Step 63 opens the **completed Step 62 SQLite read-only** and copies
the frozen index memberships to a separate private SQLite database.
It verifies the Step 62 metadata/file snapshot and the Step 36 ZIP
fingerprint on each invocation. The stage rejects changes to either.
The exclusive writer lock, owner-only private directory/database and
atomic row-count checkpoints follow Step 62's protections. A crashed
encounter stage resumes by skipping already committed source CSV rows.
This still decompresses the preceding ZIP bytes, not random access.

Only these two outputs are generated, inside the cloned repo's existing
Git-ignored private results subtree:

`results/phase1/full_reconstruction_private/step63_ed_sensitivity_private/step63_ed_feasibility_LOCAL_ONLY.sqlite`

`results/phase1/full_reconstruction_private/step63_ed_sensitivity_private/step63_ed_feasibility_LOCAL_ONLY.json`

**Neither output may be committed to GitHub or shared without the
applicable institutional data-use and disclosure review.** The JSON
contains aggregates without person/encounter IDs, but is not a
privacy-cleared disclosure artifact.

## Execution (one step at a time)

First pull code and run both synthetic-only test modules and the full
suite. If any test fails, **do not scan the clinical ZIP**:

```bash
git pull --ff-only origin analysis-rebuild-phase1-audit
python -m py_compile scripts/step63_ed_encounter_feasibility.py
python -m pytest -q tests/test_step62_checkpointed_cohort.py tests/test_step63_ed_encounter_feasibility.py
python -m pytest -q
```

After passing tests, **encounter scan** on the authorized workstation:

```bash
python scripts/step63_ed_encounter_feasibility.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip" \
  --stage encounter \
  --acknowledge I_CONFIRM_EXISTING_PROTOCOL_PERMITS_LOCAL_COHORT_RECONSTRUCTION
```

Inspect successful completion/reconciliation against the full Step 36
encounter manifest. The output is **not** a clinical result.

Only then run **database-only candidate-link evaluation**:

```bash
python scripts/step63_ed_encounter_feasibility.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip" \
  --stage link \
  --acknowledge I_CONFIRM_EXISTING_PROTOCOL_PERMITS_LOCAL_COHORT_RECONSTRUCTION
```

The link stage creates the local-only aggregate report; it does not
read all encounter records again. Check the **original indexed cohort
denominators**, index-key quarantines, patient-level holds caused by
ANY ambiguous encounter, restricted evaluable denominators, uniquely
linked ED encounters, by-year and by-`P` attrition, and retained event
records. If links are rare or source flags call reliability into
question, stop rather than launching another large procedure scan.

**Actual Step63 encounter checkpoint (2026-10-19):** The
authorized workstation completed the encounter scan and all local
synthetic tests passed. It also detected a nontrivial number of
quarantined encounter keys, including some Step62 index keys.
**Specific source-derived aggregate counts remain LOCAL ONLY** and
must not be placed in this GitHub document without disclosure approval.
The completed V1 Step63 database and encounter checkpoint are
preserved. The revised **link-only** policy evaluates unambiguous
patients without repeating the encounter source; it excludes indexed
patients with any quarantined encounter key from the strict
reciprocal-uniqueness *evaluable* subset and audits this attrition.
Its actual link yield has not yet been verified on the workstation.

**Future stage, not yet implemented:** Only if encounter feasibility
passes its scientific review, implement a separate checkpointed ED
procedure scan for the uniquely linked ED encounters, with date-bounded
CPT14 events and frozen primary inpatient capture comparisons by
cohort, year and the unvalidated P label. Verify any improvement as
*recorded-code capture*, not performed imaging. A second pass over the
procedure CSV must be justified by the observed unique-link yield.

Never rerun completed Step 62 stages or the disabled Step 45 scanner.

# Young Stroke Neuroimaging: Reproducibility and Re-analysis

This repository supports an observational study of brain MRI and vascular
imaging selection among adults hospitalized with early-onset ischemic stroke.
The prior notebook `disparity_young-claen.ipynb` remains **unchanged as the
legacy reference**. New work uses documented, tested Python scripts.

## CURRENT ACTION: Evidence-mapping coverage triage (Step 56)

The workstation confirmed **481 passed, three nonblocking warnings**.
Step55 classified **3,270 reference terminology candidates**:
**14 exact CPT core codes (all 14 located)**, **13 other CPT codes**,
**3,240 non-CPT/unverified entries**, **2 excluded terms**, and **1 separate
CT-perfusion term**.

These are **reference terminology counts, not procedure-record frequencies**.
We cannot know whether CPT14 captures most or few recorded imaging events
until an independent, institution-authorized procedure-row code-system and
date-completeness assessment. Literature validates code *meaning*, not whether
a given source record is a *performed examination*.

[Step56](docs/STEP56_REFERENCE_CODE_SYSTEM_COVERAGE_TRIAGE.md) creates a
small **private 13-CPT follow-up queue** and local aggregate reference
system/status breakdown, reconciling Step46/55 source fingerprints.
It neither opens the Research Network ZIP nor reads any patient-level
clinical tables.

```bash
git pull --ff-only origin analysis-rebuild-phase1-audit
python -m pytest -q && python scripts/step56_reference_vocabulary_coverage_triage.py prepare
```

It writes owner-only files under ignored
`results/phase1/full_reconstruction_private/imaging_review/literature_adjudication/coverage_triage/`
and does **not** rewrite any existing reviewer worksheets, approved codebook,
institutional authorization or scan guards.

The CPT14 historical code core remains high-specificity, but broader SNOMED,
HCPCS and ICD-10-PCS reference code mappings are **deferred**, not asserted
absent. Research Network's proposed **2016 onward** cohort period is
coverage-dependent and does not inherit Diamond's fixed **2018–2019**
interval. Primary A same-inpatient imaging and B date-only ED-inclusive
sensitivity remain unchanged. Draft PR #1 remains unmerged.

## CURRENT ACTION: Literature-reviewed imaging code definitions (Steps 54–55)

**Investigator correction:** **2018–2019 applies to Diamond, not the
Research Network.** We propose Research Network `IMP` index admissions
from **2016-01-01 through the last sufficiently complete observed
calendar year**, to be finalized after authorized source-coverage QA.
No end year is assumed from the ZIP creation date.

The previous 49-code priority sheet and the full 3,270-entry
terminology inventory are **reference candidates**, not validated
completed clinical imaging. I reviewed authoritative CMS coding sources
and committed a [14-code exact-CPT evidence registry](scripts/step54_literature_imaging_registry.py)
and [literature/period protocol](docs/STEP54_55_LITERATURE_CODEBOOK_REVIEW_AND_RESEARCH_NETWORK_PERIOD.md),
plus the [public evidence-coded 14-row CSV](docs/STEP54_PUBLIC_CPT14_LITERATURE_CODE_MEANING_REVIEW.csv).
A [private reference-inventory matcher](scripts/step55_private_literature_codebook_review.py)
classifies ALL locally prepared Step46 candidate rows against the evidence,
without reading any patient/encounter/diagnosis/procedure rows and without
requiring manual classification of thousands of lexical candidates.

Exact CPT codes: CT head `70450/70460/70470` (comparator);
CTA head `70496`; CTA neck `70498`;
MRA head `70544/70545/70546`; MRA neck `70547/70548/70549`;
MRI brain `70551/70552/70553`. Other code systems remain
**deferred** until an exact source-backed mapping is available, not
automatically considered absent imaging. CPT `70471` for combined
head+neck CTA is 2026-only, and CT perfusion has separate 2026 coding
changes; neither is silently counted into the historical CPT14 core.

```bash
git pull --ff-only origin analysis-rebuild-phase1-audit
python -m pytest -q && python scripts/step55_private_literature_codebook_review.py prepare
```

This command uses the existing **private** Step46 reference inventory,
not the original Research Network ZIP. It writes **new** owner-only
literature recommendations under
`results/phase1/full_reconstruction_private/imaging_review/literature_adjudication/`.
It does **not** modify existing codebook/signoff/approval files, claim
Research Network performed-care validation or enable the superseded
Step45 full clinical scan. The old Step47 `valid_for_2018_2019`
signoff is not a valid Research Network all-years workflow. For the
manuscript describe *recorded imaging codes*, not proven receipt.

The user-confirmed outcome A same-IMP **primary** and date-linked
ED-inclusive B **sensitivity** remain unchanged; both co-primary
age cohorts remain independent. Draft PR #1 remains unmerged pending
the historical research-data Git governance issue.

## Current implementation: Step53 synthetic outcome routing

The investigator's Step52 update has now been **validated locally** at
`557a8ab`: **415 passed, three unchanged nonblocking warnings**.
[Step53 reconstruction outcome contract](docs/STEP53_RECONSTRUCTION_OUTCOME_ROUTING_CONTRACT.md)
and a [pure in-memory reference assembler](scripts/step53_outcome_reference_assembler.py)
with [synthetic tests](tests/test_step53_outcome_reference_assembler.py)
show how to preserve the agreed primary A same-inpatient-encounter
outcome separately from provisional ED-inclusive sensitivity B at
maximum ED→IP date gaps 0, 1 and 2 calendar days.

**This is NOT a replacement full clinical-data extraction pipeline.**
It takes already selected synthetic index admissions and events labeled
reviewed-performed by a caller. It cannot approve source codes, dates,
site identifiers or actual medical care. Both overlapping co-primary age
definitions remain distinct, and the original Step45 full-source scan
is still disabled.

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
```

Do not run real-data scans or set local approval flags. The next
material dependency is **independent clinical imaging-codebook review
and data-owner authorization**, followed by a governed implementation
of the full bounded-memory reconstruction. PR #1 remains draft and
unmerged pending the historical restricted-data review.

## Investigator-confirmed analysis priority (2026-10-18)

The investigator approved the final **relative role** of the imaging definitions:

- **A = PRIMARY:** documented imaging coded to the same index inpatient
  (`IMP`) encounter. This is a narrow capture definition; it can miss imaging
  performed before inpatient admission.
- **B = SENSITIVITY:** A plus imaging coded to a single, reciprocally unique,
  same-patient, date-adjacent emergency (`EMER`) encounter. The proposed
  ED end-date → IP start-date window is 0–1 **calendar days**. It is an
  **unverified date-only association**, not proof of the same hospital.
- **Additional sensitivity:** vary the ED→IP maximum gap across 0, 1 and
  2 calendar days, and transparently report excluded/ambiguous candidates.

Apply the same outcome priorities to **both co-primary age cohorts**
(`uniform_18_50`, `original_sex_specific_18_52_54`). Define the
hospitalized stroke denominator independently of imaging availability,
and describe outcomes as **documented imaging codes**, not confirmed
procedures or evidence that absent coding means absent care.

The decision is now frozen for development in
[`investigator_analysis_contract()`](scripts/step52_date_only_ed_ip_sensitivity.py),
covered by [synthetic tests](tests/test_step52_date_only_ed_ip_sensitivity.py),
and recorded in the [Step52 protocol](docs/STEP52_NO_HCO_DATE_ONLY_ED_IP_SENSITIVITY.md).

**No investigator decision can substitute for clinical codebook validation,
data-owner approval, or governance of restricted records.** The previous
Step45 full clinical-data scan remains hard blocked. No actual patient data
were used to implement this decision; draft PR #1 stays unmerged.

To verify the new test cases:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
```

## Current study-design status: no verified exported hospital/episode key (Step 52)

The operator confirmed **381 passing tests** and Step51 checked all **18 CSV
table headers**. The only broadly present candidate-like field was
`source_id`, whose HCO/site meaning is **unknown**. Oncology
`tumor_site_code` is not a hospital identifier. No explicit
HCO/hospital or parent-episode key was found in the exported headers.

[Step52 protocol](docs/STEP52_NO_HCO_DATE_ONLY_ED_IP_SENSITIVITY.md),
[pure provisional date-only resolver](scripts/step52_date_only_ed_ip_sensitivity.py),
and [synthetic-only tests](tests/test_step52_date_only_ed_ip_sensitivity.py)
have been added. They separate:
- **same-`IMP` imaging** (inpatient-encounter reference, may miss ED scans),
- **ED + IMP date-only sensitivity** (same patient, unique candidate ED whose
  end date is 0–1 calendar days before IP start), and
- **0-day and 0–2-day** ED-link windows as sensitivity variants.

No match is a verified transfer/same-hospital episode. **A PRIMARY and
B SENSITIVITY are now investigator-confirmed** (see the top of this README);
clinical/data-steward codebook and data-use reviews remain outstanding.
Step52 does not change the two co-primary age definitions or auto-approve
the imaging codebook.

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
```

**Do not rerun Step51 or execute the old Step45 clinical scan.**
No clinical data have been read for this step. Site/key semantics and local
full-data processing authorizations are still needed. Draft PR #1 stays
unmerged pending institutional governance review.

## Current local action: look for a site/episode key in OTHER tables (Step 51)

The workstation confirmed **364 tests passed** and Step50's existing Step36
encounter-table headers show **no explicit HCO/parent-episode field**.
This does **not** mean ED→inpatient date matching is impossible, but it
prevents claiming verified same-hospital episode linkage.

[Step51](docs/STEP51_ALL_TABLE_HEADER_LINKAGE_SEARCH.md) inspects the CSV
**header line only** from every table in the same existing local ZIP and
compares core tables with the Step36 saved schema/size metadata. No
clinical rows are parsed, extracted, linked or written to output.
It creates one owner-only private status JSON in the cloned repository's
ignored `results/phase1/full_reconstruction_private/site_linkage_review/`.

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q && \
python scripts/step51_all_csv_header_linkage_search.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip"
```

This is header-only work with the ZIP, **not** a full clinical scan.
No source `source_id` is presumed an HCO identifier. Any column-name hint
requires clinical/data-steward semantics verification. If no useful
column exists, consider a documented **date-only sensitivity** rather
than automatically asserting same-hospital care. The original Step45
full clinical scan is still blocked and PR #1 stays draft.

## Current local action: hospital/site-key structural review (Step 50)

After the operator confirmed **352 passing tests**, the next blocker is not
date arithmetic but the meaning of HCO/site and episode identifiers in the
export. [Step50](docs/STEP50_SITE_LINKAGE_METADATA_CHECK.md) uses the
previously generated **Step36 metadata JSON** (column headers only) and
creates a private site/episode field report and blank data-steward worksheet.
It does **not** open the original ZIP, read patient/encounter/diagnosis or
procedure rows, or assert that a `source_id` is a hospital key.

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q && python scripts/step50_site_linkage_metadata_check.py
```

Outputs remain within the local cloned repository's Git-ignored
`results/phase1/full_reconstruction_private/site_linkage_review/`.
This is **not** a site-linkage validation, clinical sign-off or authorization
for a source-wide scan. The original Step45 full clinical scan is still
explicitly blocked. Keep draft PR #1 unmerged pending restricted-data
governance review.

## Current implementation: ED-end-date → inpatient-start-date candidates (Step 49)

The study now has a [Step49 pure ED/IP encounter resolver](scripts/step49_ed_ip_episode_candidates.py),
[synthetic-only tests](tests/test_step49_ed_ip_episode_candidates.py),
and [complete safety/quality documentation](docs/STEP49_ED_IP_END_DATE_LINKAGE.md).
The existing Step48 `ed_to_ip_candidate` helper delegates to this revised rule.

**Proposed main temporal match:** same `patient_id`, independently
verified same HCO/site, different ED (`EMER`) and inpatient (`IMP`)
encounter IDs, and `IMP.start_date - ED.end_date` of **0–1 calendar days**.
Compare **same-day (0)** and **0–2 days** as sensitivity scenarios.
`ED.start_date` can be much earlier if the ED visit continues until
admission. Day-only dates cannot prove the within-day order of care.

Do **not** automatically attach multiple candidate EDs to an admission,
assign one ED to multiple IP stays, impute HCO/site from `source_id`,
or turn a candidate date match into a proven hospital transfer. The
resolver holds these ambiguities, missing dates/site, cross-site
transfers, and duplicate/colliding encounter IDs.

The quality-summary function returns only in-memory aggregate counts
for locally governed inspection, not disclosure-cleared outputs;
no patient rows/identifiers are written to files.

To verify this commit on the study workstation:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
```

**Step45 real-data execution REMAINS DISABLED.** A patient-level
site/linkage validation using institutionally authorized data and
a revised full-cohort algorithm are required before any source scan.

## Current study definition: literature-backed stroke and ED-to-IP reconstruction (Step 48)

The investigator has clarified that neuroimaging code definitions should be
defensible from literature/authoritative coding resources; the study needs
imaging sensitivity analyses; and imaging done during the **emergency visit
before an inpatient admission** must be included in that inpatient episode.
The user-supplied stroke code families include **ICD-9 433.x1/434.x1**,
**ICD-10-CM I63 family**, and **H34.1**, with a retinal subgroup and
cerebral-only sensitivity analysis so definitions are transparent.
We retain **both co-primary age cohorts** defined previously.

A [reviewable Step48 protocol with scientific references](docs/STEP48_STROKE_CODES_ED_TO_INPATIENT_PROTOCOL.md)
and synthetic-only [code-family/ED-IMP candidate helpers](scripts/step48_reference_stroke_ed_policy.py)
and [tests](tests/test_step48_reference_stroke_ed_policy.py) are now committed.
No source ZIP or patient records were read for Step48.

**IMPORTANT: Step45 source-wide clinical execution is deliberately
disabled**. Its previous principal-I63-and-same-inpatient-encounter
behavior is incompatible with ED-before-IP imaging and the revised
code families. Its metadata `--zip` plan and synthetic tests still work.
Step48 *does not yet implement* the complete source-wide ED-to-IP
episode builder. Do not set approvals to true or attempt the Step45
real-data stage flags. The next task is completing that implementation
and validating hospital/site linkage before any real-data source scan.

The previously prepared 49-code review subset and 3,270-term private
inventory remain **unapproved reference candidates** under
`results/phase1/full_reconstruction_private/imaging_review/`.
Reviewed high-specificity CPT codes and broader multi-system sets can
be compared as prespecified imaging sensitivity definitions; literature
alone does not guarantee that a TriNetX procedure record means an exam
was actually performed.

## Current action: one bundled clinical imaging review (Steps 46–47)

To reduce back-and-forth, use the
[chained Step46–47 reviewer workflow](docs/STEP46_47_CHAINED_IMAGING_CLINICAL_REVIEW.md).
It joins the already generated **Step42 reference candidates** to a
private first-review packet for the study neurologist/neuroradiologist
and a complete companion reference inventory.

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q && python scripts/step46_47_imaging_review_bundle.py prepare
```

**PREPARE ONLY:** no patient, encounter, diagnosis or procedure rows read;
no original source ZIP scan; no code approved; no changes to Step45
`approvals_LOCAL_ONLY.json` or its empty `imaging_codebook_APPROVED_LOCAL_ONLY.csv`.

Everything generated remains in the cloned repository's Git-ignored
`results/phase1/full_reconstruction_private/imaging_review/`, including
the full code inventory, focused clinician worksheet, review guide and
FALSE signoff template. Keep these reference and review files private.
The packet is not a codebook approved for real-data analysis.

When a clinician has reviewed the codes AND the complete codebook
scope and signed off explicitly, the same script has a separate
`finalize` mode that can translate **only reviewer-included performed
codes** into the existing Step45 codebook format. It refuses unsigned
or unsupported entries and never flips institutional approval flags.
**Do not run finalize until a real clinical sign-off.** PR remains
draft/unmerged pending institutional data governance review.

## Current implementation: guarded full-cohort extraction (Step 45)

The study now uses **TWO PARALLEL CO-PRIMARY age definitions**:

- **Uniform**: ages 18–50 for all sexes
- **Original sex-specific**: males 18–52, females 18–54

Neither definition is a secondary sensitivity. Due to year-of-birth-only
data, boundary-uncertain ages are excluded from the conservative
primary extracts and reported separately in local diagnostics.
Each patient can appear in both overlapping primary cohorts.

The [guarded Step 45 pipeline](docs/STEP45_GUARDED_FULL_RECONSTRUCTION.md)
has been implemented in `scripts/step45_full_cohort_reconstruction.py`,
with synthetic-only tests. It is a disk-backed, staged **diagnosis → encounter
→ patient → index → procedure → report** reconstruction. It is
imaging-independent at cohort definition, uses a reviewed codebook for
imaging flags, and retains all patient-level stages **only in the clone's
Git-ignored `results/phase1/full_reconstruction_private/`**.

**NO FULL SOURCE SCAN HAS BEEN EXECUTED.** Without `--stage` and
separate full-scan confirmation plus locally recorded authorizations,
the script only inspects ZIP metadata. To check the safe plan:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step45_full_cohort_reconstruction.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip"
```

Clinical inpatient/principal-diagnosis semantics, YOB boundary policy,
source ID meaning, imaging codebook and data-use/storage permissions
must be signed off before issuing full-scan flags. The code does not
grant these approvals automatically. This is a guarded technical
reconstruction, **not** a ready clinical disparity model. Draft PR #1
remains unmerged because public Git history carries unresolved
TriNetX data-governance concerns.

## Current decision: finish protocol and prepare full-cohort extraction

[Step 44](docs/STEP44_ANATOMY_AMBIGUITY_REVIEW.md) established that
the unresolved mixed head/neck terminology is **mixed in the code
descriptions themselves**, not an artifact of inherited reference paths.
Additional keyword triage will not validate those clinical concepts.

We are **stopping the repeated nonrepresentative sampling/terminology
steps**. The next substantive work is the
[Phase 1 full-cohort reconstruction specification
(draft)](docs/PHASE1_FULL_COHORT_RECONSTRUCTION_SPEC_DRAFT.md):
a diagnosis-first, imaging-independent I63 candidate set, validated
inpatient encounter linkage, demographics/age eligibility and one
controlled complete procedure scan using a clinician-reviewed codebook.
It explicitly requires source-size/storage planning, disclosure-safe
local staging, clinical meaning of inpatient/principal-diagnosis flags
and local data-owner approval before execution.

No further full-source clinical scan is authorized by the current
prefix audits. All eventual generated stage files and aggregate reports
must stay **inside this clone's ignored `results/phase1/`**; never
commit or upload patient-level records. PR #1 remains draft pending
governance review.

## Current action: distinguish terminology-path ambiguity (Step 44)

The Step43 aggregate report preserved every candidate, but its
triage placed the ambiguous terminology in one large mixed
head/neck bucket. That is still **too crude for clinical review**:
an inherited reference path may mention head and neck even when
the actual code description specifies only one region.

Run [Step44](docs/STEP44_ANATOMY_AMBIGUITY_REVIEW.md) to split this
review workload into technical groups based on **description-only
versus reference-path** anatomy matches. This reads only the
existing private Step43 worksheet and its local aggregate JSON.
It **does not read any clinical or original Research Network files**,
does not reclassify approved outcomes, and does not delete codes.

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step44_anatomy_ambiguity_review.py
```

A full private ambiguity worksheet, smaller first-review worksheet,
and aggregate-only status ZIP are written **only** into the clone's
gitignored `results/phase1/`. Do not share the LOCAL_ONLY CSVs.
The inpatient definition and clinical neuroimaging codebook still
require substantive review before any full cohort reconstruction.

## Current action: prioritize neuroimaging reference code review (Step 43)

The Step42 reference-only audit found a large candidate vocabulary,
including ambiguous anatomy and potentially nonprocedure terms. Its
results are **not evidence that the coded clinical procedure occurred**.
Before another very large source scan, use the
[Step43 triage guide](docs/STEP43_NEUROIMAGING_REVIEW_TRIAGE.md) to
produce a complete PRIVATE candidate review list and a small,
balanced first-review subset, with no automated inclusion decisions.

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step43_neuroimaging_review_triage.py
```

This step reads only the existing local Step42 CSV and status report,
**zero clinical records**. It stores all outputs in the cloned
repository's ignored `results/phase1/`: two LOCAL-ONLY codebook CSVs
and an aggregate-only status JSON/ZIP. **Do not upload the CSVs.**
The command refuses to overwrite an existing review worksheet
without explicit `--overwrite`.

The encounter `IMP` meaning, diagnosis-first index, complete
neuroimaging codebook, and site/source capture all still require
clinical/data-steward validation before a single well-planned
private inpatient stroke cohort extraction.

## Next step: neuroimaging vocabulary review (Step 42)

The Step41 **nonrandom file-prefix** pilot found that encounter-link
checks are technically feasible, but independent diagnosis and procedure
prefixes cannot establish actual stroke-neuroimaging co-occurrence.
The pilot is **not an imaging-utilization estimate** or evidence that
stroke patients went without neuroimaging.

Before a huge encounter-linked source scan, use the [Step42
reference-only vocabulary audit](docs/STEP42_NEUROIMAGING_VOCABULARY_DISCOVERY.md)
to discover candidate CT/MRI/CTA/MRA terminology across CPT, SNOMED,
HCPCS and other procedure systems. It reads no clinical rows.
Its private, unapproved CSV codebook must stay in gitignored
`results/phase1/`; an independent aggregate-only review ZIP can be
shared only after institutional disclosure review.

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step42_neuroimaging_vocabulary.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip"
```

Once the codebook, inpatient criteria and diagnosis index are reviewed,
design a **single efficient, private full-source reconstruction**, rather
than another sequence of unrelated event-prefix scans. The draft PR
remains unmerged pending data governance review.

## Technical next step: provisional inpatient event concordance (Step 41)

Step 40 status confirmed that the codebook worksheet's clinical decision
cells are still blank. We will **not** treat lexical candidates as
approved inpatient definitions. The shared reference terminology makes
a strict inpatient candidate available for a *bounded technical-only*
pilot, while unclassified encounter types remain unknown.

Run [Step41](docs/STEP41_PROVISIONAL_INPATIENT_CONCORDANCE.md) to
examine whether diagnosis and procedure prefixes share encounter and
patient keys with sampled candidate inpatient encounters, and whether
recorded I63 and selected CPT imaging codes align in time. Its
nonrandom-prefix technical counts are **not** cohort estimates or
evidence of imaging utilization.

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step41_provisional_inpatient_concordance.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip"
```

The bounded script writes only aggregate JSON plus a review ZIP inside
the repo's gitignored `results/phase1/`. Clinical codebook review
and source linkage validation are still required before the full
study-cohort reconstruction and disparity models.

## Current gating item: clinical type-code review (Step 40)

The Step39 private worksheet has been created successfully: all observed
encounter types have a reference description, but inpatient interpretation
and clinician approval are still **pending**. Follow the
[Step40 manual decision protocol](docs/STEP40_ENCOUNTER_TYPE_REVIEW_VALIDATION.md)
to review and classify the local five-row worksheet **without sharing it**.

After an authorized clinical/data-steward review, run:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step40_encounter_type_review_validation.py
```

The validator never reads source clinical ZIP tables, modifies the
worksheet, or approves inpatient definitions. The aggregate-only JSON
and review ZIP stay inside Git-ignored `results/phase1/`, where
**all generated research files must remain**. The repo PR stays draft.
Do not start the full clinical cohort reconstruction before verifying
inpatient status, source-ID scope, and imaging ascertainment.

## Current action: local encounter-type codebook review (Step 39)

The uploaded Step38 report successfully matched **all five** sampled
encounter-type codes to the Research Network Encounter Type terminology.
The automated description classifier left one reference-matched type
unresolved. That group should not be interpreted as missing encounters
or as non-inpatient. The aggregate counts remain in the private report.

Run [Step39](docs/STEP39_ENCOUNTER_TYPE_CLINICAL_REVIEW.md) to create
a **local-only private clinical-review worksheet** (five type codes,
their descriptions and prefix counts) plus a **separate aggregate-only
review ZIP**. Neither source codes nor their definitions enter the ZIP.
All generated outputs remain in the clone's gitignored
`results/phase1/`. Do not commit or upload the local worksheet.

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step39_encounter_type_clinical_review.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip"
```

A clinician/data steward still needs to approve the inpatient code
definition before we start a full linked-cohort reconstruction.

## Current action: encounter-type terminology reference (Step 38)

The corrected Step37 bounded pilot recognized compact YYYYMMDD date codes
in all sampled encounter, diagnosis, and procedure records. Sample-level
patient IDs agreed in observed encounter links, although some source_id
values differed; source provenance remains to be investigated.
Most encounter type values were **not recognized by a lexical-only rule**.

Run the [Step38 terminology-mapping audit](docs/STEP38_ENCOUNTER_TYPE_TERMINOLOGY.md)
to match the bounded encounter prefix with the local
`standardized_terminology.csv` **Encounter Type** reference table. This
reads only a 50k encounter prefix plus one streaming *reference metadata*
pass, and outputs aggregate JSON/review ZIP exclusively inside gitignored
`results/phase1/`. It does not validate admissions or any clinical
imaging disparity, and it never publishes the source type codes.

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step38_encounter_type_terminology.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip"
```

## Next action: bounded Research Network encounter pilot (Step 37)

Step 36 metadata preflight completed with required Research Network tables and
encounter-link fields present; structural readiness **does not** verify
inpatient admissions or imaging receipt. The [Step 37 pilot
protocol](docs/STEP37_RESEARCH_NETWORK_ENCOUNTER_PILOT.md) is now implemented
at `scripts/step37_research_encounter_pilot.py` with synthetic-only tests.
It reads at most 50,000 *nonrandom prefix rows* from each of encounter,
diagnosis, and procedure tables by default, with no full clinical scan.
The code checks sample-level encounter/patient/source key consistency
and label patterns without producing patient-level output.

From the cloned repository:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step37_research_encounter_pilot.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip"
```

Generated JSON and review ZIP exist **only** in gitignored
`results/phase1/`. Do not upload patient-level data or infer
population-wide linkage rates from file-prefix matches. The draft PR
remains unmerged pending institution-level data governance.

## Current path: Research Network feasibility (Step 36)

The locally held Research Network stroke export has encounter-key columns,
but their completeness, linkage and inpatient meaning remain unverified.
Run the [Step 36 metadata-only preflight](docs/STEP36_RESEARCH_NETWORK_PREFLIGHT.md)
before any encounter-level clinical reconstruction. Its generated JSON and
review ZIP stay **only** under the clone's gitignored `results/phase1/`.
The source TriNetX ZIP stays at its original external location; do not
copy patient-level files into this public repository.

The Step 36 report is a **schema check**, not evidence of verified admissions
or imaging receipt. Do not run a billion-row source scan merely to repeat
the preflight. The original disparities question remains conditional on
clinically valid encounter and imaging ascertainment.

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

## Step 33 validated; Step 34 internal manuscript work

The study-team uploaded `step33_recording_pattern_descriptives.json`
with `all_three_dimensions_reconciled=true`,
`aggregate_inputs_only=true`, denominator **86,902**,
and no private SQLite or original ZIP record reads.
Each age/recorded-sex/index-year breakdown sums to
**39,815 head-only matches** and **39,949 head+neck matches**
for the working +/-1-day window.

A private internal methodological manuscript draft is available separately
from this public GitHub repository; [Step34 internal exhibit instructions](docs/STEP34_INTERNAL_MANUSCRIPT_PACKAGE.md)
are now available. The aggregate-only
[Step34 script](scripts/step34_manuscript_exhibits.py)
creates internal vector SVG/high-resolution PNG plots,
descriptive CSV tables and a source SHA256 manifest
under gitignored owner-only results/ paths. It
requires matplotlib; eight new synthetic tests
still need to pass on the study workstation.
Outputs remain unapproved for external disclosure.

The methodological focus is selection on historical
MRI/CTA/MRA coding, comparison to an imaging-independent
diagnosis-first denominator, procedure vocabulary
sensitivity, calendar-date matching assumptions and
high demographic missingness. No true encounter,
imaging receipt or racial access disparities are
inferred; no additional billion-row scan is needed.

## Step 32 passed; Step 33 methods research preparation

The study team confirmed **157 passed, 2 nonblocking warnings**
for the repository suite and ran Step32 successfully. Its output
reconciles all age, recorded sex and index-year marginal counts
to the same 86,902 patients and 121,033 code-specific events
without rescanning the original Diamond ZIP or exporting patient
records.

Within +/-1 day, the **head+neck sensitivity** any-included-CPT
code match varies descriptively by age band (52.60% at 19-29;
44.22% at 40-50), recorded sex (47.71% Female; 43.72% Male),
and year (43.70% in 2018; 48.87% in 2019).
The **working primary head-only** any-code definition is
52.35% versus 44.09%, 47.56% versus 43.55%, and
43.53% versus 48.73%, respectively. These are UNADJUSTED
administrative code-matching frequencies and must not be
interpreted as actual imaging receipt or access inequalities.

A new [Step33 methods study and evidence-based figure/table plan](docs/STEP33_METHODS_STUDY_DESIGN.md)
documents descriptive results and a potential publishable
source-data methods audit. The
[Step33 aggregate-only script](scripts/step33_aggregate_patterns.py)
reconciles the Step31 and Step32 JSONs, outputs exact
head-only and head+neck percentage rates, and does not open
either the clinical source ZIP or private SQLite. Its new
synthetic tests still need to run on the user's workstation.
No further original billion-row source scan is justified.

```bash
python -m pytest -q && python scripts/step33_aggregate_patterns.py   --step31 results/phase1/step31_expanded_reconciliation.json   --step32 results/phase1/step32_recording_heterogeneity_qc.json   --output results/phase1/step33_recording_pattern_descriptives.json
```

Even broad aggregate counts require institutionally approved
cumulative disclosure review before public release. No clinical
disparity modeling, admission-level imaging claims, or manuscript
publication is authorized by a passing technical audit.

## Step 32: Study-team read-only code-recording QC

The uploaded `step31_expanded_reconciliation.json` reports
**all aggregate checks passed** over 0, +/-1, +/-3 and +/-7-day
windows, with **zero original ZIP or patient-level SQLite
records read** by that aggregate script. Expanded CPT code matching
adds only 175 patients to the any-code category at +/-1 day and
158 at +/-7 days, leaving **54.03%** and **51.32%** without a
matching included CPT code respectively. This is source-code
recording, not proof of absent imaging.

A new [Step 32 read-only private-index audit](docs/STEP32_RECORDING_HETEROGENEITY_QC.md)
checks whether recorded-code coverage varies by broad index year,
recorded sex and approximate age band. It opens only the already
completed small PRIVATE SQLite indexes and cross-checks their
aggregate counts against Step30; **it does not open the original
1.17-billion-row procedure source**. No regression, p-values,
causal or demographic disparities conclusions are produced.
The script has synthetic tests that still require a study-team
pytest run. New subgroup aggregates should not be released
without cumulative small-cell disclosure review.

## Step 31: Expanded 14-CPT procedure scan completed; inference still blocked

Study-team full extraction from the existing ZIP completed with
**1,166,493,611** manifest-verified procedure rows. The
**86,902-person** principal-I63 diagnosis-first denominator is
unchanged; all 97,872 prior unique modality-day matches were preserved.
The completed private code-specific database stores 121,033 exact
code-specific patient/day records outside Git. This was explicitly
*evidence-reviewed exploratory extraction*, not clinician-approved
imaging utilization or admission validation.

At +/-1 calendar day, original 9-CPT coverage had 39,774 people
with any matched imaging code; the 14-CPT head/neck expansion has
39,949 (only **175 more**, +0.201 percentage points).
**46,953 (54.03%)** still have none of the included procedure codes.
At +/-7 days, 44,602 (51.32%) remain unmatched. This suggests
source capture/observability limitations that additional neck codes
do not resolve. Do not describe missing CPT codes as no clinical
imaging, or code frequencies as hospital imaging utilization rates.

See [Step 31 completed-scan findings](docs/STEP31_EXPANDED_SCAN_FINDINGS.md).
A new [aggregate-only reconciliation](scripts/step31_expanded_reconciliation.py)
checks the source, original Step22 and expanded Step30 reports
without reading any original ZIP or private SQLite records.
Full new tests still require execution on the study workstation.
A **methods/measurement-bias** manuscript is now a more defensible
candidate than unsupported access/clinical disparities inference.

## Step 30: evidence-based imaging code review, existing data only

The investigator explicitly authorized one additional scan of the
original local procedure table if permitted by the current data-use
agreement. The imaging definitions have been appraised against
**2013 ASNR/ACR/SNIS stroke imaging guidance, 2019 AHA/ASA
ischemic stroke guidance, and historical CMS code listings**.
See [Step 30 scientific evidence review](docs/STEP30_EVIDENCE_REVIEW_AND_AUTHORIZATION.md).

The 14-code
[evidence-reviewed CPT catalog](dataset/imaging_codebook_literature_review_v1.csv)
is **NOT a physician sign-off**. Head CT, brain MRI, CTA head and
MRA head remain separate primary code outcomes; CTA/MRA neck is a
distinct expanded sensitivity. No hospital admission, completed
imaging, stroke incidentness, data-capture completeness or
clinical inequity may be inferred just from code proximity.

The extractor has an additional **--execute-literature** path that
requires the local operator's explicit
**--confirm-existing-data-use-permitted** attestation. It never
falsifies an institutional or clinical approval. Run the
metadata preflight and full tests first; see
[Step 28 local commands](docs/STEP28_IMAGING_CODEBOOK_PREFLIGHT.md).
Use the full scan only if the existing TriNetX agreement and
institutional rules allow this private research extraction. The
assistant cannot trigger the workstation scan from this chat.

## Step 28 preflight completed; Step 29 clinical codebook review

The study-team `step28_codebook_plan.json` confirms the original
archive fingerprint, **86,902** eligible diagnosis-index patients,
**1,166,493,611** declared procedure rows and **14 candidate CPT
codes**, all pending clinical review. **Zero source clinical rows were
scanned; no expanded extraction has started.**

[Step 29 clinical review memo](docs/STEP29_CLINICAL_CODEBOOK_REVIEW.md)
separates CTA/MRA head from CTA/MRA neck and asks the clinical team
to agree whether head-only or head-plus-neck should be the primary
recorded-code endpoint. The exact code is retained in any future
approved extraction, allowing both anatomical summaries without
a second scan. Missing encounter identifiers, >75% race/ethnicity
missingness and old public data-sharing artifacts remain blockers
to population disparity claims.

Do NOT use --execute until the exact clinical codebook, protocol,
source-capture meaning and data-use review are approved. No additional
TriNetX source access is available.

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

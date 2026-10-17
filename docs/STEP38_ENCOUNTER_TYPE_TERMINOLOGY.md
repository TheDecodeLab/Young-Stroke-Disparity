# Step 38: Research Network encounter-type terminology check

**Goal:** determine whether previously *unclassified* encounter \`type\` values
can be interpreted using the original Research Network
\`standardized_terminology.csv\` reference table.

The uploaded Step 37 report showed all 150,000 sampled clinical-event dates
in compact YYYYMMDD form. The parser now recognizes that format. In a
nonrandom prefix of 50,000 encounters, only 1,120 had an obvious lexical
inpatient candidate label, while 48,880 remained unclassified. This does
**not** mean those 48,880 encounters were non-inpatient.

The Step 37 encounter-prefix matches had consistent patient identifiers
between event and encounter rows, but some \`source_id\` values differed
across events. Such differences require provenance review, not an automatic
exclusion or assumption of invalid encounters.

## What Step 38 scans

- **At most the first 50,000 records of \`encounter.csv\`**, using just the
  encounter \`type\` field and never writing patient/event IDs
- **One streaming pass over \`standardized_terminology.csv\`** to find
  \`code_system=Encounter Type\` code/description mappings
- The metadata-only Step 36 and aggregate-only Step 37 JSONs already
  under \`results/phase1/\`, to verify input lineage and row-count agreement

The reference terminology file has approximately 2.3 million rows according
to the previously inspected manifest. Its streaming pass reads **reference
metadata, not a billion-row clinical-event table**. It is capped at
3,000,000 reference rows and aborts rather than reporting incomplete
terminology coverage. No larger patient-event scan is needed at this stage.

## Run from the cloned repository

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step38_encounter_type_terminology.py \
  --zip "$HOME/datasets/TriNetX/stroke_research_network_dataset_68b1a0575a2bf16052a523ef.zip"
```

Generated files (only inside the clone, both gitignored):

```text
results/phase1/step38_encounter_type_terminology.json
results/phase1/step38_encounter_type_terminology_review.zip
```

The ZIP contains **only** the aggregate JSON. The program rejects all
output locations outside the cloned repository's \`results/phase1/\` path;
it never copies the source ZIP. Generated outputs have owner-only 0600
permissions. Temporary synthetic-test files also stay under
\`results/phase1/\`.

## Reading the report

The JSON contains aggregate rows examined, terminology scan counts,
coverage of sampled encounter types by \`Encounter Type\` reference codes,
and **keyword-based candidate categories** such as inpatient, emergency,
outpatient, observation, virtual, mixed, and unclassified.

Only code descriptions are used transiently, and only coarse category
counts are exported. No patient ID, encounter ID, \`source_id\`, actual
\`type\` value or code, literal date, terminology description, ZIP content,
or record-level row is written into the output. Counts of 1 through 10
are suppressed. Review the report for institutional approval before
uploading it; complementary counts could still be sensitive.

Even a successfully decoded \`inpatient_candidate\` is NOT verified
hospital admission. Terminology definitions, care setting, transfer
semantics, observation status, HCO provenance and claims/EHR imaging
capture must be assessed before defining the primary clinical cohort.

If there are few or no matches to the terminology table, do not infer
that the source lacks inpatient encounters. Review the extract's
encounter-type value conventions and documentation locally before any
large clinical table scan.

## Next decision

1. If codes map and descriptions are coherent, ask the clinical/data
   investigators to approve a strict inpatient index definition.
2. If codes are not recognized, investigate their format and source
   mapping with a metadata-only diagnostic; do not force unknown codes
   into inpatient or outpatient classes.
3. Only then plan a **single** carefully controlled private encounter-
   and diagnosis-first cohort reconstruction for young 2018-19 stroke,
   with imaging and demographic completeness evaluated in that cohort.

The original clinical imaging-disparities question remains the target,
but no imaging utilization or disparity inference is approved by this
Step 38 terminology audit.

**Public repo disclosure warning:** Historical TriNetX derived row-level
files remain in public Git history. Do not publish aggregate results,
patient-level files or further exports there without institutional
privacy and data owner authorization. Keep PR #1 draft and unmerged.

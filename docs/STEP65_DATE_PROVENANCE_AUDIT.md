# Step 65: Date-provenance check for ED-linked index encounters (LOCAL ONLY)

**Status:** Synthetic-only implementation, pending investigator workstation
test confirmation. The script reads ONLY previously completed Step62
and Step63 private SQLite databases and produces a console-only aggregate.
No source ZIP scan, checkpoint modification, imaging ascertainment
change, or patient/encounter identifiers are emitted.

## Why

Step64 established the hypothetical ceiling for improvement in
documented CPT14 imaging-code capture from unique ED links.
But the Step63 ED-to-IMP link is based only on calendar dates.
The older published TriNetX dictionary specifies that encounter
`start_date_derived_by_TriNetX`, `end_date_derived_by_TriNetX` and
`derived_by_TriNetX` use `T` or `F` to identify values derived
by TriNetX; this may change our confidence in date-only linking.

Public pointers, subject to confirming the data dictionary applicable
to the current export:

- Penn State TriNetX guide:
  https://ctsi.psu.edu/services/research/trinetx
- TriNetX Data Dictionary (July 2021 edition) published on a university
  website. The historical edition describes `source_id` as provenance
  (`HCO`, `TriNetX`, `HCO-NLP`), NOT an HCO identifier; describes
  `principal_diagnosis_indicator` as P/S primary/secondary reasons
  for the encounter and separately defines `admitting_diagnosis`.
  Verify current field definitions with the responsible data steward.
  No third-party dictionary text is copied into this repository.

The derived-date audit is a quality check, not proof that a
derived date is wrong, that an ED patient was treated at the
same institution, or that a code equals completed imaging.

## Audit

`scripts/step65_date_provenance_audit.py` uses the Step63
`evt`, `idx` and `linked` tables, with a frozen Step62 snapshot
check reused from Step64.

It computes aggregates stratified by index cohort, unvalidated P-label,
and (in a second section) index year, for two roles:

- `INDEX_IMP`: all Step62 indexed inpatient encounters. Quarantined
  index events are counted as `missing_source_event`.
- `LINKED_ED`: only Step63 reciprocal-uniquely linked ED encounters.
  The script does not artificially add ED links for quarantined patients.

For each role, the three derivation flags are classified as T, F,
MIXED or OTHER_OR_BLANK. The latter includes unset and unexpected
values, not proof that a date is source-derived. All four categories
must sum to retained row count; missing events are reported separately.
Raw patient IDs, encounter IDs, exact dates and source events are not
printed or written. Small output groups (<11) are suppressed, but this
does NOT constitute institutional approval to share a full table.

## Execution

From the draft research branch:

```bash
git pull --ff-only origin analysis-rebuild-phase1-audit
python -m py_compile scripts/step65_date_provenance_audit.py
python -m pytest -q tests/test_step65_date_provenance_audit.py
python -m pytest -q
```

If both test commands succeed:

```bash
python scripts/step65_date_provenance_audit.py
```

Requires existing private databases at:

- `results/phase1/full_reconstruction_private/step62_cohort_private/provisional_cohort_LOCAL_ONLY.sqlite`
- `results/phase1/full_reconstruction_private/step63_ed_sensitivity_private/step63_ed_feasibility_LOCAL_ONLY.sqlite`

**Neither database should be uploaded or committed.** Console
aggregates are still subject to institutional disclosure review.

## Decision criterion

If linked ED dates are frequently TriNetX-derived, missing, or
inconsistent, date-only sensitivity B should be treated as especially
tentative. If most are independently sourced, that strengthens date
provenance but still does NOT verify transfer or imaging. In either
case, ED linkage reaches a limited fraction of Step62 patients; do
not base clinical disparities on assumed missing CPT14 imaging.

A new full ED procedure scan is a separate scientific decision.
Do not assume that inpatient CPT14-only outcomes describe all
inpatient neuroimaging. The Penn State TriNetX guide distinguishes
inpatient ICD-10 procedure terminology from outpatient CPT coding;
this is a reason for empirical code-system QA, not a universal
exclusion rule. The meaning and completeness of the P flag and
hospital/organization representation require steward validation.

# Step75: Correct the ICD-10-PCS section-B denominator after Step74

**Status (2026-10-20):** Read-only script and fabricated-only tests committed.
The investigator has NOT run the new local audit yet.

## Why this correction is necessary

Step74 completed successfully on the investigator's workstation:
all 708 repository tests passed, the FY2016-2025 official CMS
ICD-10-PCS ZIPs were downloaded and checked, and a LOCAL ONLY
code-profile crosswalk was preserved without a clinical-source
scan.

**A material interpretation issue was identified:** Step74's
`all_PCS_source_rows` denominator included ICD-10-PCS
codes from **every section**, but its CMS title parser
intentionally retained only codes whose first character
was `B`, the ICD-10-PCS **Imaging** section. Therefore,
the `valid_neighbor_FY_rows / all_PCS_source_rows`
ratio must NOT be called a total ICD-10-PCS
validity or crosswalk-success rate. Its complement
contains many valid non-imaging PCS procedures.

Official CMS reference: ICD-10-PCS consists of seven
characters, with the first character encoding a section:
`0` Medical and Surgical, `B` Imaging,
`C` Nuclear Medicine, etc.
https://www.cms.gov/Outreach-and-Education/MLN/WBT/MLN4151758-ICD-10-PCS/ICD10PCS/jobaids/jobaid.html

Step74's `REVIEW_ONLY` title matches remain **candidate
source rows**, not unique patients and not validated
head CT/MRI/CTA/MRA. The printed rows include two
substantially overlapping cohort definitions and are
therefore not additive clinical counts.

## Step75 correction and quality gates

The script `scripts/step75_pcs_section_denominator_audit.py`
reads only:

- Frozen Step62 and Step63 read-only private SQLite
  checkpoints;
- Frozen Step68 private `code_profile` table
  and aggregate source metadata;
- The already completed Step74 LOCAL ONLY JSON,
  including official CMS per-year ZIP SHA256 receipts;
- Cached **PUBLIC CMS FY2016-2025 ZIP packages**
  from Step74, validated against their saved hashes.

It does NOT read the original ~993-million-row
clinical procedure source, download new data,
change any database, or contact TriNetX.

The audit separates at the source-row
× cohort-membership grain:

1. **All source rows labeled ICD-10-PCS**;
2. **Other PCS sections** (first character not `B`);
3. **Imaging-section `B` code rows**;
4. Valid seven-character **syntax** and malformed
   `B` values, using the CMS alphabet exclusion
   for `I` and `O`;
5. **CMS-matched, syntactically valid imaging-section
   codes**, comparing the source service calendar
   year Y against the cached FY Y or FY Y+1
   code titles;
6. Remaining unmatched `B` rows grouped by
   three-character family, without emitting
   exact source code strings;
7. **Review-only CNS CT, CNS MR, upper-artery
   CT and upper-artery MR** candidate row counts,
   using the same conservative Step74 exact-code
   and official-title screen.

The printout includes correct **CMS matched B /
all B** rates, not merely **matched B /
all ICD-10-PCS**. Counts and review-only
candidate rows are grouped by source year,
unvalidated P flag and capture scope
(INDEX_IMP, NONIMP_DAY0, UNIQUE_ED).

Every Step75 all-PCS, CMS-matched and
review-only candidate total must reconcile
**exactly** with the Step74 saved LOCAL ONLY
report; source database snapshots and CMS
ZIP SHA256 are also checked. Fail closed
on missing data, changed snapshots, and
inconsistent partitions.

## One bundled local run

```bash
(
  set -e
  git pull --ff-only origin analysis-rebuild-phase1-audit
  python -m py_compile scripts/step75_pcs_section_denominator_audit.py
  python -m pytest -q tests/test_step75_pcs_section_denominator_audit.py
  python -m pytest -q
  python scripts/step75_pcs_section_denominator_audit.py
)
```

**Next handoff: TERMINAL OUTPUT ONLY.** No ZIP
or private SQLite/JSON file is requested.
The completed Step74 local report and CMS
archives should stay where they are.

## What Step75 can and cannot decide

If nearly all well-formed `B` rows match the CMS
year-neighbor screen, the apparent poor match in
Step74 came primarily from denominator scope.
If many `B` rows remain unmatched, inspect
source-code syntax, the first three-character
family, FY version selection and possible
mapping/encoding problems **before** adopting
any extra imaging code.

Even high match rates among `B` rows do NOT
tell us whether candidate images were performed,
whether they were related to the index
ischemic-stroke admission, or how many
CPT14-negative patients gain capture.
The old CPT14 patient-level endpoint stays frozen.

**Next substantive decision after Step75:**
Review exact official title/year-specific
B02/B03/B32/B33 candidate codes and determine
whether the anticipated additional capture
justifies one carefully checkpointed
patient-level reclassification pass or
whether CPT14 suffices as a transparently
limited coded-imaging primary outcome.
No new demographic GLM or full source scan
should be launched just because Step74
printed review-only row counts.

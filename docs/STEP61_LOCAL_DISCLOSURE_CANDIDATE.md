# Step 61: Local coarse summary for possible external scientific review

**Status:** The investigator completed Step58, all three Step59 scans, and
Step60 locally on 2026-10-18. The repository previously passed **599 tests,
3 existing warnings**. The private Step60 report has **not** been transferred
to or viewed by ChatGPT. The investigator indicated external sharing of
appropriately reviewed, de-identified aggregate summaries is permitted.

The [Step61 script](../scripts/step61_disclosure_candidate.py) reads only
`step60_local_aggregate_review_LOCAL_ONLY.json` from the approved workstation's
Git-ignored `results/phase1/full_reconstruction_private/source_wide_qa/`
directory. It does **not** open the TriNetX ZIP, reread patient data, redo
Step59, or transfer anything to GitHub. Its sole output is a **private candidate
for subsequent human disclosure review**.

## What the candidate contains

- Calendar years **only if all three** relevant tables have **at least
  1,000 aggregate rows each** for that year. If any table is smaller, the entire
  year is omitted. This threshold concerns **source rows**, not independent
  patients or a HIPAA/statistical disclosure certification.
- Broad directional changes (`roughly_similar`, `up_25_to_50pct`,
  `up_more_than_50pct`, `down_20_to_50pct`,
  `down_more_than_50pct`) between **adjacent eligible** calendar years for
  encounter, diagnosis and procedure row volumes. No cross-table percentages,
  actual counts or underlying denominators are included.
- Qualitative share of CPT vs non-CPT procedure rows
  (`mostly_CPT`, `mostly_non_CPT`, or `mixed_CPT_and_non_CPT`) **only
  when both complementary groups have at least 50 rows**, with a minimum
  1,000 procedure-row denominator. Otherwise `withheld`.
- Presence of recorded core CPT14 procedure *code rows*, only when both the
  CPT14 subgroup and remaining CPT rows are at least 50 and CPT rows total
  at least 1,000. Otherwise the result says
  `withheld_not_evidence_of_absence`, **never zero recorded procedures**.
- Static cautions that **source-code rows are not imaging exams**, that HCO
  participation and calendar-year completeness remain unverified, and that the
  complete study end year is still unknown.

The candidate **does not include** original counts, exact percentages, exact
code-row frequencies, small subgroup estimates, patient or encounter IDs,
hospital/HCO labels, source filenames, locations, descriptions, demographic
strata, diagnosis codes or free-text notes.

**Important:** This conservative default does not guarantee that an output is
safe or authorized for disclosure. It does not assess external dataset
agreements, previous public releases, possible differencing attacks across
related summaries, disclosure of proprietary metadata or additional PSU
restrictions. A trained reviewer still needs to approve external release,
and even a coarse year-trend label may need to be removed under your terms.

## Run locally on the approved workstation

First pull and test the *public script and synthetic test fixtures only*:

```bash
git pull --ff-only origin analysis-rebuild-phase1-audit
python -m py_compile scripts/step61_disclosure_candidate.py
python -m pytest -q
```

The previous full workstation suite was **599 passed**. Step61 adds **11
synthetic tests** that passed independently against the **exact committed
bytes** of the script and test file, so the expected new full count is **610**.
If it differs, review before continuing.

Only after full tests pass, create the local candidate:

```bash
python scripts/step61_disclosure_candidate.py \
  --acknowledge I_CONFIRM_PRIVATE_DISCLOSURE_CANDIDATE_ONLY
```

The command writes (mode 0600, without overwrite):

```
results/phase1/full_reconstruction_private/source_wide_qa/step61_disclosure_candidate_LOCAL_ONLY.json
```

It does **not** print aggregate findings to the terminal. It does not
create a file in a public repo directory and does not share the file
automatically.

## Before uploading anything to ChatGPT

1. Review that **this particular type of summary** is permitted for external
   AI-service sharing under your Penn State research agreement and any network
   contract. You already indicated that approved aggregates may be shared,
   but the script cannot validate the actual agreement.
2. Open **only the Step61 candidate** locally and review each year/qualitative
   trend for small-cell, indirect identification and prior-release
   differencing risk. Seek the required institutional disclosure clearance.
3. If clearance is obtained, manually upload **only that reviewed Step61
   candidate**. Do **not** upload the Step60/Step59 JSON reports, source ZIP,
   patients, procedures, private code descriptions or restricted institution
   metadata. Otherwise we can use a private local review workflow instead.

Even after the candidate is reviewed, analysis recommendations must remain
qualified. Step61 is a **descriptive source-quality aid**, not a stroke
phenotype, validated performed-imaging ascertainment, final research-period
selection or disparity estimate. PR #1 remains DRAFT and Step45's obsolete
full clinical scan remains disabled.

## Relevant files

[Active research plan](ACTIVE_RESEARCH_NETWORK_STUDY_PLAN.md) |
[Step60 local source QA](STEP60_PRIVATE_SOURCE_QA_REVIEW.md) |
[Synthetic Step61 tests](../tests/test_step61_disclosure_candidate.py).

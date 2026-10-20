# Step66: ED imaging-code ceiling after date-provenance restriction

**Status (2026-10-19):** Completed successfully on the investigator's
authorized workstation after a corrected output-suppression test and
two-pass SQL optimization. The standalone Step66 synthetic suite and
full repository suite passed, and the read-only analysis completed its
cohort, unvalidated P-stratum, and index-year reporting without an
exception. **No clinical source ZIP scan, no patient-level files uploaded
to GitHub, and no local database writes.** The original failed test and
interrupted run remain in project history as audit events.

## Question

Step65's read-only aggregate review found that some linked ED
encounter end dates are marked `end_date_derived_by_TriNetX=T`.
The date-only ED predecessor definition (0-1 calendar days) relies
on this field. A documentation-derived rather than directly sourced
end date is not necessarily wrong, but provenance needs a separate
sensitivity check before treating this link as a plausible care episode.

Step66 keeps frozen Step63 **reciprocally unique pairs** and computes
hypothetical maximum *new* CPT14-coded patients using increasingly
restrictive date-provenance subsets. It does **not** recompute
uniqueness after dropping links, which could incorrectly turn a
previously ambiguous candidate into a unique one.

## Definitions and denominator

**Always keep the original Step62 indexed patient denominator and
Step62 primary same-IMP CPT14 capture**. Every cohort is analyzed
separately; co-primary cohorts overlap and must not be added.

- `all unique ED`: previously frozen Step63 reciprocal-unique
  date-only 0-1 day linked ED, before checking derivation flags.
- `ED end+IMP start both F`: the *two calendar dates used in the
  cross-encounter linkage* both have TriNetX derived flags `F`.
  `F` is used as a conservative source-provenance definition,
  not a clinical guarantee.
- `all ED flags + IMP start F`: stricter subset that also requires
  ED `derived_by_TriNetX=F` and ED
  `start_date_derived_by_TriNetX=F`.
- `F critical dates gap=0`: subset of the second definition with
  ED end on the same calendar day as IMP start.
- `F critical dates gap=1`: subset with ED end the calendar day
  preceding IMP start. The last two partitions are disjoint and
  together exhaust the `F`-critical-date set.

For each scenario:

`maximum_new = # patients with qualifying ED link AND without any
Step62 same-IMP CPT14 documented-code outcome`.

No ED procedure records are used. These are **logical upper bounds**
assuming imaging CPT14 codes hypothetically existed in every qualifying
linked ED encounter currently inpatient-code-negative. Actual
incremental capture, if evaluated later, cannot exceed these counts.
No results are clinical imaging utilization, missing imaging or a
validated care transition.

A returned date gap outside 0-1, missing retained ED event, or a
snapshot/link-policy mismatch causes a hard failure. No private
identifiers are printed or saved. Grouped output includes cohort,
unvalidated `P` label and index year, with group n<11 suppressed.
This does not constitute a disclosure-cleared aggregate artifact.

## Query optimization and regression tests

The current Step66 implementation first aggregates the complete frozen
Step62 index and its recorded `ANY_CPT14` flag using indexed existence
lookups. A **separate** aggregation then joins date-provenance fields
only for the much smaller **frozen Step63 unique-ED link subset**.
This replaces an expensive single SQL query joining the full
index population through ED and IMP event records.

Before showing results it checks that the frozen ED/IMP event rows
still exist and agree with Step63 linked encounter/date keys, that
ED/IMP date spans are internally valid, that linked date gaps stay
within 0-1 calendar days, and that source-provenance scenario
subsets are properly nested. The original Step62 denominator stays
fixed, including ED-linkage-unassessable patients.

The synthetic suite now tests both groups under 11 (correctly
suppressed) and non-suppressed display, modified/frozen ED event
dates, gap-boundary failures, and **independent reconciliation**
of Step66's unrestricted ceiling against Step64's separately
implemented synthetic metrics.

No full runtime or performance claim is made until the investigator
runs this revision locally. Do not run the source ZIP or rerun
completed Step62/63 staging to test Step66.

## Execution (investigator's authorized workstation only)

```bash
(
  set -e
  git pull --ff-only origin analysis-rebuild-phase1-audit
  python -m py_compile scripts/step66_provenance_sensitive_ceiling.py
  python -m pytest -q tests/test_step66_provenance_sensitive_ceiling.py
  python -m pytest -q
  python scripts/step66_provenance_sensitive_ceiling.py
)
```

The parenthesized **subshell** stops at the first failed compile or
test, so the analysis will never launch after an earlier failure.
Its `set -e` does not change the investigator's interactive shell.

Both databases are opened in read-only mode:

- `results/phase1/full_reconstruction_private/step62_cohort_private/provisional_cohort_LOCAL_ONLY.sqlite`
- `results/phase1/full_reconstruction_private/step63_ed_sensitivity_private/step63_ed_feasibility_LOCAL_ONLY.sqlite`

The script does not require the source ZIP. Nothing is written to
the private databases. Do not upload either database. Share aggregate
terminal output only with appropriate disclosure authorization.

## Completed scientific interpretation

The investigator's local results establish that excluding links whose
ED end or inpatient start dates are marked TriNetX-derived reduces the
**hypothetical** imaging-code capture ceiling overall, with much larger
reductions in the earlier study years. Most residual potential
additional capture arises from **same-calendar-day** links rather than
one-day-prior links. Differences persist across unvalidated P strata.
No actual ED procedures have been examined by Step66, and exclusion of
derived dates is a cautious provenance sensitivity—not a validated
measure of date accuracy.

**Decision:** Treat the 0-1-day ED sensitivity as a secondary, unverified
event-code capture analysis, not as the primary clinical imaging
utilization measure. Do not launch the approximately billion-row
procedure rescan solely to pursue this upper bound. First complete
the [Step67 measurement-validity gate](STEP67_MEASUREMENT_VALIDITY_GATE.md)
on procedure-code semantics and version-correct alternative coding.
Keep actual source-derived aggregate values in LOCAL ONLY outputs,
not this public source tree.

## Interpretation

If the maximum potential addition shrinks substantially after
requiring non-derived ED end and IMP start dates, the ED sensitivity's
ability to address Step62 CPT14 missingness is even smaller than the
Step64 unconstrained ceiling. If it changes little overall, compare
the effect within `P` groups and earlier years, where provenance
differences may be concentrated.

An output of zero hypothetical additional imaging-code patients
would not demonstrate that any actual imaging was or was not done.
Even after this exercise, imaging coding-system coverage,
encounter-type semantics, HCO participation, and `P` field meaning
remain material issues before demographic regression. 

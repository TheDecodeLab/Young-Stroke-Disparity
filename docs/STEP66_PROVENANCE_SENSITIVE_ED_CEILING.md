# Step66: ED imaging-code ceiling after date-provenance restriction

**Status:** Synthetic-only implementation pending local tests and local
validation. **No clinical source ZIP scan; no local patient-level files
are uploaded to GitHub.**

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

## Execution (investigator's authorized workstation only)

```bash
git pull --ff-only origin analysis-rebuild-phase1-audit
python -m py_compile scripts/step66_provenance_sensitive_ceiling.py
python -m pytest -q tests/test_step66_provenance_sensitive_ceiling.py
python -m pytest -q
```

Only after both test commands pass:

```bash
python scripts/step66_provenance_sensitive_ceiling.py
```

Both databases are opened in read-only mode:

- `results/phase1/full_reconstruction_private/step62_cohort_private/provisional_cohort_LOCAL_ONLY.sqlite`
- `results/phase1/full_reconstruction_private/step63_ed_sensitivity_private/step63_ed_feasibility_LOCAL_ONLY.sqlite`

The script does not require the source ZIP. Nothing is written to
the private databases. Do not upload either database. Share aggregate
terminal output only with appropriate disclosure authorization.

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

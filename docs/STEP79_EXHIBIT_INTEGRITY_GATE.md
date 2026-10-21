# Step79: Audit completed private paper exhibits before manuscript use

**Status (2026-10-20):** Step78 completed locally with 736 tests
passing; Step79 code and fabricated-only tests are committed,
but the **local Step79 check is pending**.

## Why

Step78 generated five private CSV tables, two PNG figures, a
private Results draft and a provenance manifest using the frozen
Step62/63/68 research-network checkpoints. This is a complete
**draft calculation package**, not yet a shareable manuscript.

Cross-exhibit arithmetic consistency and suppression/differencing
risk must be assessed before deciding which data belong
in public tables. The quality of the clinical interpretation
remains distinct from software test success.

## Script

`scripts/step79_manuscript_exhibit_integrity.py` reads ONLY
the existing immutable local folder:

```text
results/phase1/full_reconstruction_private/
step78_paper_exhibits_private/draft_v1/
```

It does not read source patient/encounter ZIP or SQLite
files, rerun GLMs, or modify Step78 artifacts.

Checks:

1. **Bundle and manifest identity:** exactly the nine known
   private files; expected policy, 18–50 primary cohort,
   overlap warning, and clinical/disclosure restrictions.
2. **Basic figure integrity:** PNG signature/IHDR and
   sufficient dimensions. This is NOT a human visual
   inspection of annotations, axis legibility or figure
   communication.
3. **Table1 vs Table2:** identical P-specific denominators,
   original same-IMP CPT14 numerators, exact recomputed
   percentages and percentage-point contrasts.
4. **Alternative outcome nesting:** all three broader
   definitions must include original index-IMP captured
   patients; ED/pre2/day0 must contain same-day
   and unique prior ED within each P cohort.
5. **Table3:** valid year, P and quarantine strata,
   rates from reported denominators, suppression of
   small denominators and a partition check when
   fully observed.
6. **Table4:** each measured demographic category
   partition, appropriate primary cohort denominator,
   valid percentages and missing/other labels.
7. **Table5:** exact 12 exploratory contrasts,
   marginal difference recomputation,
   interval ordering and explicit declaration
   that no HCO-cluster inference, severity adjustment
   or verified imaging receipt is available.
8. **Preliminary cross-table disclosure flags:** a
   small incremental numerator from subtracting
   two nested CPT14 definitions; inferable
   small event or complement counts in percent
   cells; and possible reconstruction of suppressed
   demographics/source-quality cells from
   published totals and other categories.

**Important:** This check is a preliminary internal
screen, NOT formal disclosure certification.
Cross-table and provider/site privacy risks may
remain even when the script finds no flags.
No public manuscript-ready decision is automatic.

## One run

```bash
(
  set -e
  git pull --ff-only origin analysis-rebuild-phase1-audit
  python -m py_compile scripts/step79_manuscript_exhibit_integrity.py
  python -m pytest -q tests/test_step79_manuscript_exhibit_integrity.py
  python -m pytest -q
  python scripts/step79_manuscript_exhibit_integrity.py
)
```

**Send TERMINAL OUTPUT ONLY.** The script deliberately prints
no data values, small counts, raw demographic labels,
patient identifiers or private figure pixels. Do not
upload the draft_v1 files or restricted clinical
code-review worksheets.

## Decision after run

- If a hard integrity check fails, repair only
  the reproducible *code* on GitHub; preserve
  immutable Step78 `draft_v1` for traceability
  and issue an explicitly versioned private
  corrected results bundle if needed.
- If disclosure flags are raised, use the
  institutional review process to determine
  safe complementary suppression, coarse
  reporting or omission; do NOT simply remove
  one flag and call the bundle release-approved.
- Independently inspect both rendered figures
  for clarity and scientific honesty. Numerical
  categories are nominal, so connecting
  them with a trend line can falsely suggest
  time or dose ordering; final publication
  may need an unconnected dot/interval plot.
- After integrity/disclosure review, write the
  paper's Results, Discussion, limitations,
  and reference-backed Introduction.
  Preselected PCS clinical review remains a
  separate sensitivity/codebook improvement,
  not a prerequisite for the CPT14 measurement
  methods paper.

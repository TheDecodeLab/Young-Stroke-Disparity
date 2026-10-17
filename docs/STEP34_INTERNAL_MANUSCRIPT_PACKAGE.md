# Step 34: Internal manuscript draft and reproducible exhibits

**Status:** Internal research writing only. Results must pass institutional
data-use and cumulative small-cell disclosure checks before any public
release. This stage does not request additional TriNetX data, run any
procedure scan or read patient-level SQLite.

## Input consistency and research scope

The study team submitted Step33 results for 86,902 diagnosis-indexed
individuals. All three broad marginal dimensions independently
sum to 86,902; the working head-only primary matched-code count
at +/-1 day is 39,815, and the inclusive head/neck sensitivity
count is 39,949. Step33 confirms its own aggregate-only data
provenance and that no clinical inference is authorized.

The coding sensitivity remains small relative to the temporal
window sensitivity. The full original procedure extraction is
complete and needs no repetition. These reports are not evidence
that people without CPT records did not undergo imaging.

## Manuscript source

See [internal manuscript draft v0.1](METHODS_MANUSCRIPT_DRAFT_v0.1.md),
covering: proposed abstract, introduction, methods, descriptive
results, limitations, discussion, figure/table specifications and
verified supporting biomedical references.

This manuscript has **not** been accepted by clinical coauthors,
data governance, an IRB or a journal. It is a planning draft;
its title and clinical interpretation remain conditional.

## Local code for tables and figures

The aggregate-only [Step34 script](../scripts/step34_manuscript_exhibits.py)
produces two CSV tables and high-resolution PNG/vector SVG
figures using just the completed JSONs:

- Figure 2: same-day, +/-1, +/-3, +/-7-day probability
  of a recorded *included CPT-code match*, comparing
  historical 9 CPT, 14 CPT head-only, and 14 CPT
  head+neck anatomical definitions.
- Figure 3 age, sex, year: **three separate figures**,
  each reporting head-only primary and head/neck
  sensitivity matching percentages under +/-1 day.
- Table 2: numerator, denominator, and percentage
  for the temporal/code definition comparison.
- Table 3: broad age/recorded sex/year strata,
  same-denominator numerator and percentage
  for head-only and head/neck versions.
- A JSON manifest with source SHA256 and
  generated-artifact SHA256 fingerprints.

The figures are white-background, large-label,
readable drafts. They do not use artificial
confidence intervals, unverified odds ratios,
hypothesis tests, or claims of population
imaging receipt/access.

## Run from repository root

```bash
git pull origin analysis-rebuild-phase1-audit

# Install dependencies only if your virtual environment lacks matplotlib.
python -m pip install -r requirements.txt

python -m pytest -q && \
python scripts/step34_manuscript_exhibits.py \
  --step25 results/phase1/step25_readiness_gate_v2.json \
  --step31 results/phase1/step31_expanded_reconciliation.json \
  --step33 results/phase1/step33_recording_pattern_descriptives.json \
  --out-dir results/phase1/step34_internal_exhibits
```

A complete run writes only under the Git-ignored
results/ directory, uses owner-only output permissions,
and checks that every published-facing count and
nested difference is either zero or at least 11.
These controls **do not replace** cumulative
cross-report privacy/disclosure review.

The Step34 script uses matplotlib. If matplotlib
is already available in the activated virtual
environment, you do not need to reinstall
the other project requirements.

## What to share

For troubleshooting, share the test summary
or error traceback. The
step34_internal_manifest.json itself includes
only aggregate-data hashes/file names, but
review its metadata before transmission.
Do not upload private clinical SQLite, original
ZIP, source patient data, or unreviewed
stratified graphics/table files.

The repository's historic public patient-level
TriNetX Parquet still requires institutionally
guided remediation, including Git-history
considerations. No figure or text should
be submitted externally until that governance
issue is resolved.

**Draft PR remains unmerged.**

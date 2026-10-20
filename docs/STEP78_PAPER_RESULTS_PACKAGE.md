# Step78: Internal paper-results exhibit bundle and manuscript draft

**Status:** Code and fabricated-only regression tests committed.
The investigator's local Step78 data/exhibit run is PENDING.

## Scope decision

Paper focus: **how encounter attribution and recording quality alter
measured neuroimaging CPT-code capture** among young adults with
candidate ischemic stroke. This is a retrospective **measurement
and ascertainment study**, NOT verified differences in
clinical imaging receipt, appropriate care, or causal inequity.

The completed Step77 result provides a mathematical upper bound
showing that the selected ICD-10-PCS review-only candidates alone
cannot erase the large index-IMP P contrast. It does not authorize
adding PCS to the patient-level numerator or another
billion-row source scan. Independent PCS clinical review can
be done later **without blocking** a CPT14 ascertainment
paper that does not classify PCS as performed imaging.

**Current primary patient population:** the uniform 18–50
year definitely eligible cohort; the historical sex-dependent
eligibility cohort overlaps and is sensitivity only.

**Current primary outcome:** one of the original 14 CPT
neuroimaging codes recorded on the same patient and indexed
IMP encounter during its start/end dates. This is
*documented code capture*, not validated radiology performed.

**Interpretation of P:** an unvalidated I63 principal
indicator. P=0 includes secondary/blank/unmarked diagnosis
records, not confirmed secondary ischemic stroke.

**Secondary outcomes:** index inpatient OR different
encounter on same admission calendar date; index inpatient
OR unique preceding ED; and an exploratory union of index
inpatient, ED and other near-day code events. No
same-hospital or same-episode assertion. Small-cell and
cross-table inference must be reviewed before release.

## Implementation and provenance

`scripts/step78_paper_results_bundle.py` uses:
- the frozen, **read-only** Step62 candidate cohort SQLite;
- the frozen Step63 indexed and ambiguous-encounter SQLite;
- the completed Step68 procedure-CPT14 flag SQLite,
  plus its privately stored aggregate policy/snapshot;
- the tested Step69 patient-group aggregation,
  Step70 direct pooled-year×encounter-quality
  descriptive standardization,
  Step72 grouped demographic modeling preparation,
  and Step73 provisional working-binomial sensitivity.

Input source signatures and original CPT14 aggregates
are rechecked before any outputs are created.
No original encounter, diagnosis or ~993-million-row
procedure CSV/ZIP is opened. No patient identifiers,
individual analytic observations or unrecognized
source demographic strings are exported. The
stored covariance intervals are
**NOT cluster-robust**, do not adjust unmeasured
severity and are supplementary descriptive
diagnostics only.

### Restricted output

One immutable, all-or-nothing private output folder:

```text
results/phase1/full_reconstruction_private/
step78_paper_exhibits_private/draft_v1/
```

Files:

| File | Intended use |
|---|---|
| `table1_P_and_recording_quality.csv` | Main cohort P recording and any-key ambiguity |
| `table2_P_endpoint_sensitivity.csv` | Main patient-level endpoint comparisons, crude and common year×quality mix |
| `table3_year_quarantine.csv` | Stratified source-quality screen; groups under 11 withheld |
| `table4_demographic_completeness.csv` | Measured sex/race/ethnicity data completeness and descriptive code capture |
| `table5_exploratory_demographic_models.csv` | Exploratory adjusted-code-capture model differences with NON-HCO-robust caveats |
| `figure1_coded_capture_by_encounter.png` | Primary encounter-definition rate comparison |
| `figure2_source_quality_standardization.png` | Crude and pooled-quality-mix P differences |
| `RESULTS_DRAFT_LOCAL_ONLY.md` | Provisional Results prose with the actual private numbers |
| `manifest_LOCAL_ONLY.json` | Frozen source signatures, analytic policy and explicit disclosure warnings |

The script stages output artifacts in a private 0700
directory, checks every artifact exists, restricts file
permissions to 0600, and atomically renames the
completed directory. It refuses overwriting an
existing `draft_v1`. If the analysis fails before
the rename, it removes incomplete staged outputs,
leaving completed upstream checkpoints untouched.

The public code repository contains a **text-only,
result-free manuscript draft**:
[Working manuscript](MANUSCRIPT_ASCERTAINMENT_WORKING_DRAFT.md).
The real numbers belong exclusively in the
LOCAL ONLY generated draft and must not be copied
into tracked files before disclosure approval.

## One combined investigator execution

```bash
(
  set -e
  git pull --ff-only origin analysis-rebuild-phase1-audit
  python -m py_compile scripts/step78_paper_results_bundle.py
  python -m pytest -q tests/test_step78_paper_results_bundle.py
  python -m pytest -q
  python scripts/step78_paper_results_bundle.py
)
```

**Return TERMINAL OUTPUT ONLY.** Do not upload,
ZIP, commit or email the private results
tables, figures, report, manifest or databases.
The private folder can be reviewed manually on
the authorized workstation in the next stage.
The command is fail-fast and the new synthetic
tests must pass before any actual analysis executes.

## Review gates before submission

1. Verify Step78 cohort and endpoint counts independently
   against the frozen Step68 and Step69/70 summaries.
2. Confirm Table2's *recorded-code estimand*
   and qualifier for every encounter screen.
3. Review small-cell and **cross-table differencing**
   disclosure risks across all exhibits, including
   Table3/Table4 and multiple overlapping cohorts.
4. Decide whether Table5 exploratory demographic
   associations belong in the supplement at all;
   they are not validated racial/ethnic care disparities.
5. Review any clinical coding assertions using the
   public CMS code register; PCS remains OUT of
   the actual patient numerator until clinical
   adjudication, which is not a prerequisite if
   the paper is explicitly CPT14-based.
6. Obtain coauthor clinical and statistical
   reviews, then prepare a shareable,
   source-permission-compliant manuscript.

The **next response after the local run** should
interpret only the terminal's validation status.
The private source-derived paper results are not
automatically released by this workflow.

# Step 43: Prioritize neuroimaging terminology for clinical codebook review

**Status:** Manual vocabulary review preparation only. No clinical data scanned.

The Step 42 Research Network reference-only pass returned thousands of
potential neuroimaging terminology entries, many with ambiguous head/neck
anatomy. No candidate is a validated evidence of an imaging procedure.
We need a manageable first review set **without discarding or approving**
any entries in the full reference list.

## How this works

`scripts/step43_neuroimaging_review_triage.py` reads **only** the local
Step 42 candidate worksheet and aggregate status JSON, already in
`results/phase1/`. It verifies all candidate category and discovery
counts reconcile, then assigns **review priority**, never a clinical
inclusion/exclusion decision.

Review buckets:

- `A_historical_CPT_anchor`: the previous CPT anchors, for checking only
- `B_description_specific`: description itself supports the suggested category
- `C_description_disagrees_with_path`: description-only and combined
  description/path categories differ, requiring correction
- `D_path_only_or_weak_description`: candidate appears to rely heavily
  on the terminology hierarchy, with high false-positive risk
- `E_mixed_head_and_neck`: anatomy cannot be assigned to head vs neck
- `F_possible_nonprocedure_concept`: wording suggests history, result,
  refused test, or another concept rather than a performed procedure
- `G_same_code_multiple_categories`: same code-system/code combination
  has conflicting candidate categories in the source worksheet

Triage buckets are **heuristic and not exhaustive**. A history/status term
not recognized by a rule could appear in the apparent high-priority set.
Some legitimate procedure terms may also receive a lower priority.
No codes are automatically excluded.

## Run from the cloned repository

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step43_neuroimaging_review_triage.py
```

No Research Network ZIP path is needed. The script reads **zero**
clinical events and does not reopen any of the multi-billion-row
clinical tables. It does not change the Step42 codebook.

Outputs are written **only** inside the cloned repo's Git-ignored
`results/phase1/`:

```text
step43_neuroimaging_triage_full_LOCAL_ONLY.csv
step43_neuroimaging_review_first_LOCAL_ONLY.csv
step43_neuroimaging_triage_status.json
step43_neuroimaging_triage_status_REVIEW.zip
```

The **full** worksheet retains every Step42 candidate (including its
original unapproved reviewer fields), adding four diagnostic columns.
The **first-review** worksheet takes up to **15 entries per provisional
imaging category**, sorted by triage priority. This convenience subset
is **not comprehensive** and must NEVER be deployed as a final codebook.
You can change its size with `--review-per-category N` (1 to 50).

The two CSVs contain raw terminology codes and descriptions.
They are **local-only**. The CSV serialization neutralizes cells
starting with spreadsheet formula characters to reduce spreadsheet
formula execution risk. Treat them as review files rather than
machine-readable validated clinical mappings.

The review ZIP contains **only** the aggregate JSON and excludes the
candidate codes, descriptions, annotation fields, and source data.
Generated files use owner-only mode 0600. Even this aggregate report
should be checked against institutional data-use permissions before
sharing.

To prevent erasing clinical notes, the script **refuses to replace any
existing Step43 output**. The `--overwrite` flag explicitly authorizes
replacement; do not use it after entering review decisions without
preserving your annotated copy locally.

## Next scientific decision

Ask the study neurologist/neuroradiologist and the TriNetX data steward
to review the prioritized candidate list and the full backlog; resolve
procedure intent, anatomy, coding systems, order vs completion,
status/history concepts, and head/neck separation.

Clinical sign-off of the encounter inpatient definition (`IMP`
provisional) and the meaning/coverage of `source_id` remain separate
preconditions. Establish the imaging-independent I63 cohort definition,
age window and diagnosis position before a carefully designed
single-pass private reconstruction.

**Do not run adjusted clinical disparities models from the Step41
truncated prefixes.** No Step43 output claims actual MRI/CTA/MRA
receipt or imaging equity. The public repository's unresolved historic
patient-level data exposure remains a governance hold on merging PR #1.

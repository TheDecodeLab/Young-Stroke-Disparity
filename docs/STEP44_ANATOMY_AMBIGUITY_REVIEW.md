# Step 44: Diagnose the mixed head/neck terminology group

**Purpose:** Reduce unnecessary clinical-review work without approving or discarding any imaging code.

The Step 43 aggregate report preserved all original imaging-vocabulary candidates, but its triage produced only three categories: historical CPT anchors, description-specific matches, and a large mixed head/neck group. **None** of the previous warning categories contained entries. This means the current review priority largely repeats the Step 42 classification; it is not enough to interpret the mixed-anatomy group.

Step 44 analyzes the already-generated **private Step 43 full worksheet**, comparing the technique/anatomy category from the **code description alone** with the earlier classification that also used the reference `path`.

It separates ambiguous entries into four **technical, nonapproved review groups**:

- `description_specific_but_reference_path_mixed`: description suggests one anatomical category, but the full hierarchy/reference label was mixed
- `head_and_neck_mixed_in_description`: description itself appears to mention head and neck together
- `only_reference_path_indicates_anatomy`: description alone does not provide a recognized modality/anatomy match
- `other_description_disagreement`: another disagreement or unusual description-only result

These are **not** validated radiology codes, proof of performed imaging, or final inclusion/exclusion rules. Reference descriptions and hierarchy labels can be misleading. The result **never changes the Step 42/43 primary category, clinical-review fields, or full source list**.

## Run

From the cloned GitHub repository:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
python scripts/step44_anatomy_ambiguity_review.py
```

The script does **not** read the original Research Network ZIP, clinical events, identifiers, or other large files. It reads just:

```text
results/phase1/step43_neuroimaging_triage_full_LOCAL_ONLY.csv
results/phase1/step43_neuroimaging_triage_status.json
```

It validates original candidate row totals, category counts, and triage tiers before generating any result. Its outputs are **only** inside the cloned repository's Git-ignored `results/phase1/`:

```text
step44_anatomy_ambiguity_full_LOCAL_ONLY.csv
step44_anatomy_ambiguity_review_first_LOCAL_ONLY.csv
step44_anatomy_ambiguity_status.json
step44_anatomy_ambiguity_status_REVIEW.zip
```

The full worksheet keeps every *originally ambiguous* entry with unchanged reference codes/descriptions and reviewer fields, plus one unapproved technical subtype. The first-review worksheet takes **up to 15 examples per subtype**, not a representative or complete list. Use `--review-per-origin N` with 1–50 if necessary.

**Keep both CSVs private.** They include source terminology codes, descriptions and possibly review notes; they are deliberately **excluded** from the ZIP. The review ZIP includes only aggregate status JSON. Both use owner-only file permissions. The script avoids overwriting existing files without an explicit `--overwrite` flag. Do not use that flag if you have manually annotated a review file without keeping a local backup.

Small aggregate subtype groups of 1–10 are suppressed in the review report, but complementary disclosure can remain possible, so check institutional rules before sharing.

## Scientific stop/go

The new split should tell us whether mixed-anatomy terms are caused mostly by overly broad terminology paths or genuinely mixed descriptions. **It cannot settle the actual clinical codebook.** Have the neuroradiologist/neurologist and data steward review the code definitions, modality, procedure status, and coverage across CPT/SNOMED/other systems. The inpatient encounter and diagnosis-first young-stroke index criteria remain unapproved.

After the technical codebook is curated, design a **single, memory-bounded private cohort reconstruction**, rather than another round of independently truncated procedure and diagnosis prefixes. No Step 44 result establishes MRI use or a sex/race disparity. Keep PR #1 draft and unmerged pending public-repository data-governance review.

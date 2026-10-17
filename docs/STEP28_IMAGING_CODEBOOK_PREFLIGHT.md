# Step 28: candidate imaging codebook and guarded extraction

**Fixed-data research salvage. NO new TriNetX data.**
All future analysis is confined to the original authorized Diamond ZIP and
existing complete private diagnosis/demographic/index SQLite files.

**Status: CODEBOOK CANDIDATE, NOT APPROVED FOR EXECUTION OR INFERENCE.**

## Design decisions proposed for review

- Population: earliest observed principal ICD-10-CM I63 diagnosis
  during 2018-2019, approximate age 19-50, recognized binary recorded
  sex. One index per person, **not** first-ever stroke or admission.
- Outcome: a CPT code recorded near diagnosis, not confirmed performed
  imaging at an identified hospital encounter.
- Primary window (proposed): index day plus/minus 1 calendar day;
  day 0, plus/minus 3, and plus/minus 7 days for sensitivity.
- CT head, MRI brain, CTA head/neck, MRA head/neck. Retain people with
  no matching code in the independent denominator.
- No unqualified race/ethnicity disparity claims, given >75% missing.

## Versioned candidate table

The file
[dataset/imaging_codebook_candidate_v1.csv](../dataset/imaging_codebook_candidate_v1.csv)
contains **14 exact CPT codes**:

| Class | Original nine | Additional five to review |
| --- | --- | --- |
| CT head | 70450, 70460, 70470 | none |
| MRI brain | 70551, 70552, 70553 | none |
| CTA | 70496 head | 70498 neck |
| MRA | 70544, 70545 head | 70546 head, 70547-70549 neck |

A CMS document issued in January 2012 lists these CPT codes
and their anatomical sites, so the additions are historically plausible
for 2018-19 (NOT evidence of their completeness in the Diamond source):
- [CMS 2012 Transmittal 2395, Attachment 1](https://www.cms.gov/regulations-and-guidance/guidance/transmittals/downloads/r2395cp.pdf)
- [CMS Medicare claims processing manual on MRA codes](https://www.cms.gov/Regulations-and-Guidance/Guidance/Transmittals/Downloads/R1472CP.pdf)

Do not add later-era codes indiscriminately. Coding version validity,
billing system, modifiers, dates of service, whether neck angiography
belongs in the endpoint, and non-CPT code families still require
specialist review. The script matches exact code-system/code pairs:
CPT 70498 does not automatically imply HCPCS 70498. ICD-10-PCS mappings
are NOT approved or added.

## Safe preflight: zero SOURCE clinical rows scanned

From the study workstation, in the repository root:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q

python scripts/step28_imaging_extract.py \
  --plan \
  --zip ../../../../datasets/TriNetX/dataset_64b01b62c6dca15375ae9828_stroke.zip \
  --private-dir ../../../../datasets/TriNetX/young_stroke_private/chained_v1 \
  --output results/phase1/step28_codebook_plan.json
```

The --plan path validates the original source ZIP fingerprint,
manifest-declared procedure row count, completed index and imaging DBs
and candidate codebook. It reads eligible IDs from an approved private
SQLite index, but reads no original ZIP clinical source rows. It
writes only aggregate metadata and explicitly sets
approval_status: NOT_APPROVED. It performs **no 1.17 billion-row scan**.

Review the aggregate JSON for metadata disclosure before sharing.
Never upload the original ZIP, private SQLite or patient-level data.

## Full extraction design: DO NOT RUN before actual sign-off

The script includes an --execute mode for ONE future sequential
procedure.csv scan from the EXISTING ZIP, which is not authorized yet.
Execution requires:

1. The lead investigator and stroke clinician review every included
   code and sign off on head/neck definitions, population,
   recorded-code outcome, primary and sensitivity windows.
2. Data stewardship review of use/sharing constraints, including
   the pre-existing patient-level file in public Git history.
3. Set clinical_review=approved for EVERY included CSV row.
4. Create a separate LOCAL approval JSON OUTSIDE Git with
   decision=approved, two named reviewers, date,
   exactly matching codebook_sha256 and archive_members_sha256
   fingerprints provided by --plan, fixed population identifier,
   windows and nonadmission design.
5. Only then invoke --execute --approval /local/authorized/file.json.
   Prior/partial runs and mismatched source/codebook are refused.
   Review fields are a software safety stop, not cryptographic
   signatures or proof of institutional authorization.

After approval, the single scan writes code-specific patient/date/modality
data to a private SQLite DB outside Git. It verifies that no prior
nine-code patient/modality/day match was lost, checks full manifest row
count, and computes the same-day, +/-1, +/-3, and +/-7-day
modality-group counts. No clinical rows appear in returned JSON.
These remain **temporal code matches, not confirmed admissions**.

## Anatomical reporting safeguards (added after preflight)

The future Step 28 extraction report will now summarize both
**head-only recorded CTA/MRA** (the working primary endpoints) and
**head-plus-neck recorded CTA/MRA** (expanded sensitivity), using
the *same private exact-code event database*. Brain CT/MRI are
separate outcomes in both. Neck CTA/MRA without a corresponding
head CTA/MRA is counted separately when disclosure checks permit.

The entire anatomic comparison for an individual time window is
withheld if any positive group count or any positive nested-endpoint
difference is under 11. This is a conservative LOCAL QC protection,
not approval to release multiple tables: cross-window and other
published marginals can still create complementary disclosure risks.
The report explicitly sets aggregate_disclosure_review_required=true.
All person-level events remain private outside Git.

The updated source has additional fail-closed checks for anatomical
modality labels (before any expensive scan) and rejects approval
JSONs saved inside the Git repository. The candidate CSV and its
SHA256 fingerprint remain unchanged from the already completed
Step 28 preflight. The **new tests still require local execution**.

## Go/no-go after expansion

Evaluate whether matching-code coverage and source observation are
sufficient for the narrower research question. If the unmatched
fraction remains high without defensible explanation, switch to a
methods/data-quality study or discontinue imaging-disparity inference.
No models or manuscript changes are authorized here. PR stays draft.

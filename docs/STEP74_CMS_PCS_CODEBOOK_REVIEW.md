# Step74: Official CMS ICD-10-PCS titles versus observed cohort code profiles

**Status (2026-10-20):** Completed successfully on the
investigator's authorized workstation: four synthetic Step74
tests, 708 total repository tests, and the quasi-binomial
diagnostic passed. Official CMS FY2016–FY2025
public ZIPs were downloaded, parsed and cached,
with SHA256 receipts in the LOCAL ONLY report.
The Step74 source procedure crosswalk completed
read-only using already captured exact-code
source-row counts. No clinical source ZIP was
rescanned or private database modified.

**Important denominator correction (documented
before any patient-level interpretation):**
Step74's `all_PCS_source_rows` covers
EVERY ICD-10-PCS section, whereas the official
CMS title parser deliberately retained **only
section B (Imaging)**. Consequently the
percentage `valid_neighbor_FY_rows / all_PCS_source_rows`
is NOT a valid percentage of correctly mapped
all-PCS codes. The [Step75 B-section denominator
audit](STEP75_PCS_SECTION_DENOMINATOR_AUDIT.md)
correctly decomposes source non-B, B-syntax-valid,
B-CMS-matched and B-review-candidate rows,
using only the existing cached data.
The Step74 candidate counts remain unvalidated
source rows across overlapping cohorts, not
confirmed imaging in distinct patients.

## Why this step is different

Steps72 and 73 completed locally and returned 17/17 converged models
with 704 total tests passing after Step73. They show associations
in the **recording of 14 chosen CPT codes**, not necessarily actual
imaging care. Some race-category code-capture differences persist
across several assumptions; others change substantially with
same-day encounter expansion and exclusions. The working-binomial
nominal 95% intervals should **not** be called final precision:
most grouped models have deviance/df above 1, there is no
hospital clustering or stroke severity, and small P×quarantine
strata remain for AIAN. A statistically narrow interval cannot
repair a possibly mismeasured outcome.

Step74 addresses the highest-value remaining **outcome definition
gap**: whether additional documented neuroimaging may be coded
under ICD-10-PCS. We do not want another 993-million-row source scan.

## Official public sources

The script fetches **official CMS ICD-10-PCS code-title ZIPs**
for FY2016 through FY2025, by finding the named links on
the two CMS code/archive pages:

- https://www.cms.gov/medicare/coding-billing/icd-10-codes
- https://www.cms.gov/medicare/coding-billing/icd-10-codes/icd-10-cm-icd-10-pcs-gem-archive

FY2016 uses the CMS 'PCS Long and Abbreviated Titles'
package, and later years the official 'ICD-10-PCS Codes
File' packages. Packages are cached in a PRIVATE,
permission-restricted folder and archived by SHA256.
The program verifies ZIP format and minimum official
ICD-10-PCS section-B title availability before inspecting
any locally held matched code frequencies.

**Important:** ICD-10-PCS validity officially follows
effective inpatient discharge dates, which have FY
boundaries on October 1 and some interim updates. Step68
retained per-code `service_year` but not the precise
discharge date in its code-profile table. Therefore, a
calendar-year profile is matched to titles from FY year Y
or FY year Y+1 as a **coarse discovery screen only**.
This does NOT prove a code valid on an individual event's
discharge date or establish a clinical case definition.
The CMS files may also have interim modifications
(for instance April 2024).

## Conservative automated screen

The parser compares the existing Step68 private
`capture.code_profile` for ICD-10-PCS exact
seven-character codes, separated by procedure
calendar year, P indicator and context
(`INDEX_IMP`, `NONIMP_DAY0`, `UNIQUE_ED`).
They are **source row frequencies with duplicated
cohort membership**, NOT patients.

A code receives a **REVIEW ONLY** tag only when:

1. The **full exact seven-character code** appears
   in an official CMS code-title file for at least
   one neighboring FY version; and
2. Its table begins `B02` (CNS CT), `B03`
   (CNS MR), `B32` (upper-arterial CT)
   or `B33` (upper-arterial MR); and
3. Its published title contains a plausible brain,
   cerebral, intracranial, carotid, vertebral,
   head or neck body-part description.

A code beginning `B24` (heart ultrasonography),
`B31` (upper artery fluoroscopy), or any other
family is not automatically counted as the
specified brain CT/MRI/CTA/MRA endpoint.
Likewise, a `B02/B03/B32/B33` prefix alone
never qualifies. A candidate code is not equivalent
to a CPT14 procedure and cannot yet be added
to a patient imaging numerator without a
reviewed clinical codebook and encounter-level
patient assignment.

Outputs contain three components:

- Printed terminal-only row-level source-code
  **aggregate** coverage by P, service year, and
  context with no exact source codes or
  identifiers.
- A LOCAL ONLY JSON containing the exact
  observed codes, full public CMS titles,
  official archive URLs and SHA256, *source
  code row frequencies*, and review-only
  category candidates. This contains source-derived
  measurements and **must not be uploaded
  or committed** without approval.
- A second modeling diagnostic that refits
  Step73's original primary-cohort grouped
  binomial models and inflates nominal
  delta-method CI half-widths by
  `sqrt(max(1, deviance / residual_df))`
  as a rough quasi-binomial overdispersion
  sensitivity. It does **NOT** account for
  hospital clusters, measurement bias or
  uncontrolled patient mix.

## One combined run (network needed ONLY for public CMS ZIPs)

```bash
(
  set -e
  git pull --ff-only origin analysis-rebuild-phase1-audit
  python -m py_compile scripts/step74_cms_pcs_codebook_review.py
  python -m pytest -q tests/test_step74_cms_pcs_codebook_review.py
  python -m pytest -q
  python scripts/step74_cms_pcs_codebook_review.py
)
```

If a synthetic test fails, this block stops before any data
analysis. If the public CMS site cannot be reached or
one of its ZIP layouts differs from the tested parser,
the program prints `CMS PUBLIC DOWNLOAD/FORMAT BLOCKER`,
does not modify any clinical database and stops. Previously
downloaded official public ZIPs remain cached locally;
fix the downloader rather than reprocessing source data.

**Handoff: TERMINAL OUTPUT ONLY.** Do NOT ZIP or upload
the existing private SQLite files or Step74 source-
derived JSON. If the CMS download is blocked, send
the error lines printed by the program.

Private output file (not requested for upload):

`results/phase1/full_reconstruction_private/step74_public_cms_private/step74_cms_pcs_crosswalk_LOCAL_ONLY.json`

## Decision gate

- If exact CMS titles indicate many candidate
  nervous-system/upper-artery image-code rows,
  clinically review those codes and release
  an **approved public-only codebook** listing
  code, year, exact description, targeted
  modality, exclusion/inclusion rationale,
  and source version.
- Then decide how to link PCS records to frozen
  indexed patients: Step68 stores non-CPT14
  per-code *row counts*, not patient-level
  flags, so an expanded patient-level
  capture endpoint would require a separately
  justified, targeted source processing pass.
  Do not imply a change in patient imaging
  capture based solely on these code frequencies.
- If these code systems are rare or inapplicable,
  retain frozen CPT14 code-capture endpoint
  with explicit limitations.
- No further adjusted demographic GLMs
  should be presented as final clinical
  disparity estimates until the codebook
  and primary outcome hierarchy are frozen.

No routine contact with TriNetX is required for
this public-documentation and local-source-data check.

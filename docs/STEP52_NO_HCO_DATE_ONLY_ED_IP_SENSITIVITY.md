# Step 52: Predeclared date-only ED→inpatient sensitivity (no verified hospital key)

**Status: synthetic-only code and protocol, not a real-data analysis.** The preceding Step51 inspection succeeded locally with **381 passing tests, three unchanged warnings**; headers from 18 CSV members contained `source_id` and unrelated oncology tumor-site fields, but no explicit HCO/hospital/parent-episode key. We cannot certify that any two encounter IDs refer to a single hospital stay. This lack of a clearly identified key in the ZIP headers is **not** proof that a reliable mapping does not exist outside the export.

## Study outcomes to compare, WITHOUT assuming a validated HCO key

For each of the **two previously specified co-primary age cohorts**, report the following *when approved data are eventually available*:

| Outcome definition | Concept | Interpretation |
|---|---|---|
| **A. Same-inpatient-encounter reference** | Imaging recorded on the identified `IMP` encounter ID, using clinically reviewed performed-imaging codes | Higher linkage specificity, but may miss imaging performed before admission in the ED |
| **B. Candidate peri-admission ED + inpatient sensitivity** | A plus imaging codes on exactly one qualifying earlier `EMER` encounter for the same patient with adjacent dates | **Unverified patient-and-date association**, not proven same-hospital imaging; subject to false matches and missing ED codes |
| **C. Date-window sensitivities** | Compare B at 0 days, 0–1 days, 0–2 calendar days between `EMER.end_date` and `IMP.start_date` | Assess how assumptions alter documented imaging rates and sex/race contrasts |

**The eventual primary endpoint choice is not settled by this automated step.** The investigator wants ED imaging included, but we cannot equate an unverified date-only match with a confirmed hospital episode. The final primary-versus-sensitivity designation requires study/clinical/data-steward approval and a data-quality assessment. Do not silently replace the intended hospitalized stroke denominator, which is based on inpatient eligibility independent of imaging.

## Conservative candidate eligibility

The **same patient ID** (scope/harmonization *unverified*), distinct encounter IDs, `EMER` and `IMP` type labels (meaning still requires signoff), parseable ED `start_date`/`end_date` and inpatient `start_date` are necessary. Index hospitalization selection remains **independent of whether imaging exists**.

Use `0 <= (IMP.start_date - ED.end_date).days <= 1` as the proposed 0–1-calendar-day date rule; the ED could start earlier. Compare 0 and 2-day limits. Calendar dates are **not elapsed 24- or 48-hour windows** and a same-day match does not establish visit order. Reject or hold malformed dates, negative stays, overlaps, missing ED end date and events beginning after admission.

Exactly one ED→IP candidate is required *in both directions*: no multiple EDs for one IP and no one ED for multiple candidate IPs. Duplicate encounter keys or encounter IDs used across different patients, plausible ED competitors with unresolved date/site, and cross-site mismatch when independently verified site identifiers are supplied are held, never greedily resolved. Do not infer HCO identity from `source_id`. A site mismatch is not proof that encounters are unrelated; it may reflect a real transfer, which cannot be resolved here.

The labels `date_only_possible_ED_IP_NOT_VERIFIED_SAME_HOSPITAL` and `date_only_unique_provisional_REQUIRES_ID_SCOPE_AND_LINKAGE_VALIDATION` intentionally prevent a date candidate from being promoted to a proven admission. The Step49 strict site-aware helper stays unchanged.

## Code and synthetic verification

- `scripts/step52_date_only_ed_ip_sensitivity.py`: `date_only_pair_candidate`, `resolve_date_only_candidates`, `date_only_window_summary`, `outcome_definition_labels`.
- `tests/test_step52_date_only_ed_ip_sensitivity.py`: invented records test the 0/1/2-day windows, longer ED duration, competing EDs/IPs, impossible dates, missing site and misleading `source_id`, conflicting verified hospital keys, encounter-ID collision, no leakage of IDs into *in-memory* aggregate summaries, and nonmutation of inputs.
- Pure Python functions may process caller-supplied in-memory records, so **do not pass real clinical encounters without institutional permission**. The module itself never opens data files or scans the original ZIP. Outputs containing private patient+encounter keys must remain in approved, Git-ignored storage only if an authorized caller later persists them.

Run **tests only** on the study workstation:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
```

No extra Step51 header scan is needed. Do not run the superseded Step45 clinical scan.

## What must be demonstrated before publication or a full scan

1. Data stewardship: whether `patient_id` identifies the same person across HCOs, `encounter_id` collision scope, what `source_id` actually means, and how encounter labels/dates are constructed. Request any provider-specific site or encounter mapping external to the CSV export.
2. Reviewer-signed reference codebooks for brain MRI, CTA head/neck, MRA head/neck, CT head comparator, performed-vs-ordered status and relevant procedure code systems. Literature-supported code families are not automatically valid in each data source.
3. In a separately authorized, local, full-population reconstruction: report missingness, competing/ambiguous link rates, linked ED imaging contribution, differences between A/B/C, and missingness/site capture by sex, race and cohort. **Do not claim that no imaging was done** when no procedure code is recorded. An external clinical validation subset would be needed for actual match accuracy.
4. Data-owner signoff for local row-level processing, disclosure/suppression controls, index stroke diagnosis coding and handling of retinal `H34.1` and legacy ICD-9 codes.
5. Continue to keep PR #1 **draft and unmerged** until the preexisting Git history containing potentially restricted research data has been reviewed by the institution.

**Conclusion:** The date-only ED/IP association can be prespecified as a *sensitivity definition*, with the reliable same-encounter inpatient reference. The code cannot verify hospital identity or medical care episode continuity. No clinical scan has been performed or authorized by this protocol.

# Step 49: ED end-date → inpatient start-date linkage candidates

**Status:** Implemented as a pure Python, synthetic-only preparation and validation step. The previous source-wide Step45 clinical scan remains **DISABLED**. No patient data, Research Network ZIP, source clinical table or restricted codebook is touched by Step49.

## Refined time rule (proposed, not yet HCO/site-validated)

The Research Network export includes `patient_id`, `encounter_id`, `type`, `start_date` and `end_date` on `encounter.csv`. Dates are recorded as `YYYYMMDD`, without a confirmed time of day.

Compare the **emergency encounter END** against the **inpatient encounter START**. An ED visit may start days earlier; do not use its start as the principal proximity measure.

| Window | Candidate dates | Interpretation |
|---|---|---|
| 0 calendar days | `ED.end_date == IMP.start_date` | strict same-day sensitivity |
| 0–1 calendar days | `0 <= IMP.start_date - ED.end_date <= 1` | **proposed main linkage window** |
| 0–2 calendar days | `0 <= IMP.start_date - ED.end_date <= 2` | wider sensitivity |

Even a same-day date match is a **possible episode link**, not evidence that ED care preceded admission within that day. Calendar days must not be described as 24- or 48-hour intervals. A negative interval/overlap of end/start dates is held for review; do not infer the transfer order.

Require an identical, nonblank `patient_id`; a distinct `encounter_id`; `EMER` to `IMP` encounter types; parseable ED start/end and inpatient start; nonnegative visit lengths; and the **same independently verified HCO/site key**. The Research Network `source_id` must **not** be assumed to be a verified site identifier.

The pairwise rule can only assess one possible pair. A second step performs **reciprocal uniqueness**: an inpatient stay with more than one candidate ED, or an ED visit with more than one candidate inpatient stay, is marked ambiguous, not linked. Duplicate encounter IDs/rows and potential competitors with unresolved site/dates are held. No nearest-date guessing, no automatic transfer across sites, and no attachment of stand-alone ED visits to the hospitalized denominator.

## Synthetic implementation and tests

- `scripts/step49_ed_ip_episode_candidates.py`: `pair_candidate`, `resolve_episode_candidates`, and `compare_link_windows`.
- `scripts/step48_reference_stroke_ed_policy.py`: original `ed_to_ip_candidate` now delegates to the refined Step49 pairwise rule.
- `tests/test_step49_ed_ip_episode_candidates.py`: invented encounter fixtures covering long ED stays, same-day/one-/two-day windows, boundary dates across December/January, missing/invalid date, unverified or different site, two EDs for one admission, one ED for two admissions, duplicate IDs, and no patient identifiers in aggregate reporting.
- Existing Step48 and Step45 synthetic tests remain included in the normal `pytest` suite.

Use from the cloned repository:

```bash
git pull origin analysis-rebuild-phase1-audit
python -m pytest -q
```

No `--execute-full-scan`, no re-running Step46 `prepare`, and no approval editing are needed. This is a *code/test* verification only.

## How to assess reliability on permitted local data later

A **data-steward-approved** local audit must establish the true meaning and uniqueness scope of patient/encounter IDs and the existence (or not) of a stable HCO/site identifier or parent encounter/admission ID. Without verified site mapping, the rule intentionally returns a hold and does not silently accept links.

Only once those keys are grounded should a governed, **private** encounter-level assessment report the numbers of: same-day candidates, next-day candidates, two-day candidates; ambiguous multiple-ED or multiple-inpatient cases; missing date or site; conflicting overlap; and site-to-site transfers. Compare 0, 0–1 and 0–2 windows and review a securely authorized sample for positive predictive value before fixing a final linkage policy. Compare imaging flags for ED-only, inpatient-only and combined episodes under each co-primary age definition.

`compare_link_windows` returns aggregate **unsuppressed in-memory counts**, not disclosure-cleared releases. Do not publish or upload small cells, patient identifiers, private code descriptions or per-episode mappings. Any later processing/output must be restricted to the existing cloned repo's ignored `results/phase1/` as approved by the institutional data owner.

**The observed full-data matching performance is unknown.** Synthetic test success does not measure false-link rates, site coverage or clinical completeness. The Step45 source-wide real-data scan remains blocked, and PR #1 remains draft and unmerged while historical repository governance issues are resolved.

#!/usr/bin/env python3
"""Step52: patient+date ED/IP SENSITIVITY candidates when HCO key is absent.

PURE functions only; no ZIP/table reads, output files or data scans.
These mappings are not verified hospital transfers or completed care episodes.
Patient_id scope across HCOs is not established. Never label the output
"confirmed_same_hospital" or treat an ED procedure as verified inpatient.
"""
from __future__ import annotations

from collections import Counter, defaultdict

try:
    from .step49_ed_ip_episode_candidates import (
        CANDIDATE as SITE_AWARE_PAIR, UNRESOLVED, _key, _text, _window,
        pair_candidate,
    )
    from .step48_reference_stroke_ed_policy import date_only
except ImportError:
    from step49_ed_ip_episode_candidates import (
        CANDIDATE as SITE_AWARE_PAIR, UNRESOLVED, _key, _text, _window,
        pair_candidate,
    )
    from step48_reference_stroke_ed_policy import date_only

DATE_ONLY_PAIR = "date_only_possible_ED_IP_NOT_VERIFIED_SAME_HOSPITAL"
DATE_ONLY_UNIQUE = "date_only_unique_provisional_REQUIRES_ID_SCOPE_AND_LINKAGE_VALIDATION"
WINDOWS = (0, 1, 2)


def date_only_pair_candidate(ed: dict, ip: dict, max_gap_days: int = 1) -> str:
    """Use Step49's validated date arithmetic, not a fabricated site key.

    In the absence of verified HCO mapping, transform the Step49 "unknown
    hospital" hold into a *date-only* possible link. If separately verified
    site fields do exist and contradict, fail closed on the cross-site link.
    source_id is deliberately never consulted.
    """
    result = pair_candidate(ed, ip, max_gap_days)
    if result in (SITE_AWARE_PAIR, "hold_site_mapping_unverified"):
        return DATE_ONLY_PAIR
    return result


def resolve_date_only_candidates(eds, ips, max_gap_days: int = 1):
    """Return in-memory private per-IP candidates with reciprocal uniqueness.

    Keys contain patient IDs; NEVER print/share results or commit them.
    A valid date-only candidate may be reviewed as a sensitivity record,
    NOT used as evidence of the true shared hospital or episode.
    """
    _window(max_gap_days)
    eds, ips = tuple(eds), tuple(ips)
    if any(not isinstance(r, dict) for r in eds + ips):
        raise TypeError("Encounter inputs must be dictionaries")
    keys = [_key(row) for row in eds + ips]
    duplicated = {k for k, n in Counter(k for k in keys if all(k)).items() if n > 1}
    encounter_scope = defaultdict(set)
    for patient, enc in keys:
        if patient and enc:
            encounter_scope[enc].add(patient)
    cross_patient_encounters = {k for k, people in encounter_scope.items()
                                if len(people) > 1}
    ed_by_patient = defaultdict(list)
    for ed in eds:
        ed_by_patient[_key(ed)[0]].append(ed)
    proposed = defaultdict(list)
    unresolved = defaultdict(list)
    for ip in ips:
        ipkey = _key(ip)
        if not all(ipkey):
            continue
        for ed in ed_by_patient[ipkey[0]]:
            outcome = date_only_pair_candidate(ed, ip, max_gap_days)
            if outcome == DATE_ONLY_PAIR:
                proposed[ipkey].append(_key(ed))
            elif outcome in UNRESOLVED:
                unresolved[ipkey].append(outcome)
    inverse = defaultdict(set)
    for ipkey, candidates in proposed.items():
        for edkey in candidates:
            inverse[edkey].add(ipkey)
    result = {}
    for ip in ips:
        ipkey = _key(ip)
        if not all(ipkey):
            continue
        choices = proposed[ipkey]
        linked_ed = None
        if ipkey in duplicated or any(edkey in duplicated for edkey in choices):
            status = "hold_duplicate_patient_encounter_key"
        elif (ipkey[1] in cross_patient_encounters or
              any(edkey[1] in cross_patient_encounters for edkey in choices)):
            status = "hold_encounter_id_reused_across_patients"
        elif len(set(choices)) > 1:
            status = "ambiguous_multiple_ED_candidates"
        elif len(choices) == 1 and len(inverse[choices[0]]) > 1:
            status = "ambiguous_one_ED_multiple_IP"
        elif unresolved[ipkey]:
            status = "hold_unresolved_possible_ED"
        elif len(choices) == 1:
            status = DATE_ONLY_UNIQUE
            linked_ed = choices[0]
        else:
            status = "no_unique_date_only_ED_candidate"
        if ipkey in result:
            result[ipkey] = {
                "status": "hold_duplicate_patient_encounter_key",
                "emergency_key": None, "calendar_gap_days": None,
                "same_hospital_verified": False,
            }
            continue
        gap = None
        if linked_ed:
            ed = next(row for row in ed_by_patient[ipkey[0]] if _key(row) == linked_ed)
            gap = (date_only(_text(ip, "start_date")) -
                   date_only(_text(ed, "end_date"))).days
        result[ipkey] = {
            "status": status, "emergency_key": linked_ed,
            "calendar_gap_days": gap,
            "same_hospital_verified": False,
        }
    return result


def date_only_window_summary(eds, ips, windows=WINDOWS):
    """In-memory counts only. Counts require cell-suppression before release."""
    eds, ips = tuple(eds), tuple(ips)
    result = {}
    for days in windows:
        _window(days)
        links = resolve_date_only_candidates(eds, ips, days)
        counts = Counter(row["status"] for row in links.values())
        gaps = Counter(row["calendar_gap_days"] for row in links.values()
                       if row["status"] == DATE_ONLY_UNIQUE)
        result[str(days)] = {
            "inpatient_records_submitted": len(ips),
            "inpatient_keys_classified": len(links),
            "status_counts": dict(sorted(counts.items())),
            "unique_date_only_provisional_candidates": counts[DATE_ONLY_UNIQUE],
            "provisional_gap_days_counts": dict(sorted(gaps.items())),
            "same_hospital_verified": False,
            "patient_id_cross_hco_scope_verified": False,
            "source_archive_or_clinical_files_opened": False,
            "outcome": "SENSITIVITY_ONLY_NOT_CONFIRMED_ED_IP_TRANSFER",
        }
    return result


def outcome_definition_labels():
    """Investigator-selected endpoint priority; NOT a data-use authorization.

    Both co-primary age cohorts apply independently to the same definitions.
    The primary numerator must NEVER include a different ED encounter.
    """
    return (
        "same_inpatient_encounter_documented_imaging_PRIMARY_REFERENCE",
        "inpatient_plus_date_only_unique_ED_imaging_PROVISIONAL_SENSITIVITY",
        "ED_date_window_0_1_2_calendar_days_SENSITIVITY",
    )


def investigator_analysis_contract():
    """Frozen investigator decision for a future approved reconstruction.

    Describes planned recorded-procedure outcomes, not actual imaging receipt.
    No patient records or clinical codebooks are accessed by this helper.
    A site-unverified ED match is usable only as a labeled sensitivity.
    """
    return {
        "study_outcome": "documented_imaging_codes_not_confirmed_receipt",
        "primary": {
            "key": "A_same_IMP_encounter",
            "role": "primary",
            "procedure_encounter_types": ("IMP",),
            "may_include_separate_ED_encounter": False,
        },
        "sensitivity": {
            "key": "B_IMP_plus_unique_provisional_ED",
            "role": "sensitivity",
            "procedure_encounter_types": ("IMP", "EMER"),
            "may_include_separate_ED_encounter": True,
            "ED_linkage_requires_reciprocal_uniqueness": True,
            "ED_to_IP_main_gap_calendar_days": (0, 1),
            "ED_to_IP_window_sensitivity_max_gap_days": (0, 1, 2),
            "same_hospital_verified": False,
        },
        "co_primary_age_cohorts": (
            "uniform_18_50", "original_sex_specific_18_52_54"
        ),
        "denominator_selected_independent_of_imaging": True,
        "clinical_codebook_review_complete": False,
        "institutional_full_scan_authorized_by_this_decision": False,
    }

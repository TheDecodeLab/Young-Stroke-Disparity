#!/usr/bin/env python3
"""Step49: date-only ED-to-inpatient candidate linkage, SYNTHETIC/PURE ONLY.

No file reads, clinical source scans, network operations or persisted outputs.
Input records are dictionaries with encounter_id, patient_id, type, start_date,
end_date, and a verified_site_key SUPPLIED ONLY AFTER independent validation.
Results are provisional research candidates, never proven transfers/admissions.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from typing import Dict, Iterable, Tuple

if __package__:
    from .step48_reference_stroke_ed_policy import date_only
else:
    from step48_reference_stroke_ed_policy import date_only

CANDIDATE = "candidate_same_site_nearby_ED_IP_REQUIRES_VALIDATION"
WINDOWS = (0, 1, 2)
UNRESOLVED = frozenset({
    "hold_site_mapping_unverified",
    "hold_overlapping_episode_timing",
    "hold_missing_ED_end_date",
    "hold_missing_or_invalid_dates",
    "hold_bad_emergency_interval",
    "hold_bad_inpatient_interval",
    "hold_different_site_or_transfer",
})
EPISODE_CANDIDATE = "unique_temporal_candidate_REQUIRES_SITE_AND_CLINICAL_VALIDATION"


def _text(row, key):
    return str(row.get(key) or "").strip()


def _key(row):
    return (_text(row, "patient_id"), _text(row, "encounter_id"))


def _window(max_gap_days):
    # Limit is calendar days between ED END and IP START, not elapsed hours.
    if type(max_gap_days) is not int or max_gap_days not in (0, 1, 2, 3):
        raise ValueError("max_gap_days must be 0, 1, 2, or 3")


def pair_candidate(ed: dict, admission: dict, max_gap_days: int = 1) -> str:
    """Assess a single ED -> inpatient record pair, without presuming uniqueness.

    Complete ED end date is required. Long ED stays can still link when the
    ED END date is adjacent to inpatient admission. An ED beginning after
    admission, negative duration, and dates after admission are not linked.
    """
    _window(max_gap_days)
    ed_pid, ed_id = _key(ed)
    ip_pid, ip_id = _key(admission)
    if not ed_pid or not ip_pid or ed_pid != ip_pid:
        return "reject_patient_id"
    if not ed_id or not ip_id or ed_id == ip_id:
        return "reject_invalid_or_same_encounter_id"
    if _text(ed, "type").upper() != "EMER":
        return "reject_not_EMER"
    if _text(admission, "type").upper() != "IMP":
        return "reject_not_IMP"
    ed_start = date_only(_text(ed, "start_date"))
    ip_start = date_only(_text(admission, "start_date"))
    if ed_start is None or ip_start is None:
        return "hold_missing_or_invalid_dates"
    ed_end_value = _text(ed, "end_date")
    if not ed_end_value:
        return "hold_missing_ED_end_date"
    ed_end = date_only(ed_end_value)
    if ed_end is None:
        return "hold_missing_or_invalid_dates"
    ip_end_raw = _text(admission, "end_date")
    ip_end = date_only(ip_end_raw) if ip_end_raw else None
    if ip_end_raw and ip_end is None:
        return "hold_missing_or_invalid_dates"
    if ed_end < ed_start:
        return "hold_bad_emergency_interval"
    if ip_end and ip_end < ip_start:
        return "hold_bad_inpatient_interval"
    if ed_start > ip_start:
        return "reject_emergency_starts_after_admission"
    if ed_end > ip_start:
        return "hold_overlapping_episode_timing"
    gap = (ip_start - ed_end).days
    if gap > max_gap_days:
        return "not_adjacent_in_requested_window"
    # source_id is NOT an HCO identifier. Only separately verified mapping.
    site_ed = _text(ed, "verified_site_key")
    site_ip = _text(admission, "verified_site_key")
    if not site_ed or not site_ip:
        return "hold_site_mapping_unverified"
    if site_ed != site_ip:
        return "hold_different_site_or_transfer"
    return CANDIDATE


def resolve_episode_candidates(
    emergency_encounters: Iterable[dict],
    inpatient_encounters: Iterable[dict],
    max_gap_days: int = 1,
) -> Dict[Tuple[str, str], dict]:
    """Match only unambiguous *provisional* ED/IP candidate pairs.

    Return keys are PRIVATE patient_id+IP encounter_id pairs; never export
    outside an institution-approved patient-level workspace. No source I/O.
    Every admission is represented, even if it has no candidate ED.
    Ambiguous patient-level encounter duplicates, competing EDs, or multiple
    prospective recipient admissions block unique linkage rather than using
    nearest-date tie-breaking.
    """
    _window(max_gap_days)
    eds, ips = list(emergency_encounters), list(inpatient_encounters)
    for encounter in eds + ips:
        if not isinstance(encounter, dict):
            raise TypeError("Each encounter must be a dictionary")
    duplicates = Counter(_key(row) for row in eds + ips if all(_key(row)))
    duplicates = {key for key,n in duplicates.items() if n > 1}
    id_patients = defaultdict(set)
    for row in eds + ips:
        patient, encounter = _key(row)
        if patient and encounter:
            id_patients[encounter].add(patient)
    colliding_encounter_ids = {
        encounter for encounter, patients in id_patients.items()
        if len(patients) > 1
    }
    by_patient_ed = defaultdict(list)
    by_patient_ip = defaultdict(list)
    for row in eds:
        by_patient_ed[_text(row, "patient_id")].append(row)
    for row in ips:
        by_patient_ip[_text(row, "patient_id")].append(row)
    links = defaultdict(list)
    uncertainty = defaultdict(list)
    for ip in ips:
        ip_key = _key(ip)
        if not all(ip_key):
            continue
        for ed in by_patient_ed[ip_key[0]]:
            ed_key = _key(ed)
            reason = pair_candidate(ed, ip, max_gap_days)
            if reason == CANDIDATE:
                links[ip_key].append(ed_key)
            elif reason in UNRESOLVED:
                # If start/end is incomplete, the temporal relationship is
                # unknown. Do not certify a competing "unique" match.
                uncertainty[ip_key].append(reason)
    # An ED could also be a candidate for more than one IP. No greedy matching.
    by_ed = defaultdict(list)
    for ip_key, ed_keys in links.items():
        for ed_key in ed_keys:
            by_ed[ed_key].append(ip_key)
    result = {}
    for ip in ips:
        key = _key(ip)
        if not all(key):
            continue
        choices = links[key]
        if key in duplicates:
            status = "hold_duplicate_patient_encounter_key"
            choice = None
        elif key[1] in colliding_encounter_ids or any(
                ed_key[1] in colliding_encounter_ids for ed_key in choices):
            status = "hold_encounter_id_reused_across_patients"
            choice = None
        elif any(ed_key in duplicates for ed_key in choices):
            status = "hold_duplicate_patient_encounter_key"
            choice = None
        elif len(set(choices)) > 1:
            status = "ambiguous_multiple_ED_candidates"
            choice = None
        elif len(choices) == 1 and len(set(by_ed[choices[0]])) > 1:
            status = "ambiguous_one_ED_multiple_IP"
            choice = None
        elif uncertainty[key]:
            status = "hold_unresolved_potential_ED_competitor"
            choice = None
        elif len(choices) == 1:
            status = EPISODE_CANDIDATE
            choice = choices[0]
        else:
            status = "no_unique_ED_candidate"
            choice = None
        if key in result:
            # Multiple IP rows share a patient+encounter identifier.
            result[key] = {"status": "hold_duplicate_patient_encounter_key",
                           "emergency_key": None, "calendar_gap_days": None}
            continue
        gap = None
        if choice is not None:
            # Resolve only from the matched encounter (not the first visit).
            ed_row = next(ed for ed in by_patient_ed[key[0]] if _key(ed) == choice)
            gap = (date_only(_text(ip, "start_date")) -
                   date_only(_text(ed_row, "end_date"))).days
        result[key] = {"status": status, "emergency_key": choice,
                       "calendar_gap_days": gap}
    return result


def compare_link_windows(emergency_encounters, inpatient_encounters, windows=WINDOWS):
    """Aggregate diagnostics for locally governed use; no external release.

    Returns only counts, never IDs. Use institutional small-cell suppression
    before disclosure. Converts sources to tuples for repeatable windows.
    """
    eds, ips = tuple(emergency_encounters), tuple(inpatient_encounters)
    out = {}
    for window in windows:
        _window(window)
        links = resolve_episode_candidates(eds, ips, window)
        out[str(window)] = {
            "inpatient_records_examined": len(ips),
            "status_counts": dict(sorted(Counter(
                link["status"] for link in links.values()
            ).items())),
            "unique_provisional_links": sum(
                link["status"] == EPISODE_CANDIDATE for link in links.values()
            ),
            "candidate_end_to_start_gap_days": dict(sorted(Counter(
                link["calendar_gap_days"] for link in links.values()
                if link["status"] == EPISODE_CANDIDATE
            ).items())),
            "clinical_episode_linkage_validated": False,
            "verified_site_mapping_supplied_by_caller": "required_not_inferred",
        }
    return out

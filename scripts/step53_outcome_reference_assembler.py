#!/usr/bin/env python3
"""Step53: pure reference assembler for the confirmed A-primary/B-sensitivity.

SYNTHETIC TESTS / DESIGN ONLY. No ZIP, database, file I/O, reporting or
authorization logic. Inputs are assumed to be preselected index admissions
and reviewed, recorded-performed imaging events. Do not pass real clinical
records without separate institutional data-owner approval. This is NOT a
production full-population cohort builder or clinical codebook validator.
"""
from __future__ import annotations

from collections import defaultdict

try:
    from .step48_reference_stroke_ed_policy import date_only
    from .step52_date_only_ed_ip_sensitivity import (
        DATE_ONLY_UNIQUE, resolve_date_only_candidates, investigator_analysis_contract,
    )
except ImportError:
    from step48_reference_stroke_ed_policy import date_only
    from step52_date_only_ed_ip_sensitivity import (
        DATE_ONLY_UNIQUE, resolve_date_only_candidates, investigator_analysis_contract,
    )

CATEGORIES = frozenset({
    "MRI_BRAIN", "CTA_HEAD", "CTA_NECK", "MRA_HEAD", "MRA_NECK", "CT_HEAD"
})
WINDOWS = (0, 1, 2)


def _field(row, name):
    return str(row.get(name) or "").strip()


def _visit_key(row):
    return (_field(row, "patient_id"), _field(row, "encounter_id"))


def _visit_interval(row):
    start = date_only(_field(row, "start_date"))
    end = date_only(_field(row, "end_date"))
    if start is None or end is None or end < start:
        return None
    return (start, end)


def _reviewed_event_map(events):
    """Require caller-provided, independently reviewed performed-code status.

    This helper does NOT validate procedure codes or their meaning. The
    reviewed flag is for testable provenance, not a substitute for signoff.
    """
    mapping = defaultdict(list)
    for event in events:
        if not isinstance(event, dict):
            raise TypeError("Procedure events must be dictionaries")
        key = _visit_key(event)
        if not all(key):
            raise ValueError("Procedure event missing patient/encounter key")
        if event.get("codebook_reviewed_performed") is not True:
            raise ValueError("Imaging event lacks explicit reviewed-performed flag")
        category = _field(event, "category")
        if category not in CATEGORIES:
            raise ValueError("Imaging category unknown or not approved in design")
        day = date_only(_field(event, "date"))
        if day is None:
            raise ValueError("Procedure event date missing or invalid")
        mapping[key].append((day, category))
    return mapping


def _in_window(events_by_visit, key, span, latest=None):
    if span is None:
        return frozenset()
    lo, hi = span
    if latest is not None:
        hi = min(hi, latest)
    return frozenset(
        category for day, category in events_by_visit.get(key, ())
        if lo <= day <= hi
    )


def assemble_outcome_reference(index_admissions, all_inpatient_encounters,
                               all_emergency_encounters, imaging_events):
    """In-memory A/B modality flags, not a full-data pipeline.

    IMPORTANT: all inpatient encounters for candidate patients are required
    for reciprocal ED ambiguity checks, not just selected index admissions.
    The index set must already have been derived WITHOUT using imaging.
    Returns PATIENT-LEVEL data in memory: never print, upload or commit it.
    """
    contract = investigator_analysis_contract()
    if contract["primary"]["may_include_separate_ED_encounter"]:
        raise RuntimeError("Primary outcome contract unexpectedly includes ED")
    index, inpatients, eds = (
        tuple(index_admissions), tuple(all_inpatient_encounters),
        tuple(all_emergency_encounters)
    )
    if any(not isinstance(x, dict) for x in index + inpatients + eds):
        raise TypeError("Encounter/index records must be dictionaries")
    by_ip = {}
    for ip in inpatients:
        key = _visit_key(ip)
        if not all(key) or key in by_ip:
            raise ValueError("Inpatient encounter key absent or duplicated")
        if _field(ip, "type").upper() != "IMP":
            raise ValueError("Inpatient pool has non-IMP encounter")
        by_ip[key] = ip
    by_ed = {}
    for ed in eds:
        key = _visit_key(ed)
        if not all(key) or key in by_ed:
            raise ValueError("ED encounter key absent or duplicated")
        if _field(ed, "type").upper() != "EMER":
            raise ValueError("ED pool has non-EMER encounter")
        by_ed[key] = ed
    if set(by_ip).intersection(by_ed):
        raise ValueError("An encounter key cannot be both IMP and EMER")
    events_by_visit = _reviewed_event_map(imaging_events)
    links = {window: resolve_date_only_candidates(eds, inpatients, window)
             for window in WINDOWS}
    out = {}
    for indexed in index:
        cohort = _field(indexed, "cohort")
        ipkey = _visit_key(indexed)
        if cohort not in contract["co_primary_age_cohorts"]:
            raise ValueError("Unknown co-primary age definition")
        if ipkey not in by_ip:
            raise ValueError("Preselected index does not match an IMP encounter")
        result_key = (cohort, ipkey[0])
        if result_key in out:
            raise ValueError("Duplicate patient index within one age cohort")
        # Key, dates and type must be compatible with the selected index.
        # A separate indexed date field (if given) must not disagree.
        ip = by_ip[ipkey]
        if _field(indexed, "start_date") and (
                _field(indexed, "start_date") != _field(ip, "start_date")):
            raise ValueError("Index admission start disagrees with encounter")
        inpatient_interval = _visit_interval(ip)
        primary = _in_window(events_by_visit, ipkey, inpatient_interval)
        sensitivity = {}
        for window in WINDOWS:
            linked = links[window].get(ipkey, {})
            status = linked.get("status", "no_unique_date_only_ED_candidate")
            included = set(primary)
            matched = None
            if (inpatient_interval is not None and status == DATE_ONLY_UNIQUE):
                edkey = linked["emergency_key"]
                ed = by_ed[edkey]
                ed_interval = _visit_interval(ed)
                included.update(_in_window(
                    events_by_visit, edkey, ed_interval,
                    latest=inpatient_interval[0],
                ))
                matched = edkey
            sensitivity[window] = {
                "recorded_modalities": tuple(sorted(included)),
                "candidate_link_status": status,
                "provisional_ED_used": matched is not None,
                "same_hospital_verified": False,
            }
        out[result_key] = {
            "index_inpatient_key": ipkey,
            "primary_assessable": inpatient_interval is not None,
            "primary_recorded_modalities": tuple(sorted(primary)),
            "date_only_ED_sensitivity_by_max_gap": sensitivity,
            "denominator_from_preselected_index_not_imaging": True,
            "clinical_episode_linkage_verified": False,
        }
    return out

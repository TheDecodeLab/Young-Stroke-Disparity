#!/usr/bin/env python3
"""Research Network pre-reconstruction decision contract, PLANNING ONLY.

Contains static requirements and pure functions for reviewing statements
that other authorized people provide. NO patient data, ZIP handling, file I/O,
approval mutation or clinical execution. A complete checklist is NOT a
legal/institutional authorization or clinical-data scan permit.
"""
from __future__ import annotations

from datetime import date

STUDY = "young_stroke_research_network"
START_YEAR = 2016
REQUIRED_EVIDENCE = {
    "institutional_data_use_scope": "governance",
    "encrypted_storage_and_access_controls": "governance",
    "legacy_git_history_privacy_review": "governance",
    "source_export_identity_and_integrity": "provenance",
    "observed_calendar_year_and_hco_completeness": "coverage",
    "research_network_imp_emer_semantics": "clinical_semantics",
    "diagnosis_code_principal_flag_and_retinal_policy": "clinical_semantics",
    "patient_encounter_id_uniqueness_scope": "linkage",
    "hospital_or_episode_linkage_key_availability": "linkage",
    "procedure_code_systems_and_event_recording_semantics": "measurement",
    "approved_year_aware_imaging_codebook": "measurement",
    "age_yob_and_sex_specific_cohort_policy": "clinical_semantics",
    "quality_and_small_cell_disclosure_plan": "governance",
    "approved_execution_environment_and_staged_resource_plan": "governance",
}
DOCUMENTED_ABSENCE_ALLOWED = frozenset({
    "hospital_or_episode_linkage_key_availability",
})
STATES = frozenset({"confirmed_external", "pending", "rejected", "documented_absent"})


def evaluate_evidence(declarations):
    """Audit externally supplied claims without certifying them.

    Input: dict[check_key] = {
      "status": "confirmed_external"|"pending"|"rejected"|"documented_absent",
      "evidence_ref": non-empty non-PHI local/official reference string,
      "reviewer_role": non-empty non-PHI role string
    }
    Never put names, patient IDs, source paths or protected metadata in input.
    Returns planning readiness; clinical_scan_authorized is ALWAYS False.
    """
    if not isinstance(declarations, dict):
        raise TypeError("Evidence declarations must be a dictionary")
    unknown = set(declarations) - set(REQUIRED_EVIDENCE)
    if unknown:
        raise ValueError("Unknown evidence keys are not accepted")
    missing, pending, rejected, invalid, accepted = [], [], [], [], []
    for key in REQUIRED_EVIDENCE:
        row = declarations.get(key)
        if row is None:
            missing.append(key)
            continue
        if not isinstance(row, dict):
            raise TypeError("Each evidence entry must be a dictionary")
        if set(row) != {"status", "evidence_ref", "reviewer_role"}:
            raise ValueError("Each entry requires exactly status, evidence_ref, reviewer_role")
        status = row["status"]
        if status not in STATES:
            raise ValueError("Unknown evidence state")
        evidence = row["evidence_ref"]
        role = row["reviewer_role"]
        if not isinstance(evidence, str) or not isinstance(role, str):
            raise TypeError("Evidence references and reviewer roles must be strings")
        if len(evidence.strip()) > 160 or len(role.strip()) > 100:
            raise ValueError("Only short non-PHI evidence references/roles are permitted")
        if status == "rejected":
            rejected.append(key)
        elif status == "pending":
            pending.append(key)
        elif status == "documented_absent":
            if key not in DOCUMENTED_ABSENCE_ALLOWED or not evidence.strip() or not role.strip():
                invalid.append(key)
            else:
                accepted.append(key)
        elif not evidence.strip() or not role.strip():
            invalid.append(key)
        else:
            accepted.append(key)
    if rejected:
        state = "REJECTED_MUST_REDESIGN"
    elif missing or pending or invalid:
        state = "BLOCKED_NEEDS_EXTERNAL_EVIDENCE"
    else:
        state = "EVIDENCE_PACKET_READY_FOR_INDEPENDENT_AUTHORITY_REVIEW"
    return {
        "study": STUDY,
        "planning_state": state,
        "accepted_evidence_items": tuple(accepted),
        "missing_evidence_items": tuple(missing),
        "pending_evidence_items": tuple(pending),
        "rejected_evidence_items": tuple(rejected),
        "invalid_evidence_items": tuple(invalid),
        "hco_episode_linkage_verified": (
            declarations.get("hospital_or_episode_linkage_key_availability", {}).get("status")
            == "confirmed_external"
            and "hospital_or_episode_linkage_key_availability" in accepted
        ),
        "primary_definition": "A_exact_index_inpatient_encounter_recorded_code",
        "sensitivity_definition": "B_provisional_unique_date_only_ED_plus_IMP",
        "research_network_proposed_start_year": START_YEAR,
        "research_network_end_year": None,
        "data_owner_review_performed_by_this_function": False,
        "clinical_scan_authorized": False,
        "old_step45_execution_unblocked": False,
    }


def coverage_window_candidate(year_decisions, current_year=None):
    """Provisional 2016+ year window from independently reviewed summaries.

    Each dict declares year, full_calendar_year, hco_comparability_reviewed,
    event_code_capture_reviewed, reviewer_accepted, all explicit booleans.
    These values must be sourced independently, NOT inferred from reference
    terminology, ZIP metadata or the largest year in a clinical data file.
    Stops at first incomplete year. Any later accepted year despite a gap
    is a contradiction: no candidate. Does not authorize use.
    """
    if not isinstance(year_decisions, (list, tuple)):
        raise TypeError("year_decisions must be a list/tuple")
    required = {"year", "full_calendar_year", "hco_comparability_reviewed",
                "event_code_capture_reviewed", "reviewer_accepted"}
    by_year = {}
    today_year = date.today().year if current_year is None else current_year
    if isinstance(today_year, bool) or not isinstance(today_year, int) or today_year < START_YEAR:
        raise ValueError("current_year must be at least 2016")
    for record in year_decisions:
        if not isinstance(record, dict) or set(record) != required:
            raise ValueError("Each year requires exactly five coverage fields")
        year = record["year"]
        if isinstance(year, bool) or not isinstance(year, int) or not START_YEAR <= year <= today_year:
            raise ValueError("Coverage year must be a valid 2016+ calendar year")
        if year in by_year:
            raise ValueError("Duplicate calendar year in coverage evidence")
        if any(not isinstance(record[k], bool) for k in required - {"year"}):
            raise TypeError("Year review flags must be explicit booleans")
        by_year[year] = all(record[k] for k in required - {"year"})
    if START_YEAR not in by_year:
        return {
            "planning_state": "NO_CANDIDATE_START_YEAR_UNVERIFIED",
            "candidate_end_year": None,
            "clinical_end_year_approved": False,
        }
    first_fail = next((year for year in range(START_YEAR, max(by_year)+1)
                      if by_year.get(year) is not True), None)
    if first_fail is not None and any(ok for year, ok in by_year.items() if year > first_fail):
        return {
            "planning_state": "CONTRADICTORY_NONCONTIGUOUS_YEAR_EVIDENCE",
            "candidate_end_year": None,
            "clinical_end_year_approved": False,
        }
    candidate_end = first_fail-1 if first_fail is not None else max(by_year)
    if candidate_end < START_YEAR:
        candidate_end = None
    return {
        "planning_state": ("REVIEWED_CANDIDATE_WINDOW_NOT_APPROVED"
                           if candidate_end is not None else "NO_COMPLETE_START_YEAR"),
        "candidate_end_year": candidate_end,
        "clinical_end_year_approved": False,
    }

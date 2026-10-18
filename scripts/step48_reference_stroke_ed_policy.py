#!/usr/bin/env python3
"""Step48: testable, reference-only young-stroke phenotype and ED/IP link rules.

NO local dataset or clinical file access. Returns diagnostic CANDIDATE
classifications only. It does not approve ICD-9 case identification in the
2018-19 US period, determine stroke severity, or assert ED-to-IP linkage.
"""
from __future__ import annotations

import re
from datetime import date

ICD10 = frozenset({"ICD-10", "ICD-10-CM", "ICD10", "ICD10CM"})
ICD9 = frozenset({"ICD-9", "ICD-9-CM", "ICD9", "ICD9CM"})

# The exact 118 ICD-10 code list is NOT available from a two-line summary.
# Prefix matches are potential candidates, not code-set validation.
CEREBRAL = "cerebral_ischemic_candidate"
RETINAL = "retinal_artery_occlusion_separate_sensitivity"
LEGACY = "legacy_icd9_cerebral_candidate_requires_period_audit"
NONE = "not_in_user_supplied_stroke_code_families"


def stroke_code_family(system: str, code: str) -> str:
    system = (system or "").strip().upper()
    code = (code or "").strip().upper()
    if system in ICD10:
        if code == "H34.1":
            return RETINAL
        # I63 and dotted subcategories. Do NOT match I630 without a dot.
        if re.fullmatch(r"I63(?:\.[A-Z0-9]{1,5})?", code):
            return CEREBRAL
    if system in ICD9:
        normalized = code.replace(".", "")
        # 433.x1 and 434.x1 (examples 433.01, 434.11):
        # the final fifth digit must be 1; reject 433.x0 and 434.x0.
        if re.fullmatch(r"43[34][0-9]1", normalized):
            return LEGACY
    return NONE


def date_only(value):
    val = (value or "").strip()
    try:
        if re.fullmatch(r"\d{8}",val):
            return date(int(val[:4]), int(val[4:6]), int(val[6:]))
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}",val):
            return date.fromisoformat(val)
    except ValueError:
        return None
    return None


def ed_to_ip_candidate(ed: dict, admission: dict, max_gap_days: int = 1) -> str:
    """One plausible encounter-pair, never a confirmed episode.

    ED and inpatient encounter_id differ; patient_id+time alone is not enough
    to certify transfer. Use externally verified stable site identifier only.
    With date-only source, <=1 calendar day is NOT the same as 24 hours.
    """
    if max_gap_days not in (0,1,2,3):
        raise ValueError("max_gap_days must be 0 to 3")
    ed_id = (ed.get("encounter_id") or "").strip()
    ip_id = (admission.get("encounter_id") or "").strip()
    ed_pid = (ed.get("patient_id") or "").strip()
    ip_pid = (admission.get("patient_id") or "").strip()
    if not ed_pid or not ip_pid or ed_pid != ip_pid:
        return "reject_patient_id"
    if not ed_id or not ip_id or ed_id == ip_id:
        return "reject_invalid_or_same_encounter_id"
    if (ed.get("type") or "").strip().upper() != "EMER":
        return "reject_not_EMER"
    if (admission.get("type") or "").strip().upper() != "IMP":
        return "reject_not_IMP"
    ed_start = date_only(ed.get("start_date"))
    ed_end = date_only(ed.get("end_date"))
    ip_start = date_only(admission.get("start_date"))
    if ed_start is None or ip_start is None:
        return "hold_missing_or_invalid_dates"
    if ed_end and ed_end < ed_start:
        return "hold_bad_emergency_interval"
    # Do not assume source_id == HCO/site identifier; it can be different
    # across tables. Only a *separately verified* site key can be compared.
    site_ed = (ed.get("verified_site_key") or "").strip()
    site_ip = (admission.get("verified_site_key") or "").strip()
    if not site_ed or not site_ip:
        return "hold_site_mapping_unverified"
    if site_ed != site_ip:
        return "hold_different_site_or_transfer"
    # Date-only; allow ED same day or calendar day before IP. Do not
    # infer there is a verified transfer merely from the window.
    gap = (ip_start-ed_start).days
    if gap < 0:
        return "reject_emergency_starts_after_admission"
    if gap > max_gap_days:
        return "not_adjacent_in_requested_window"
    if ed_end and (ip_start-ed_end).days > max_gap_days:
        return "not_adjacent_in_requested_window"
    if ed_end and ed_end > ip_start:
        return "hold_overlapping_episode_timing"
    return "candidate_same_site_nearby_ED_IP_REQUIRES_VALIDATION"


def modality_set_names() -> tuple[str,...]:
    """Predeclared sensitivity labels, NOT clinical codebooks."""
    return (
        "historical_CPT14_anchor_EXPLORATORY",
        "reviewed_CPT_imaging",
        "reviewed_CPT_plus_nonCPT_imaging",
    )

#!/usr/bin/env python3
"""Step54: literature-grounded external imaging-code semantics (CPT, versioned).

Reference ONLY: maps published procedure CODE MEANINGS, not clinical occurrence
or performed-exam status in TriNetX. No patient/encounter/procedure row reads.
The Research Network's study years must be established from data coverage,
not copied from Diamond's independent 2018-2019 analysis.
"""
from __future__ import annotations

from datetime import date

# CMS historical code list (effective 2011), current CMS/NCCI code reference.
CPT_HISTORICAL = "https://www.cms.gov/regulations-and-guidance/guidance/transmittals/downloads/r738otn.pdf"
CPT_UPDATED = "https://www.cms.gov/files/document/09-chapter9-ncci-medicare-policy-manual-2026-final.pdf"
CPT_2026_CHANGE = "https://www.cms.gov/files/document/annual-update-list-cpt-hcpcs-codes-effective-january-1-2026.pdf"
CTP_2026_CHANGE = "https://www.cms.gov/medicare-coverage-database/view/article.aspx?articleId=58223&ver=19"

# Exact-code matching only. 14 anatomically unambiguous historical CPT anchors.
# All six categories are recorded IMAGE CODE families, never guaranteed exams.
BASE_CPT = {
    "70450": ("CT_HEAD", "CT brain/head without contrast"),
    "70460": ("CT_HEAD", "CT brain/head with contrast"),
    "70470": ("CT_HEAD", "CT brain/head without and with contrast"),
    "70496": ("CTA_HEAD", "CT angiography of head"),
    "70498": ("CTA_NECK", "CT angiography of neck"),
    "70544": ("MRA_HEAD", "MR angiography of head without contrast"),
    "70545": ("MRA_HEAD", "MR angiography of head with contrast"),
    "70546": ("MRA_HEAD", "MR angiography of head without and with contrast"),
    "70547": ("MRA_NECK", "MR angiography of neck without contrast"),
    "70548": ("MRA_NECK", "MR angiography of neck with contrast"),
    "70549": ("MRA_NECK", "MR angiography of neck without and with contrast"),
    "70551": ("MRI_BRAIN", "MRI brain without contrast"),
    "70552": ("MRI_BRAIN", "MRI brain with contrast"),
    "70553": ("MRI_BRAIN", "MRI brain without and with contrast"),
}

# CT perfusion is a distinct modality; do not silently count it as CTA/CT_HEAD.
# 0042T (historical) was deleted effective 2026-01-01; new 70472/70473
# identify CT cerebral perfusion and are NOT the CTA head/neck outcome.
CT_PERFUSION = {
    "0042T": ("2016-01-01", "2025-12-31", "CT perfusion, historical"),
    "70472": ("2026-01-01", None, "CT cerebral perfusion with concurrent CT/CTA"),
    "70473": ("2026-01-01", None, "CT cerebral perfusion without concurrent CT/CTA"),
}

# Beginning 2026, single CTA 70471 may cover both head and neck; requiring
# explicit dual-category support. It MUST NOT default to either single class.
CTA_DUAL_2026 = "70471"

# Explicit examples of common but WRONG automatic matches to acute structural
# brain MRI / CT angiography / MRA head and neck outcomes.
EXCLUSION_EXAMPLES = {
    "70554": "functional MRI, not routine structural brain MRI",
    "70555": "functional MRI, not routine structural brain MRI",
    "70540": "MRI orbit, face and/or neck; not brain MRI or MRA neck",
    "70542": "MRI orbit, face and/or neck; not brain MRI or MRA neck",
    "70543": "MRI orbit, face and/or neck; not brain MRI or MRA neck",
    "70480": "CT orbit/ear, not CT head/brain comparator",
    "70481": "CT orbit/ear, not CT head/brain comparator",
    "70482": "CT orbit/ear, not CT head/brain comparator",
    "70486": "CT maxillofacial, not CT head/brain comparator",
    "70487": "CT maxillofacial, not CT head/brain comparator",
    "70488": "CT maxillofacial, not CT head/brain comparator",
    "70490": "CT soft tissue neck, not CTA neck",
    "70491": "CT soft tissue neck, not CTA neck",
    "70492": "CT soft tissue neck, not CTA neck",
    "93880": "carotid duplex ultrasound, not CTA/MRA neck",
    "93882": "carotid duplex ultrasound, not CTA/MRA neck",
}

def _iso_day(value):
    if isinstance(value, date):
        return value
    if isinstance(value, str) and len(value) == 10:
        return date.fromisoformat(value)
    raise ValueError("Expected an ISO calendar date YYYY-MM-DD")


def research_network_period_policy():
    """Planning rule, not a claimed observed data date range.

    Research Network: begin 2016-01-01 for a consistent U.S. ICD-10 era;
    end at the last complete observed calendar year with acceptable coverage.
    A period-end cannot be assigned until approved full-data QA.
    Diamond remains a separate 2018-2019 dataset and estimand.
    """
    return {
        "diamond": {
            "start": "2018-01-01", "end": "2019-12-31",
            "period_fixed": True,
        },
        "research_network": {
            "proposed_start": "2016-01-01",
            "proposed_end": None,
            "end_rule": "last_complete_observed_calendar_year_after_coverage_QA",
            "include_pre_2016": False,
            "era_start_is_investigator_planning_decision_not_observed_min_date": True,
            "2018_2019_Diamond_rule_must_NOT_be_reused": True,
        },
    }


def classify_imaging_code(system: str, code: str, event_date=None) -> dict:
    """Return source-supported *candidate code meaning* only.

    event_date, when present, checks 2026 coding boundaries. No source data
    or procedure status is checked. Never use as final performed-codebook
    approval without mapping and recording-semantics validation.
    """
    system = (system or "").strip().upper().replace(" ", "")
    code = (code or "").strip().upper()
    result = {
        "code_system": system, "code": code,
        "status": "defer_unmapped_or_unverified_system",
        "category": None, "secondary_category": None,
        "meaning": "No externally verified exact-category mapping in curated registry",
        "date_compatibility": "needs_service_date_or_source_era_validation",
        "performed_procedure_verified": False,
        "source_semantics_verified": False,
        "external_code_meaning_supported": False,
        "clinical_codebook_signed_off": False,
        "source_url": None,
    }
    if system != "CPT":
        return result
    if code in BASE_CPT:
        category, meaning = BASE_CPT[code]
        result.update({
            "status": "core_exact_CPT_modality_candidate",
            "external_code_meaning_supported": True,
            "category": category, "meaning": meaning,
            "date_compatibility": "known_pre_2016_and_in_historical_CMS_schedule",
            "source_url": CPT_HISTORICAL,
        })
        return result
    if code == CTA_DUAL_2026:
        result.update({
            "status": "extended_CTA_head_plus_neck_2026_only_NOT_CORE",
            "external_code_meaning_supported": True,
            "category": "CTA_HEAD", "secondary_category": "CTA_NECK",
            "meaning": "Combined CTA head and neck, single code 70471",
            "source_url": CPT_2026_CHANGE,
        })
        earliest = date(2026, 1, 1)
        result["date_compatibility"] = (
            "yes" if event_date is not None and _iso_day(event_date) >= earliest
            else "no_before_2026" if event_date is not None
                 else "unknown_requires_date"
        )
        return result
    if code in CT_PERFUSION:
        start, end, meaning = CT_PERFUSION[code]
        result.update({
            "status": "CT_PERFUSION_SEPARATE_NOT_PRIMARY_CTA_MRA_MRI_CT_HEAD",
            "external_code_meaning_supported": True,
            "meaning": meaning, "source_url": CTP_2026_CHANGE,
            "date_compatibility": "unknown_requires_date",
        })
        if event_date is not None:
            d = _iso_day(event_date)
            result["date_compatibility"] = (
                "yes" if _iso_day(start) <= d and
                (end is None or d <= _iso_day(end)) else "no_outside_valid_era"
            )
        return result
    if code in EXCLUSION_EXAMPLES:
        result.update({
            "status": "exclude_not_study_modality",
            "external_code_meaning_supported": True,
            "meaning": EXCLUSION_EXAMPLES[code],
            "source_url": ("https://www.cms.gov/medicare/quality-initiatives-patient-assessment-instruments/pqrs/downloads/2014-physician-fee-schedule-final-rule_cms-1600-fc.pdf" if code in {"93880","93882"} else CPT_HISTORICAL),
            "date_compatibility": "not_applicable",
        })
        return result
    result.update({
        "status": "defer_CPT_not_in_literature_core",
        "meaning": "CPT not in selected evidence-backed imaging families",
        "source_url": CPT_HISTORICAL,
    })
    return result


def registry_summary():
    return {
        "study_outcomes": tuple(sorted(set(v[0] for v in BASE_CPT.values()))),
        "historical_core_codes": len(BASE_CPT),
        "source_system": "CPT",
        "performed_procedure_verified": False,
        "source_codebook_review_signed_off": False,
        "research_network_study_period": research_network_period_policy()["research_network"],
    }

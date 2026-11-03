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
    """Backward-compatible Step48 entrypoint for revised end-date-first rule.

    The Step49 resolver also checks competing ED/IP candidates. A single
    pair match never proves that the encounters are the same admission.
    """
    if __package__:
        from .step49_ed_ip_episode_candidates import pair_candidate
    else:
        from step49_ed_ip_episode_candidates import pair_candidate
    return pair_candidate(ed, admission, max_gap_days)


def modality_set_names() -> tuple[str,...]:
    """Predeclared sensitivity labels, NOT clinical codebooks."""
    return (
        "historical_CPT14_anchor_EXPLORATORY",
        "reviewed_CPT_imaging",
        "reviewed_CPT_plus_nonCPT_imaging",
    )

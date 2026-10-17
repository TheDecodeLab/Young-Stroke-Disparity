"""Synthetic aggregate-only tests for Step31, no patient records."""
from __future__ import annotations
from copy import deepcopy

import pytest

from scripts.step31_expanded_reconciliation import reconcile

MODS = ("CT", "MRI", "CTA", "MRA")
CATS = ("CT only", "CT + additional",
        "Additional without CT", "None of four")


def fixture():
    n = 180
    old = {
        "total": n, "CT": 100, "MRI": 50, "CTA": 30, "MRA": 20,
        "CT only": 40, "CT + additional": 60,
        "Additional without CT": 30, "None of four": 50,
    }
    head = {
        "total": n, "CT": 100, "MRI": 50, "CTA": 30, "MRA": 35,
        "CT only": 35, "CT + additional": 65,
        "Additional without CT": 42, "None of four": 38,
    }
    wide = {
        "total": n, "CT": 100, "MRI": 50, "CTA": 45, "MRA": 50,
        "CT only": 30, "CT + additional": 70,
        "Additional without CT": 58, "None of four": 22,
    }
    preflight = {
        "stage": "STEP28_PREFLIGHT_ONLY",
        "procedure_rows_scanned": 0,
        "number_of_candidate_codes": 14,
        "candidate_codes": [{"clinical_review": "evidence_reviewed"} for _ in range(14)],
        "codebook_sha256": "a" * 64,
        "source_procedure_rows_declared": 1000,
        "private_indexed_age_19_50_patients": n,
    }
    exp = {
        "stage": "STEP28_EXPANDED_CODE_EXTRACTION_TEMPORAL_PROXY",
        "review_basis": "published_evidence_only_no_independent_clinician_signoff",
        "existing_data_use_permission_attested_by_local_operator": True,
        "manifest_row_count_verified": True,
        "source_procedure_rows_scanned": 1000,
        "approved_codebook_sha256": "a" * 64,
        "encounter_validated": False,
        "ready_for_manuscript_inference": False,
        "scientific_inference_and_publication_approved": False,
        "eligible_diagnosis_first_patients": n,
        "retained_legacy_patient_modality_days": 300,
        "matched_code_specific_patient_days": 320,
        "aggregate_disclosure_review_required": True,
        "windows_inclusive_days_each_side": {
            str(w): dict(wide, suppressed=False) for w in (0, 1, 3, 7)},
        "anatomic_profiles_by_window": {
            str(w): {
                "suppressed": False,
                "head_only_primary": dict(head),
                "head_plus_neck_sensitivity": dict(wide),
                "neck_without_head_cta_mra": {
                    "CTA neck without CTA head": 15,
                    "MRA neck without MRA head": 15,
                }
            } for w in (0, 1, 3, 7)},
    }
    legacy = {
        "stage": "STEP22_LOCAL_SQLITE_VALIDATION_ONLY",
        "previous_chained_report_compared": True,
        "previous_chained_report_discrepancies": {},
        "age_eligible_n": n,
        "matched_distinct_modality_days": 300,
        "windows_inclusive_days_each_side": {
            str(w): dict(old, suppressed=False) for w in (0, 1, 3, 7)},
    }
    return preflight, exp, legacy


def test_synthetic_aggregate_reconciles_without_reading_rows():
    report = reconcile(*fixture())
    assert report["all_aggregate_checks_passed"] is True
    assert report["original_source_rows_read"] == 0
    assert report["patient_level_rows_read"] == 0
    assert report["clinical_inference_approved"] is False
    seven = report["per_window"]["7"]
    assert seven["expanded_minus_historical_coverage_percent_points"] > 0
    assert seven["additional_any_included_code_vs_historical_n"] == 28
    assert seven["new_head_mra_patient_matches_n"] == 15
    assert seven["small_delta_suppressed"] is False


def test_wrong_codebook_rejected():
    x = deepcopy(fixture())
    x[1]["approved_codebook_sha256"] = "b"*64
    with pytest.raises(ValueError, match="fingerprint"):
        reconcile(*x)


def test_source_row_mismatch_rejected():
    x = deepcopy(fixture())
    x[1]["source_procedure_rows_scanned"] -= 1
    with pytest.raises(ValueError, match="source procedure"):
        reconcile(*x)


def test_wrong_legacy_event_preservation_rejected():
    x = deepcopy(fixture())
    x[1]["retained_legacy_patient_modality_days"] -= 1
    with pytest.raises(ValueError, match="historical modality-day"):
        reconcile(*x)


def test_neck_subclass_disagreement_rejected():
    x = deepcopy(fixture())
    x[1]["anatomic_profiles_by_window"]["1"]["neck_without_head_cta_mra"][
        "MRA neck without MRA head"] = 30
    with pytest.raises(ValueError, match="MRA neck-only"):
        reconcile(*x)


def test_missing_required_window_rejected():
    x = deepcopy(fixture())
    del x[1]["windows_inclusive_days_each_side"]["3"]
    with pytest.raises(ValueError, match="sensitivity windows"):
        reconcile(*x)


def test_new_small_delta_suppressed_entire_added_group():
    x = deepcopy(fixture())
    for w in ("0", "1", "3", "7"):
        # A valid head panel, but only 2 additional MRA patients compared to old.
        h = x[1]["anatomic_profiles_by_window"][w]["head_only_primary"]
        h["MRA"] = 22
    result = reconcile(*x)
    seven = result["per_window"]["7"]
    assert seven["small_delta_suppressed"] is True
    assert "new_head_mra_patient_matches_n" not in seven


def test_subgroup_not_admission_validated():
    x = deepcopy(fixture())
    x[1]["encounter_validated"] = True
    with pytest.raises(ValueError, match="admission-validated"):
        reconcile(*x)

"""Synthetic aggregate fixtures only; no user clinical records or patient IDs."""
from __future__ import annotations
from copy import deepcopy
import pytest
from scripts.step25_readiness_gate import gate


def reports():
    classes = {
        "CT only": 30, "CT + additional": 40,
        "Additional without CT": 20, "None of four": 30,
    }
    wide = dict(classes, **{"total": 120, "CT": 70, "MRI": 45,
                             "CTA": 35, "MRA": 20})
    temporal_windows = {
        "0": {"CT only": 40, "CT + additional": 20,
              "Additional without CT": 10, "None of four": 50,
              "total": 120, "CT": 60, "MRI": 20, "CTA": 15, "MRA": 10},
        "1": {"CT only": 35, "CT + additional": 30,
              "Additional without CT": 15, "None of four": 40,
              "total": 120, "CT": 65, "MRI": 35, "CTA": 25, "MRA": 14},
        "3": {"CT only": 32, "CT + additional": 35,
              "Additional without CT": 18, "None of four": 35,
              "total": 120, "CT": 67, "MRI": 40, "CTA": 31, "MRA": 18},
        "7": wide,
    }
    rec = {
        "stage": "CHAINED_PROVISIONAL_RECONSTRUCTION",
        "completed_all_source_scans": True, "validated_admission_cohort": False,
        "stages": [
            {"scan_complete": True, "declared_total_source_rows": 500,
             "aggregate_counters": {"rows_scanned": 500},
             "distinct_principal_I63_candidate_patients": 150},
            {"eligible_n": 120, "matched_demographic_rows": 150,
             "source_rows": 220},
            {"distinct_modality_days_matched": 200,
             "aggregate_cohort_integrity": {
                 "age_eligible_first_diagnosis_n": 120,
                 "ct_only_n": 30, "ct_and_additional_n": 40,
                 "advanced_no_ct_n": 20, "none_of_four_imaging_n": 30,
                 "ct_n": 70, "mri_n": 45, "cta_n": 35, "mra_n": 20}},
        ],
    }
    temporal = {
        "stage": "STEP22_LOCAL_SQLITE_VALIDATION_ONLY",
        "previous_chained_report_compared": True,
        "previous_chained_report_discrepancies": {},
        "age_eligible_n": 120, "full_diagnosis_index_patients": 150,
        "matched_distinct_modality_days": 200,
        "windows_inclusive_days_each_side": temporal_windows,
        "race_unknown_or_missing_n": 96,
        "ethnicity_unknown_or_missing_n": 90,
    }
    by_group = [
        {"imaging_class": cls, "patients": n,
         "race_unknown_or_missing_n": race,
         "ethnicity_unknown_or_missing_n": ethnicity}
        for cls,n,race,ethnicity in [
            ("CT only",30,24,23), ("CT + additional",40,32,30),
            ("Additional without CT",20,16,15), ("None of four",30,24,22),
        ]
    ]
    eligibility = {
        "stage": "STEPS23_24_ELIGIBILITY_AND_CODE_QC",
        "signature_reconciled": True, "step22_reference_compared": True,
        "clinical_inference_allowed": False,
        "demographic_attrition": {
            "index_patients": 150, "source_patients_matched_to_index": 150,
            "original_patient_source_rows_verified": 220,
            "saved_eligible_patients_reconciled_n": 120,
            "exclusive_age_and_sex_attrition": {
                "age_over_50": 15, "age_under_19": 3,
                "eligible_19_50": 120, "missing_or_invalid_birth_year": 10,
                "unrecognized_sex": 2,
            },
        },
        "diagnosis_and_imaging_diagnostics": {
            "missing_race_ethnicity_by_imaging_group": by_group,
            "coarse_icd10_group_by_imaging": [
                {"icd10_group": "I63.9 family", "suppressed": False,
                 "eligible_total": 70,
                 "imaging_groups": {"CT only":20, "CT + additional":20,
                                    "Additional without CT":10, "None of four":20}},
                {"icd10_group": "Other I63 codes", "suppressed": False,
                 "eligible_total": 50,
                 "imaging_groups": {"CT only":10, "CT + additional":20,
                                    "Additional without CT":10, "None of four":10}},
            ],
        },
    }
    return rec, temporal, eligibility


def test_validated_aggregate_fixture():
    report = gate(*reports())
    assert report["all_prior_aggregate_counts_reconciled"]
    assert report["patient_level_sqlite_records_read"] == 0
    assert report["zip_records_read"] == 0
    assert report["ready_for_manuscript_inference"] is False
    assert report["principal_I63_index_patients"] == 150
    assert report["historical_fine_diagnosis_group_report_requires_disclosure_review"] is True
    assert report["current_input_has_suppressed_fine_group"] is False


def test_attrition_tampering_rejected():
    x = deepcopy(reports())
    x[2]["demographic_attrition"]["exclusive_age_and_sex_attrition"]["age_over_50"] += 1
    with pytest.raises(ValueError, match="attrition"):
        gate(*x)


def test_race_missingness_tampering_rejected():
    x = deepcopy(reports())
    x[2]["diagnosis_and_imaging_diagnostics"]["missing_race_ethnicity_by_imaging_group"][0]["race_unknown_or_missing_n"] += 1
    with pytest.raises(ValueError, match="race missingness"):
        gate(*x)


def test_wrong_zip_signature_rejected():
    x = deepcopy(reports())
    x[2]["signature_reconciled"] = False
    with pytest.raises(ValueError, match="status or source signature"):
        gate(*x)


def test_misaligned_time_window_rejected():
    x = deepcopy(reports())
    x[1]["windows_inclusive_days_each_side"]["1"]["MRI"] = 55
    with pytest.raises(ValueError, match="monotonic window"):
        gate(*x)


def test_coarse_code_counts_checked():
    x = deepcopy(reports())
    x[2]["diagnosis_and_imaging_diagnostics"]["coarse_icd10_group_by_imaging"][0]["eligible_total"] += 1
    with pytest.raises(ValueError, match="coarse ICD summary"):
        gate(*x)


def test_legacy_fine_group_risk_flag_without_exposing_cell():
    x = deepcopy(reports())
    detail = x[2]["diagnosis_and_imaging_diagnostics"]
    del detail["coarse_icd10_group_by_imaging"]
    detail["first_decimal_digit_audit_by_imaging"] = [
        {"icd10_family": "I63 stem", "suppressed": True}
    ]
    report = gate(*x)
    assert report["historical_fine_diagnosis_group_report_requires_disclosure_review"]
    assert report["current_input_has_suppressed_fine_group"] is True
    assert "small_group_count" not in report

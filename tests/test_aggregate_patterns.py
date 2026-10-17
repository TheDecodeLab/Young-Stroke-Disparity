"""Step33 synthetic-only aggregate test suite; no source clinical rows."""
from __future__ import annotations
from copy import deepcopy

import pytest

from scripts.step33_aggregate_patterns import compare

WINDOWS = ("0", "1", "3", "7")


def fake_reports():
    # Dimensions all cover the same 600 synthetic patients.
    # Window-specific matched totals: 200,240,270,300 respectively.
    matched = {
        "age_band": {
            "19-29": (100, (60, 65, 70, 75)),
            "30-39": (200, (70, 85, 95, 105)),
            "40-50": (300, (70, 90, 105, 120)),
        },
        "recorded_sex": {
            "Female": (250, (90, 110, 130, 140)),
            "Male": (350, (110, 130, 140, 160)),
        },
        "index_year": {
            "2018": (300, (85, 105, 120, 140)),
            "2019": (300, (115, 135, 150, 160)),
        },
    }
    def record(matched_count, denominator):
        return {
            "any_head_n": matched_count,
            "any_head_or_neck_n": matched_count,
            "brain_MRI_n": 0,
            "head_CTA_n": 0,
            "head_CT_n": matched_count,
            "head_MRA_n": 0,
            "head_or_neck_CTA_n": 0,
            "head_or_neck_MRA_n": 0,
            "none_head_or_neck_n": denominator-matched_count,
        }
    details = {}
    for dimension, entries in matched.items():
        rows = []
        for label, (denominator, sequence) in entries.items():
            rows.append({
                "stratum": label,
                "denominator": denominator,
                "windows": {
                    w: record(sequence[i], denominator)
                    for i, w in enumerate(WINDOWS)
                },
            })
        details[dimension] = {"suppressed": False, "strata": rows}
    matched_totals = (200, 240, 270, 300)
    step31 = {
        "stage": "STEP31_EXPANDED_IMAGING_AGGREGATE_RECONCILIATION",
        "all_aggregate_checks_passed": True,
        "clinical_inference_approved": False,
        "cross_report_disclosure_review_required": True,
        "original_source_rows_read": 0,
        "patient_level_rows_read": 0,
        "study_cohort_n": 600,
        "per_window": {
            w: {
                "denominator": 600,
                "expanded_with_any_included_code_n": matched_totals[i],
                "expanded_without_matching_included_code_n":
                    600-matched_totals[i],
                "head_only_with_any_included_code_n": matched_totals[i],
                "expanded_minus_historical_coverage_percent_points": 0.2,
            } for i, w in enumerate(WINDOWS)
        }
    }
    step32 = {
        "stage": "STEP32_READ_ONLY_RECORDING_HETEROGENEITY_QC",
        "private_sqlite_source_verified": True,
        "original_zip_rows_scanned": 0,
        "private_patient_level_rows_exported": 0,
        "clinical_inference_allowed": False,
        "race_ethnicity_inference_allowed": False,
        "publication_disclosure_review_required": True,
        "code_specific_event_rows_read": 700,
        "denominator": 600,
        "groupwise_coding_diagnostics": details,
    }
    return step31, step32


def test_step33_synthetic_matches_all_three_dimensions():
    r = compare(*fake_reports())
    assert r["all_three_dimensions_reconciled"] is True
    assert r["source_zip_records_read"] == 0
    assert r["private_sqlite_records_read"] == 0
    assert r["clinical_inference_allowed"] is False
    assert r["demographic_disparity_inference_allowed"] is False
    assert r["window_any_matching_code_percent"]["1"] == 40.0
    assert r["any_code_percent_change_day0_to_plusminus7"] == 16.67
    assert r["unadjusted_code_frequency_differences_percentage_points"][
        "year_2019_minus_2018_pp"] == 10.0


def test_step32_cohort_denominator_change_rejected():
    args = deepcopy(fake_reports())
    args[1]["denominator"] += 1
    with pytest.raises(ValueError, match="cohort denominator"):
        compare(*args)


def test_expanded_window_difference_rejected():
    args = deepcopy(fake_reports())
    args[1]["groupwise_coding_diagnostics"]["age_band"]["strata"][0][
        "windows"]["1"]["any_head_or_neck_n"] += 1
    with pytest.raises(ValueError, match="partition"):
        compare(*args)


def test_cross_dimension_modality_totals_rejected():
    args = deepcopy(fake_reports())
    group = args[1]["groupwise_coding_diagnostics"]["recorded_sex"]["strata"][0]
    group["windows"]["1"]["head_CT_n"] -= 1
    with pytest.raises(ValueError, match="inconsistent modality marginals"):
        compare(*args)


def test_suppressed_dimension_not_released():
    args = deepcopy(fake_reports())
    args[1]["groupwise_coding_diagnostics"]["recorded_sex"] = {"suppressed": True}
    with pytest.raises(ValueError, match="dimension withheld"):
        compare(*args)


def test_unapproved_inference_rejected():
    args = deepcopy(fake_reports())
    args[0]["clinical_inference_approved"] = True
    with pytest.raises(ValueError, match="Step 31 provenance"):
        compare(*args)


def test_publication_disclosure_requirements_preserved():
    args = deepcopy(fake_reports())
    args[1]["publication_disclosure_review_required"] = False
    with pytest.raises(ValueError, match="Step 32 provenance"):
        compare(*args)


def test_unexpected_stratum_rejected():
    args = deepcopy(fake_reports())
    args[1]["groupwise_coding_diagnostics"]["index_year"]["strata"][0][
        "stratum"] = "2017"
    with pytest.raises(ValueError, match="missing or extra strata"):
        compare(*args)

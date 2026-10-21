"""Synthetic tests for Step 10 cohort reconciliation. No clinical records."""
import pandas as pd
import pytest

from scripts.step10_reconcile_cohorts import reconcile


def make_tables():
    candidate = pd.DataFrame({
        "patient_id": ["a", "b", "c", "d"],
        "CT": [1, 1, 0, 1],
        "MRI": [1, 0, 1, 0],
        "CTA": [0, 0, 0, 1],
        "MRA": [0, 0, 0, 0],
        "sex": ["Men", "Women", "Women", "Men"],
        "age@stroke": [40, 37, 30, 50],
        "dx_year": [2018, 2018, 2019, 2019],
        "stroke": ["Ischemic"] * 4,
    })
    legacy = candidate.loc[[0, 3],
        ["patient_id", "MRI", "CTA", "MRA", "sex",
         "age@stroke", "dx_year", "stroke"]].copy()
    extra = pd.DataFrame([{
        "patient_id": "e", "MRI": 1, "CTA": 0, "MRA": 0,
        "sex": "Women", "age@stroke": 40, "dx_year": 2019, "stroke": "Ischemic",
    }])
    legacy = pd.concat([legacy, extra], ignore_index=True)
    return candidate, legacy


def test_reconcile_membership_and_counts():
    candidate, legacy = make_tables()
    result = reconcile(candidate, legacy)
    assert result["as_saved_intersection_n"] == 2
    assert result["as_saved_candidate_only_n"] == 2
    assert result["as_saved_legacy_only_n"] == 1
    x = result["cohort_summaries"]["as_saved"]
    assert x["candidate"]["ct_only_n"] == 1
    assert x["candidate"]["advanced_without_ct_n"] == 1
    assert x["candidate_ct_positive_and_advanced_n"] == 2
    assert x["difference_legacy_vs_candidate_ct_plus_advanced_n"] == 1


def test_mismatch_is_counted():
    candidate, legacy = make_tables()
    legacy.loc[0, "MRI"] = 2
    result = reconcile(candidate, legacy)
    assert result["matched_patient_fields"]["MRI"]["mismatch_n"] == 1
    assert result["status"] == "BLOCKED_FOR_INFERENCE"


def test_common_age_cutoff_is_not_saved_cohort():
    candidate, legacy = make_tables()
    result = reconcile(candidate, legacy)
    by_45 = result["cohort_summaries"]["age19_to_45"]
    assert by_45["candidate"]["patients_n"] == 3
    assert by_45["candidate"]["ct_plus_advanced_n"] == 1
    assert by_45["legacy"]["patients_n"] == 2


def test_missing_ct_or_duplicate_id_rejected():
    candidate, legacy = make_tables()
    with pytest.raises(ValueError, match="missing columns"):
        reconcile(candidate.drop(columns="CT"), legacy)
    duplicate = pd.concat([candidate, candidate.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicated"):
        reconcile(duplicate, legacy)


def test_invalid_procedure_count_rejected():
    candidate, legacy = make_tables()
    candidate.loc[0, "CT"] = -1
    with pytest.raises(ValueError, match="invalid procedure"):
        reconcile(candidate, legacy)

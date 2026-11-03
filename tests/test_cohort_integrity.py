"""Synthetic-only unit tests for cohort selection integrity."""
import pandas as pd
import pytest
from scripts.step08_cohort_integrity import audit_pattern_summary


def sample(mri_in_neither):
    return pd.DataFrame([
        {"stratification": "overall", "group": "All", "pattern": "neither",
         "group_n": 100, "pattern_n": 20, "MRI_within_pattern_n": mri_in_neither},
        {"stratification": "overall", "group": "All", "pattern": "CTA only",
         "group_n": 100, "pattern_n": 40, "MRI_within_pattern_n": 15},
        {"stratification": "overall", "group": "All", "pattern": "MRA only",
         "group_n": 100, "pattern_n": 25, "MRI_within_pattern_n": 20},
        {"stratification": "overall", "group": "All", "pattern": "both",
         "group_n": 100, "pattern_n": 15, "MRI_within_pattern_n": 12},
    ])


def test_detects_selection_red_flag():
    report = audit_pattern_summary(sample(20))
    assert report["no_mri_cta_mra_n"] == 0
    assert report["selection_bias_red_flag"] is True
    assert report["ready_for_population_inference"] is False


def test_nonzero_no_modality_is_not_validation():
    report = audit_pattern_summary(sample(10))
    assert report["no_mri_cta_mra_n"] == 10
    assert report["selection_bias_red_flag"] is False
    assert report["ready_for_population_inference"] is False


def test_missing_pattern_rejected():
    with pytest.raises(ValueError, match="four distinct"):
        audit_pattern_summary(sample(20).iloc[:-1])


def test_partition_error_rejected():
    df = sample(20)
    df.loc[1, "pattern_n"] = 39
    with pytest.raises(ValueError, match="partition"):
        audit_pattern_summary(df)


def test_mri_exceeds_denominator_rejected():
    df = sample(20)
    df.loc[0, "MRI_within_pattern_n"] = 21
    with pytest.raises(ValueError, match="exceeds"):
        audit_pattern_summary(df)

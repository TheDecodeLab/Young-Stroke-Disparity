"""Unit tests use synthetic observations only."""
import pandas as pd
import pytest

from scripts.step07_modality_patterns import summarize_modality_patterns


def synthetic():
    return pd.DataFrame({
        "sex": ["Men", "Men", "Women", "Women", "Women"],
        "dx_year": [2018, 2019, 2018, 2019, 2019],
        "age_at_stroke": [22, 36, 45, 29, 50],
        "MRI_received": [1, 0, 1, 0, 1],
        "CTA_received": [0, 1, 0, 1, 1],
        "MRA_received": [0, 0, 1, 1, 0],
        "vascular_received": [0, 1, 1, 1, 1],
        "vascular_pattern": ["neither", "CTA only", "MRA only", "both", "CTA only"],
    })


def test_overall_patterns_partition_cohort():
    result = summarize_modality_patterns(synthetic())
    overall = result[result.stratification.eq("overall")]
    assert overall.group_n.eq(5).all()
    assert overall.pattern_n.sum() == 5
    assert dict(zip(overall.pattern, overall.pattern_n)) == {
        "neither": 1, "CTA only": 2, "MRA only": 1, "both": 1,
    }


def test_per_group_denominators_and_mri():
    result = summarize_modality_patterns(synthetic())
    men = result[(result.stratification == "sex") & (result.group == "Men")]
    assert men.pattern_n.sum() == 2
    neither = men[men.pattern.eq("neither")].iloc[0]
    assert neither.MRI_within_pattern_n == 1
    assert neither.MRI_within_pattern_pct == 100.0


def test_rejects_bad_derived_outcome():
    df = synthetic()
    df.loc[0, "vascular_received"] = 1
    with pytest.raises(ValueError, match="inconsistent"):
        summarize_modality_patterns(df)


def test_rejects_wrong_age_population():
    df = synthetic()
    df.loc[0, "age_at_stroke"] = 55
    with pytest.raises(ValueError, match="19-50"):
        summarize_modality_patterns(df)


def test_rejects_wrong_pattern():
    df = synthetic()
    df.loc[0, "vascular_pattern"] = "CTA only"
    with pytest.raises(ValueError, match="disagree"):
        summarize_modality_patterns(df)

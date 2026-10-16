"""Synthetic-only checks for demographic missingness reporting."""
import pandas as pd
import pytest

from scripts.step05_missingness import summarize_missingness, suppress_small_cells


def synthetic():
    return pd.DataFrame({
        "sex": ["Men", "Men", "Women", "Women", "Women", "Men"],
        "dx_year": [2018, 2018, 2019, 2019, 2018, 2019],
        "race": ["White", pd.NA, "Black", pd.NA, pd.NA, "White"],
        "ethnicity": ["Hispanic", pd.NA, "Non-Hispanic", pd.NA, "Hispanic", pd.NA],
        "MRI_received": [1, 0, 1, 1, 0, 1],
        "vascular_received": [1, 1, 0, 1, 0, 1],
    })


def test_missingness_uses_all_denominators():
    result = summarize_missingness(synthetic())
    race = result[(result.demographic == "race") & (result.stratified_by == "overall")]
    assert int(race.n.sum()) == 6
    missing = race[race.availability == "Missing/unknown"].iloc[0]
    assert missing.n == 3
    assert missing.MRI_received_n == 1
    assert abs(missing.MRI_received_pct - 33.33) < .01


def test_sex_year_breakdown():
    result = summarize_missingness(synthetic())
    assert set(result.stratified_by) == {"overall", "sex", "dx_year"}
    race_sex = result[(result.demographic == "race") & (result.stratified_by == "sex")]
    assert race_sex.n.sum() == 6


def test_small_cell_suppression():
    result = summarize_missingness(synthetic())
    masked = suppress_small_cells(result, threshold=11)
    assert masked.suppressed_small_cell.all()
    assert masked.n.isna().all()
    assert masked.MRI_received_pct.isna().all()


def test_nonbinary_outcome_rejected():
    data = synthetic()
    data.loc[0, "MRI_received"] = 2
    with pytest.raises(ValueError, match="binary"):
        summarize_missingness(data)

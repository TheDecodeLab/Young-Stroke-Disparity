"""Unit tests based on generated synthetic observations only."""
import numpy as np
import pandas as pd
import pytest

from scripts.step06_minimal_models import analyze, fit_marginal_difference


def fake_cohort(n=500, seed=12):
    rng = np.random.default_rng(seed)
    sex = np.where(rng.uniform(size=n) < .45, "Men", "Women")
    ages = rng.integers(19, 51, size=n)
    years = rng.choice([2018, 2019], size=n)
    lp = -.25 - .35 * (sex == "Men") + .01 * (ages - 35) + .14 * (years == 2019)
    p = 1 / (1 + np.exp(-lp))
    return pd.DataFrame({
        "sex": sex,
        "age_at_stroke": ages,
        "dx_year": years,
        "race": np.where(rng.uniform(size=n) < .3, "White", pd.NA),
        "MRI_received": rng.binomial(1, p),
        "vascular_received": rng.binomial(1, .6, n),
    })


def test_outputs_are_bounded_and_direction_is_reasonable():
    report = fit_marginal_difference(fake_cohort(), "MRI_received")
    assert report["n"] == 500
    assert 0 <= report["adjusted_men_pct"] <= 100
    assert 0 <= report["adjusted_women_pct"] <= 100
    assert report["men_minus_women_pp"] < 0
    assert report["ci_low_pp"] <= report["men_minus_women_pp"] <= report["ci_high_pp"]


def test_subsets_sum_to_total():
    report = analyze(fake_cohort())
    assert set(report.subset) == {"all", "race_known", "race_missing_or_unknown"}
    assert set(report.outcome) == {"MRI_received", "vascular_received"}
    for y in ("MRI_received", "vascular_received"):
        x = report[report.outcome == y].set_index("subset")
        assert x.loc["race_known", "n"] + x.loc["race_missing_or_unknown", "n"] == x.loc["all", "n"]


def test_nonbinary_data_rejected():
    data = fake_cohort()
    data.loc[0, "MRI_received"] = 4
    with pytest.raises(ValueError, match="binary"):
        fit_marginal_difference(data, "MRI_received")


def test_outcome_other_than_supported_rejected():
    with pytest.raises(ValueError, match="Unsupported"):
        fit_marginal_difference(fake_cohort(), "MRI_count")


def test_missing_sex_rejected():
    data = fake_cohort()
    data.loc[0, "sex"] = None
    with pytest.raises(ValueError, match="Incomplete"):
        fit_marginal_difference(data, "MRI_received")

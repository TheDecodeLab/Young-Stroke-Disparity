"""Synthetic-only unit tests; no TriNetX records or identifiers."""
import pandas as pd
import pytest

from scripts.step01_audit import audit_frame
from scripts.step02_prepare import prepare
from scripts.step03_describe import describe
from scripts.step04_audit_nis import assess_manuscript_match


@pytest.fixture
def frame():
    return pd.DataFrame({
        "patient_id": ["a", "b", "c", "d"],
        "sex": ["Men", "Women", "Women", "Men"],
        "race": ["White", "Black", "Unknown", "White"],
        "ethnicity": ["Non-Hispanic", "Unknown", "Hispanic", "Non-Hispanic"],
        "age@stroke": [49, 50, 52, 54],
        "dx_year": [2018, 2019, 2019, 2018],
        "stroke": ["Ischemic"] * 4,
        "MRI": [0, 2, 1, 0], "CTA": [0, 1, 0, 1], "MRA": [0, 1, 1, 0],
        "CHA2DS2_VASc_score": [0, 1, 1, 0], "postal_code": [111, 222, 333, 444],
    })


def test_audit_reports_missingness_and_duplicates(frame):
    report = audit_frame(frame)
    assert report["rows"] == 4
    assert report["missing_or_unknown"]["race"]["n"] == 1
    assert report["modality_counts"]["MRI"]["positive_n"] == 2
    assert report["duplicate_patient_ids"] == 0
    assert any("CHA2DS2" in warning for warning in report["warnings"])


def test_prepare_age_and_outcomes(frame):
    result = prepare(frame, max_age=50)
    assert len(result) == 2
    assert result["vascular_received"].tolist() == [0, 1]
    assert result["MRI_received"].tolist() == [0, 1]
    assert list(result["vascular_pattern"].astype(str)) == ["neither", "both"]
    assert "patient_id" not in result
    assert "postal_code" not in result
    assert "CHA2DS2_VASc_score" not in result


def test_prepare_rejects_unrecoverable_age_range(frame):
    with pytest.raises(ValueError, match="source"):
        prepare(frame, max_age=55)


def test_prepare_rejects_duplicates(frame):
    df = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="one record"):
        prepare(df)


def test_describe_numerators_denominators(frame):
    desc = describe(prepare(frame, 50))
    men = desc[(desc.stratifier == "sex") & (desc.group == "Men")].iloc[0]
    women = desc[(desc.stratifier == "sex") & (desc.group == "Women")].iloc[0]
    assert men["n"] == 1
    assert men["MRI_received_pct"] == 0
    assert women["vascular_received_pct"] == 100


def test_nis_difference_is_flagged():
    rows = pd.DataFrame([
        {"comparison": "race", "age_stratum_code": "6", "group": "White",
         "mean_mri": .800000072, "reported_p": .070823917},
        {"comparison": "race", "age_stratum_code": "6", "group": "Black",
         "mean_mri": .740000746, "reported_p": .070823917},
    ])
    result = assess_manuscript_match(rows)
    assert len(result["matching_strata_in_current_csvs"]) == 1
    assert result["matching_strata_in_current_csvs"][0]["consistent_with_manuscript_p_lt_0_05"] is False

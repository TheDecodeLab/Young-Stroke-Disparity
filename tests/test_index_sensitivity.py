"""Step 12 synthetic-only diagnostic tests."""
import pandas as pd
import pytest

from scripts.step12_index_sensitivity import summarize


def rows():
    # a: CT first, MRI later; b: MRI first, CT later;
    # c: CT and MRI together; d: CT only; e: MRI only.
    x = [
        ("a", "2018-01-01", "CT"),
        ("a", "2019-01-01", "MRI"),
        ("b", "2018-01-01", "MRI"),
        ("b", "2019-01-01", "CT"),
        ("c", "2018-01-01", "CT"),
        ("c", "2018-01-01", "MRI"),
        ("d", "2018-01-01", "CT"),
        ("e", "2018-01-01", "MRI"),
    ]
    return pd.DataFrame([
        {"patient_id": p, "datetime_dx": day, "datetime_px": day,
         "category": modality, "Stroke": "Ischemic",
         "principal_diagnosis_indicator": "P"}
        for p, day, modality in x
    ])


def test_earliest_ct_vs_first_advanced():
    out = summarize(rows())
    assert out["linked_patients_any_imaging"] == 5
    assert out["patients_with_ct_at_any_linked_diagnosis"] == 4
    assert out["patients_with_ct_and_advanced_at_any_diagnoses"] == 3
    assert out["patients_ct_without_advanced_at_any_linked_diagnosis"] == 1
    assert out["first_ct_linked_diagnosis"] == {"ct_only_n": 3, "ct_and_advanced_n": 1}
    assert out["first_any_linked_diagnosis_among_ct_ever"]["advanced_without_ct_n"] == 1
    x = out["first_advanced_vs_first_ct_among_patients_with_both_anywhere"]
    assert x["different_linked_diagnosis_date_n"] == 2
    assert x["first_advanced_before_first_ct_n"] == 1
    assert x["first_advanced_after_first_ct_n"] == 1


def test_filter_principal_and_ischemic():
    x = rows()
    extra = x.iloc[[0]].copy()
    extra["patient_id"] = "z"
    extra["principal_diagnosis_indicator"] = "S"
    extra2 = x.iloc[[0]].copy()
    extra2["patient_id"] = "y"
    extra2["Stroke"] = "Hemorrhagic"
    out = summarize(pd.concat([x, extra, extra2]))
    assert out["linked_patients_any_imaging"] == 5


def test_reject_outside_window():
    x = rows()
    x.loc[0, "datetime_px"] = "2018-01-20"
    with pytest.raises(ValueError, match="outside"):
        summarize(x)


def test_reject_bad_modality():
    x = rows()
    x.loc[0, "category"] = "SPECT"
    with pytest.raises(ValueError, match="category"):
        summarize(x)


def test_reject_null_identifier():
    x = rows()
    x.loc[0, "patient_id"] = None
    with pytest.raises(ValueError, match="identifiers"):
        summarize(x)


def test_reject_missing_columns():
    with pytest.raises(ValueError, match="Missing"):
        summarize(rows().drop(columns="datetime_px"))

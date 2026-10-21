"""Synthetic-data tests; no patient-level research data used."""
import pandas as pd
import pytest
from scripts.step13_source_inventory import inspect_frames, _dates


def test_date_parser_mixed_formats():
    x = pd.Series(["20180102", "2018-02-05", "bad"])
    date = _dates(x)
    assert date.iloc[0].year == 2018
    assert date.iloc[1].month == 2
    assert pd.isna(date.iloc[2])


def test_diagnosis_principal_stroke_audit():
    df = pd.DataFrame({
        "patient_id": ["a", "a", "b", "c", "d"],
        "code": ["I63.9", "I63.1", "H34.1", "I63.9", "I63.9"],
        "date": ["20180101", "2019-05-02", "20190110", "20180101", "20170101"],
        "principal_diagnosis_indicator": ["P", "P", "P", "S", "P"],
        "encounter_id": ["a1", "a2", "b1", "c1", "d1"],
    })
    x = inspect_frames("diagnoses", [df.iloc[:2], df.iloc[2:]], list(df))
    assert x["principal_I63_2018_2019_unique_patients"] == 1
    assert x["code_group_row_counts"]["principal_I63_2018_2019_rows"] == 2
    assert x["code_group_row_counts"]["principal_H34_1_2018_2019_rows"] == 1
    assert x["encounter_key_candidates"] == ["encounter_id"]
    assert x["ready_for_reconstruction"] is False


def test_procedure_code_mapping_audit():
    df = pd.DataFrame({"patient_id": ["a", "a", "b", "b", "c"],
        "code": ["70450", "70496", "70498", "70546", "70547"],
        "date": ["20180101"] * 5})
    x = inspect_frames("procedures", [df], list(df))
    assert x["code_group_row_counts"]["ct_brain_2018_2019_rows"] == 1
    assert x["code_group_row_counts"]["cta_neck_2018_2019_rows"] == 1
    assert x["code_group_row_counts"]["mra_head_2018_2019_rows"] == 1
    assert x["code_group_row_counts"]["mra_neck_2018_2019_rows"] == 1
    assert x["encounter_key_candidates"] == []


def test_demographics_missingness():
    df = pd.DataFrame({"patient_id": ["a", "b", "c"], "sex": ["F", "Unknown", None],
                       "year_of_birth": [1970, None, 1980]})
    x = inspect_frames("demographics", [df], list(df))
    assert x["distinct_patient_ids"] == 3
    assert x["sex_missing_or_unknown_n"] == 2
    assert x["birthyear_missing_n"] == 1


def test_missing_required_schema_recorded_not_imputed():
    df = pd.DataFrame({"patient_id": ["a"], "code": ["I63.9"]})
    x = inspect_frames("diagnoses", [df], list(df))
    assert "date" in x["missing_required_columns"]
    assert "principal_diagnosis_indicator" in x["missing_required_columns"]
    assert x["ready_for_reconstruction"] is False


def test_unexpected_source_rejected():
    with pytest.raises(ValueError, match="Unrecognized"):
        inspect_frames("unknown", [], [])

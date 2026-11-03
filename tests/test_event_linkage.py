"""Synthetic-only tests for the Step 11 event-linkage audit."""
import pandas as pd
import pytest
from scripts.step11_event_linkage import audit_events


def records():
    return pd.DataFrame({
        "patient_id": ["a", "a", "a", "a", "b", "b", "c"],
        "datetime_dx": ["2018-01-01", "2018-01-01", "2019-02-01", "2019-02-01",
                        "2018-04-02", "2018-04-03", "2019-06-01"],
        "datetime_px": ["2018-01-01", "2018-01-02", "2019-02-01", "2019-02-02",
                        "2018-04-04", "2018-04-04", "2019-06-01"],
        "category": ["CT", "CT", "CT", "MRI", "CTA", "CTA", "CT"],
        "CPTcode": [70450, 70460, 70450, 70551, 70496, 70496, 70450],
        "Stroke": ["Ischemic"] * 7,
        "principal_diagnosis_indicator": ["P"] * 7,
    })


def test_earliest_ct_only_with_later_mri():
    out = audit_events(records())
    assert out["unique_patients_with_linked_ischemic_diagnoses"] == 3
    assert out["unique_patient_diagnosis_dates"] == 5
    assert out["patients_with_multiple_linked_diagnosis_dates"] == 2
    assert out["earliest_linked_diagnosis"]["ct_only_n"] == 2
    assert out["patients_ct_only_at_earliest_but_advanced_at_another_linked_diagnosis_n"] == 1
    assert out["repeated_procedure_link_keys"] == 1


def test_optional_candidate():
    candidate = pd.DataFrame({
        "patient_id": ["a", "b", "x"], "dx_year": [2019, 2018, 2018],
        "MRI": [1, 0, 0], "CTA": [0, 1, 0], "MRA": [0, 0, 0],
    })
    r = audit_events(records(), candidate=candidate)["candidate_comparison"]
    assert r["saved_rows"] == 3
    assert r["linked_in_pre_exclusion_file_n"] == 2
    assert r["not_linked_in_pre_exclusion_file_n"] == 1
    assert r["earliest_linked_dx_year_differs_from_saved_year_n"] == 1
    assert r["earliest_linked_mri_receipt_differs_from_saved_n"] == 1


def test_bad_date_rejected():
    df = records()
    df.loc[0, "datetime_dx"] = "garbled"
    with pytest.raises(ValueError, match="unparseable"):
        audit_events(df)


def test_bad_category_rejected():
    df = records()
    df.loc[0, "category"] = "SPECT"
    with pytest.raises(ValueError, match="unknown procedure"):
        audit_events(df)


def test_repeated_candidate_id_rejected():
    candidate = pd.DataFrame({
        "patient_id": ["a", "a"], "dx_year": [2018, 2019],
        "MRI": [1, 0], "CTA": [0, 1], "MRA": [0, 0],
    })
    with pytest.raises(ValueError, match="must be unique"):
        audit_events(records(), candidate=candidate)

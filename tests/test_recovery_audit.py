"""Step 9 recovery audit tests on synthetic data only."""
import pandas as pd
from scripts.step09_audit_recovery import audit_batches


def test_event_ct_only_patients_and_dates():
    df = pd.DataFrame({
        "patient_id": ["a", "b", "b", "c", "d"],
        "category": ["CT", "CT", "MRI", "CTA", "CT"],
        "datetime_dx": ["2018-01-01", "2018-01-01", "2018-01-01",
                        "2018-01-01", "2019-01-01"],
    })
    result = audit_batches([df.iloc[:2], df.iloc[2:]], list(df))
    assert result["ct_patients_n"] == 3
    assert result["ct_only_patients_n"] == 2
    assert result["ct_plus_advanced_patients_n"] == 1
    assert result["ct_only_patient_diagnosis_dates_n"] == 2


def test_ct_only_differs_by_patient_vs_index_date():
    df = pd.DataFrame({
        "patient_id": ["a", "a", "a"],
        "category": ["CT", "CT", "MRA"],
        "date_dx": ["2018-01-01", "2019-01-01", "2019-01-01"],
    })
    result = audit_batches([df], list(df))
    assert result["ct_only_patients_n"] == 0
    assert result["ct_only_patient_diagnosis_dates_n"] == 1


def test_derived_explicit_ct_recovers_zero_advanced_imaging():
    df = pd.DataFrame({
        "patient_id": ["a", "b", "c"], "CT": [1, 1, 0],
        "MRI": [0, 1, 0], "CTA": [0, 0, 1], "MRA": [0, 0, 0],
        "race": ["Unknown", "White", "Black"],
    })
    result = audit_batches([df], list(df))
    assert result["ct_only_rows"] == 1
    assert result["rows_with_no_mri_cta_mra"] == 1
    assert result["race_ethnicity_missing_or_unknown"]["race"]["n"] == 1
    assert result["distinct_patient_ids"] == 3
    assert result["duplicate_patient_id_rows"] == 0


def test_derived_without_ct_cannot_claim_ct_only():
    df = pd.DataFrame({"MRI": [0, 1], "CTA": [0, 0], "MRA": [0, 0]})
    result = audit_batches([df], list(df))
    assert result["ct_only_rows"] is None
    assert result["rows_with_no_mri_cta_mra"] == 1
    assert any("No explicit CT" in x for x in result["warnings"])


def test_unrecognized_layout():
    df = pd.DataFrame({"patient_id": ["a", "b"]})
    result = audit_batches([df], list(df))
    assert result["table_type"] == "schema_only"
    assert result["rows_scanned"] == 2


def test_repeated_ids_detected_across_batches():
    df = pd.DataFrame({
        "patient_id": ["a", "b", "a"], "CT": [1, 1, 1],
        "MRI": [0, 0, 1], "CTA": [0, 0, 0], "MRA": [0, 0, 0],
    })
    result = audit_batches([df.iloc[:2], df.iloc[2:]], list(df))
    assert result["duplicate_patient_id_rows"] == 1

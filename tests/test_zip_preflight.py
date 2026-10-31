"""Generated ZIP fixtures; never use real clinical records in tests."""
from zipfile import ZipFile
import pandas as pd
import pytest
from scripts.step16_zip_preflight import preflight, sample_summary, _date_patterns


def fake_zip(path):
    with ZipFile(path, "w") as z:
        z.writestr("diagnosis.csv", "patient_id,code_system,code,principal_diagnosis_indicator,date\n" +
                   "a,ICD-10-CM,I63.9,P,20180102\n" * 14)
        z.writestr("procedure.csv", "patient_id,code_system,code,principal_procedure_indicator,date\n" +
                   "b,CPT,70450,N,2018-03-01\n" * 14)
        z.writestr("patient.csv", "patient_id,sex,race,ethnicity,year_of_birth,postal_code\n" +
                   "c,F,Unknown,Unknown,1980,99999\n" * 14)
        z.writestr("encounter.csv", "encounter_id,patient_id,admission_date\nx,y,20180101\n")
        z.writestr("note.txt", "ignore")


def test_preflight_reads_bounded_samples_and_no_ids(tmp_path):
    z = tmp_path / "data.zip"
    fake_zip(z)
    out = preflight(z, sample_rows=12)
    assert out["headers_checked_n"] == 5
    assert out["source_preflight"]["diagnoses"]["sample_rows_read"] == 12
    assert out["source_preflight"]["diagnoses"]["common_code_system_values"]["ICD-10-CM"] == 12
    assert out["source_preflight"]["procedures"]["brain_CT_CPT_in_sample_n"] == 12
    assert out["source_preflight"]["demographics"]["race_missing_unknown_n"] == 12
    assert out["ready_for_population_inference"] is False
    assert "99999" not in str(out)
    assert "20180102" not in str(out)
    assert "encounter_id" in out["all_member_headers"][3]["possible_encounter_fields"]


def test_date_patterns():
    s = pd.Series(["20180101", "2018-01-01", "", "bad"])
    out = _date_patterns(s)
    assert out == {"missing": 1, "compact_yyyymmdd": 1, "iso_like": 1, "other_nonmissing": 1}


def test_missing_zip_fails(tmp_path):
    with pytest.raises(FileNotFoundError):
        preflight(tmp_path / "missing.zip")


def test_negative_row_limit(tmp_path):
    z = tmp_path / "data.zip"
    fake_zip(z)
    with pytest.raises(ValueError):
        preflight(z, sample_rows=0)


def test_missing_one_source_reported(tmp_path):
    z = tmp_path / "data.zip"
    with ZipFile(z, "w") as archive:
        archive.writestr("diagnosis.csv", "patient_id,code_system,code,principal_diagnosis_indicator,date\n")
    out = preflight(z)
    assert out["source_preflight"]["procedures"]["status"] == "member_missing"
    assert out["source_preflight"]["demographics"]["status"] == "member_missing"


def test_no_actual_patient_columns_used_in_sample():
    frame = pd.DataFrame({"code_system": ["ICD-10-CM"] * 15,
                          "code": ["I63.9"] * 15,
                          "date": ["20180101"] * 15,
                          "principal_diagnosis_indicator": ["P"] * 15})
    result = sample_summary("diagnoses", frame)
    assert result["I63_family_in_sample_n"] == 15
    assert result["principal_indicator_values"] == {"P": 15}


def test_nonrepresentative_flag():
    df = pd.DataFrame({"sex": ["F"] * 12, "race": ["Unknown"] * 12,
                       "ethnicity": ["Unknown"] * 12, "year_of_birth": ["1980"] * 12})
    out = sample_summary("demographics", df)
    assert out["sample_is_nonrepresentative"] is True


def test_reason_for_visit_is_not_encounter_id():
    from scripts.step16_zip_preflight import is_encounter_identifier
    assert not is_encounter_identifier("reason_for_visit")
    assert not is_encounter_identifier("admitting_diagnosis")
    assert is_encounter_identifier("encounter_id")
    assert is_encounter_identifier("visit_occurrence_id")

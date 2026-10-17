"""Step 17 tests use tiny synthetic metadata-only archives."""
from zipfile import ZipFile

import pytest

from scripts.step17_zip_provenance import audit_zip, number


def fixture_zip(path):
    with ZipFile(path, "w") as zipfile:
        zipfile.writestr("manifest.csv",
                         "file,column_count,row_count,unique_patient_count\n"
                         "diagnosis.csv,8,1000000,300000\n"
                         "procedure.csv,6,800000,250000\n"
                         "patient.csv,9,400000,400000\n"
                         "patient_cohort.csv,3,80000,80000\n")
        zipfile.writestr("cohort_details.csv",
                         "cohort_name,cohort_number,total_patient_records\n"
                         "stroke cohort,1,150000\n")
        zipfile.writestr("dataset_details.csv",
                         "total_number_unique_patients,total_number_HCOs,date_created,network_name\n"
                         "400000,15,2023-07-01,SECRET NETWORK\n")
        zipfile.writestr("readme.txt",
                         "Claims data do not necessarily include hospital encounter IDs.\n")
        zipfile.writestr("diagnosis.csv", "patient_id,code,date\nsecret,ICD,20180101\n")
        zipfile.writestr("procedure.csv", "patient_id,code,date\nsecret,CPT,20180101\n")
        zipfile.writestr("patient.csv", "patient_id,sex,postal_code\nsecret,F,99999\n")
        zipfile.writestr("patient_cohort.csv", "patient_id,cohort_name\nsecret,stroke\n")


def test_bounded_aggregate_provenance(tmp_path):
    path = tmp_path / "synthetic.zip"
    fixture_zip(path)
    report = audit_zip(path)
    assert report["original_clinical_rows_read"] == 0
    assert report["metadata"]["manifest.csv"]["metadata_records_n"] == 4
    sources = report["metadata"]["manifest.csv"]["relevant_source_statistics"]
    assert sources[0]["declared_rows"] == 1000000
    assert sources[1]["declared_unique_patients"] == 250000
    assert sources[2]["archive_member_present"] is True
    assert report["metadata"]["cohort_details.csv"]["cohort_descriptions"][0]["cohort_name"] == "stroke cohort"
    assert report["metadata"]["dataset_details.csv"]["dataset_aggregates"][0]["total_number_HCOs"] == 15
    assert report["metadata"]["readme.txt"]["mentions_encounter"] is True
    assert "SECRET NETWORK" not in str(report)
    assert "99999" not in str(report)
    assert "20180101" not in str(report)
    assert "secret," not in str(report)


def test_not_found_is_reported(tmp_path):
    z = tmp_path / "empty.zip"
    with ZipFile(z, "w") as archive:
        archive.writestr("diagnosis.csv", "patient_id,code\nx,I63\n")
    r = audit_zip(z)
    assert all(x["status"] == "not_found" for x in r["metadata"].values())
    assert r["original_clinical_rows_read"] == 0


def test_reject_large_metadata_member(tmp_path):
    z = tmp_path / "large.zip"
    with ZipFile(z, "w") as archive:
        archive.writestr("manifest.csv", b"X" * 2048)
    report = audit_zip(z, limit=1024)
    assert report["metadata"]["manifest.csv"]["status"] == "too_large_for_metadata_audit"


def test_non_numeric_aggregate_is_none():
    assert number("1,234") == 1234
    assert number("unknown") is None
    assert number(None) is None


def test_missing_zip(tmp_path):
    with pytest.raises(FileNotFoundError):
        audit_zip(tmp_path / "no.zip")


def test_invalid_limit(tmp_path):
    with pytest.raises(ValueError):
        audit_zip(tmp_path / "nothing.zip", limit=0)


def test_censored_long_cohort_name(tmp_path):
    z = tmp_path / "cohort.zip"
    with ZipFile(z, "w") as archive:
        archive.writestr("cohort_details.csv", "cohort_name,cohort_number,total_patient_records\n" +
                         "a" * 200 + ",1,150\n")
    r = audit_zip(z)
    assert len(r["metadata"]["cohort_details.csv"]["cohort_descriptions"][0]["cohort_name"]) == 120

"""Tests use synthetic CSVs built into temporary ZIP archives only."""
from zipfile import ZipFile, ZIP_DEFLATED

import pytest

from scripts.step15_zip_inventory import classify, inspect_zip


def fake_zip(path):
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as z:
        z.writestr("export/diagnosis.csv", "patient_id,code,date,principal_diagnosis_indicator,encounter_id\na,I63.9,20180101,P,1\n")
        z.writestr("export/procedure.csv", "patient_id,code,date,visit_id\na,70450,20180102,1\n")
        z.writestr("export/patient.csv", "patient_id,sex,year_of_birth\na,F,1980\n")
        z.writestr("export/other.csv", "unrelated,data\n1,2\n")
        z.writestr("export/unreadable.parquet", b"PAR1")


def test_three_source_roles(tmp_path):
    p = tmp_path / "dataset.zip"
    fake_zip(p)
    report = inspect_zip(p)
    assert report["archive_members_total"] == 5
    assert report["candidate_count"] == 3
    names = {c["archive_member"] for c in report["candidates"]}
    assert names == {"export/diagnosis.csv", "export/procedure.csv", "export/patient.csv"}
    assert report["member_types"][".parquet"] == 1
    diagnosis = next(c for c in report["candidates"] if c["archive_member"].endswith("diagnosis.csv"))
    assert diagnosis["possible_roles"][0]["kind"] == "diagnoses"
    assert diagnosis["encounter_key_candidates"] == ["encounter_id"]
    assert all("a,I63.9" not in repr(x) for x in report["candidates"])


def test_diagnosis_not_confused_with_procedure():
    x = classify(["patient_id", "code", "date", "principal_diagnosis_indicator"], "dx.csv")
    assert x[0]["kind"] == "diagnoses"
    assert x[0]["schema_complete"] is True


def test_tabs_and_large_member_are_not_extracted(tmp_path):
    p = tmp_path / "sources.zip"
    with ZipFile(p, "w") as z:
        z.writestr("data/procedures.tsv", "patient_id\tcode\tdate\na\t70450\t20180101\n")
    report = inspect_zip(p)
    assert report["candidate_count"] == 1
    assert report["candidates"][0]["archive_member"] == "data/procedures.tsv"


def test_missing_zip_fails(tmp_path):
    with pytest.raises(FileNotFoundError):
        inspect_zip(tmp_path / "missing.zip")


def test_limit_respected(tmp_path):
    p = tmp_path / "sources.zip"
    fake_zip(p)
    report = inspect_zip(p, max_members=1)
    assert report["archive_members_examined"] == 1
    assert report["truncated_at_max_members"] is True


def test_invalid_caps(tmp_path):
    p = tmp_path / "sources.zip"
    fake_zip(p)
    with pytest.raises(ValueError):
        inspect_zip(p, max_members=0)


def test_no_patient_rows_in_serialized_report(tmp_path):
    p = tmp_path / "sources.zip"
    fake_zip(p)
    report = inspect_zip(p)
    assert "20180101" not in str(report)
    assert "I63.9" not in str(report)

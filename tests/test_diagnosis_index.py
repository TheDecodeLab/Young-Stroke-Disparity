"""Step 18 synthetic fixtures for full and bounded direct-ZIP diagnosis scans."""
from pathlib import Path
import sqlite3
from zipfile import ZipFile

import pandas as pd
import pytest

from scripts.step18_diagnosis_index import (
    choose_principal_I63, ensure_private_dir, expected_rows, scan,
)


ROWS = [
    ("a", "ICD-10-CM", "I63.9", "P", "20190105"),
    ("b", "ICD-10-CM", "I63.4", "P", "20180105"),
    ("a", "ICD-10-CM", "I63.1", "P", "20180102"),
    ("b", "ICD-10-CM", "I63.4", "S", "20180102"),
    ("c", "ICD-10-CM", "I63.9", "Unknown", "20190101"),
    ("d", "ICD-10-CM", "H34.1", "P", "20180101"),
    ("e", "ICD-9-CM", "434.91", "P", "20180101"),
    ("f", "ICD-10-CM", "I63.9", "P", "20170101"),
    ("g", "ICD-10-CM", "I63.9", "P", "20190230"),
    ("h", "ICD-10-CM", "I63.9", "P", "20180101"),
]


def archive(path: Path, *, declared: int | None = None) -> None:
    with ZipFile(path, "w") as z:
        header = "patient_id,code_system,code,principal_diagnosis_indicator,date\n"
        content = header + "".join(",".join(row) + "\n" for row in ROWS)
        z.writestr("diagnosis.csv", content)
        z.writestr("manifest.csv", "file,row_count\n" +
                   f"diagnosis.csv,{len(ROWS) if declared is None else declared}\n")


def check_sqlite(path: Path) -> tuple[list[tuple], str]:
    with sqlite3.connect(path) as conn:
        data = conn.execute(
            "SELECT patient_id,index_date,dx_code FROM first_principal_I63 ORDER BY patient_id"
        ).fetchall()
        state = conn.execute("SELECT value FROM scan_state WHERE key='scan_complete'").fetchone()[0]
    return data, state


def test_full_scan_selects_first_principal_I63_and_no_imaging(tmp_path):
    z = tmp_path / "test.zip"
    archive(z)
    work = tmp_path / "private"
    report = scan(z, work, chunk_rows=2)
    assert report["scan_complete"] is True
    assert report["aggregate_counters"]["rows_scanned"] == 10
    assert report["distinct_principal_I63_candidate_patients"] == 3
    assert report["aggregate_counters"]["qualifying_invalid_calendar_date_rows"] == 1
    assert report["aggregate_counters"]["in_year_icd10_I63_unknown_principal_rows"] == 1
    db = work / "step18_diagnosis_index.sqlite"
    rows, state = check_sqlite(db)
    assert rows == [
        ("a", "20180102", "I63.1"),
        ("b", "20180105", "I63.4"),
        ("h", "20180101", "I63.9"),
    ]
    assert state == "1"
    assert "a" not in str(report)
    assert "20180102" not in str(report)
    assert report["candidate_index_year_counts"] == {"2018": 3}


def test_bounded_smoke_database_never_marked_complete(tmp_path):
    z = tmp_path / "test.zip"
    archive(z)
    work = tmp_path / "private"
    result = scan(z, work, chunk_rows=2, limit_rows=3)
    assert result["scan_complete"] is False
    assert result["aggregate_counters"]["rows_scanned"] == 3
    assert result["distinct_principal_I63_candidate_patients"] == 2
    data, state = check_sqlite(work / "step18_diagnosis_index.partial.sqlite")
    assert state == "0"
    assert len(data) == 2
    with pytest.raises(FileExistsError, match="Prior"):
        scan(z, work, chunk_rows=2)


def test_manifest_mismatch_keeps_incomplete_database(tmp_path):
    z = tmp_path / "bad.zip"
    archive(z, declared=100)
    work = tmp_path / "private"
    with pytest.raises(ValueError, match="manifest"):
        scan(z, work, chunk_rows=4)
    _, state = check_sqlite(work / "step18_diagnosis_index.partial.sqlite")
    assert state == "0"
    assert not (work / "step18_diagnosis_index.sqlite").exists()


def test_qualifying_fields_rejected_if_missing():
    df = pd.DataFrame({"code": ["I63.9"]})
    with pytest.raises(ValueError, match="Missing"):
        choose_principal_I63(df)


def test_negative_limits_rejected(tmp_path):
    z = tmp_path / "test.zip"
    archive(z)
    with pytest.raises(ValueError, match="positive"):
        scan(z, tmp_path / "private", chunk_rows=0)


def test_private_dir_inside_repo_rejected():
    from scripts.step18_diagnosis_index import ROOT
    with pytest.raises(ValueError, match="OUTSIDE"):
        ensure_private_dir(ROOT / "results" / "my_private_data")


def test_no_file_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        scan(tmp_path / "missing.zip", tmp_path / "private")


def test_manifest_rows_read(tmp_path):
    z = tmp_path / "test.zip"
    archive(z)
    with ZipFile(z) as f:
        assert expected_rows(f) == len(ROWS)

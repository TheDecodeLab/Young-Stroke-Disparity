"""Metadata-only tests using generated synthetic files."""
from pathlib import Path

import pandas as pd
import pytest

from scripts.step14_discover_sources import classify, discover


def test_diagnosis_schema_ranks_diagnoses():
    out = classify(["patient_id", "code", "date", "principal_diagnosis_indicator"], "table01.parquet")
    assert out[0]["kind"] == "diagnoses"
    assert out[0]["schema_complete"]


def test_procedure_schema_not_diagnosis():
    out = classify(["patient_id", "code", "date"], "procedure_extract.csv")
    assert out[0]["kind"] == "procedures"
    assert out[0]["schema_complete"]


def test_demographic_schema():
    out = classify(["patient_id", "sex", "year_of_birth"], "table.parquet")
    assert out[0]["kind"] == "demographics"
    assert out[0]["schema_complete"]


def test_metadata_discovery_ignores_results_folder(tmp_path: Path):
    d = tmp_path / "source"
    d.mkdir()
    pd.DataFrame({"patient_id": ["one"], "code": ["I63.9"], "date": ["20180101"],
                  "principal_diagnosis_indicator": ["P"]}).to_csv(d / "unknown.csv", index=False)
    (d / "results").mkdir()
    pd.DataFrame({"patient_id": ["two"], "sex": ["M"],
                  "year_of_birth": [1980]}).to_csv(d / "results" / "hidden.csv", index=False)
    out = discover(d, max_depth=4)
    assert out["candidate_matches_total"] == 1
    assert out["candidates"][0]["relative_path"] == "unknown.csv"
    assert out["candidates"][0]["parquet_row_count"] is None


def test_depth_and_caps(tmp_path: Path):
    (tmp_path / "level1" / "level2").mkdir(parents=True)
    pd.DataFrame({"patient_id": ["a"], "code": ["70450"],
                  "date": ["20180101"]}).to_csv(tmp_path / "level1" / "level2" / "procedures.csv", index=False)
    a = discover(tmp_path, max_depth=1)
    assert a["candidate_matches_total"] == 0
    b = discover(tmp_path, max_depth=3)
    assert b["candidate_matches_total"] == 1
    assert b["candidates"][0]["format"] == "csv"


def test_invalid_root(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        discover(tmp_path / "missing")


def test_parquet_metadata_if_available(tmp_path: Path):
    pytest.importorskip("pyarrow")
    d = tmp_path / "source"
    d.mkdir()
    pd.DataFrame({"patient_id": ["one"], "code": ["I63.9"], "date": ["20180101"],
                  "principal_diagnosis_indicator": ["P"]}).to_parquet(d / "unknown.parquet")
    out = discover(d)
    assert out["candidate_matches_total"] == 1
    assert out["candidates"][0]["parquet_row_count"] == 1
